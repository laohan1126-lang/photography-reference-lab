"""Safe, repeatable imports. Historical analysis is retained as unverified notes."""
from __future__ import annotations

import csv
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import yaml
from .db import encode
from .models import CandidateInput, NoteInput, ProjectInput, Source, CollectionReport, PackCandidate, AnalysisImport
from .policy import digest
from .service import Library, Problem

MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_FILES = 2000


def archive_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or "\\" in name or "\x00" in name or path.is_absolute() or ".." in path.parts or ":" in name:
        raise ValueError("Unsafe archive path")
    return str(path)


def read_archive(content: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_FILES or sum(x.file_size for x in members) > MAX_ARCHIVE_BYTES:
                raise ValueError("Archive exceeds file-count or expanded-size limit")
            files = {}
            for entry in members:
                name = archive_name(entry.filename)
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise ValueError("Symlink and encrypted archives are not supported")
                if entry.is_dir(): continue
                if name in files: raise ValueError("Duplicate archive path")
                if entry.file_size > 20 * 1024 * 1024:
                    raise ValueError("An archive member exceeds 20 MiB")
                files[name] = archive.read(entry)
            return files
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid ZIP archive") from exc


def import_candidates(library: Library, project_id: str, content: bytes, job_id: str = "") -> dict:
    files = read_archive(content)
    if "manifest.json" not in files:
        raise ValueError("Candidate ZIP must have manifest.json at its root")
    manifest = json.loads(files["manifest.json"])
    if not isinstance(manifest, dict) or manifest.get("schema_version") not in {1, 2} or not isinstance(manifest.get("candidates"), list):
        raise ValueError("Expected schema_version 1 or 2 and a candidates array")
    if len(manifest["candidates"]) > 1000:
        raise ValueError("A candidate package may contain at most 1000 entries")
    library.project(project_id)
    declared_job = str(manifest.get("job_id", ""))
    if declared_job and job_id and declared_job != job_id:
        raise Problem(409, "候选包属于另一个采集任务")
    job_id = job_id or declared_job
    job = library.job(job_id) if job_id else None
    if job and (job["project_id"] != project_id or job["kind"] != "collection" or job["status"] == "cancelled"):
        raise Problem(409, "候选包任务不匹配或已取消")
    execution = CollectionReport.model_validate(manifest["execution_report"]) if manifest.get("execution_report") else None
    if manifest["schema_version"] == 2 and (not job_id or not execution):
        raise ValueError("schema_version 2 requires job_id and execution_report")
    report = {"created": 0, "existing": 0, "missing": 0, "errors": [], "reference_ids": []}
    for index, item in enumerate(manifest["candidates"]):
        try:
            if not isinstance(item, dict): raise ValueError("Candidate must be an object")
            if manifest["schema_version"] == 2:
                item = PackCandidate.model_validate(item).model_dump()
            filename = archive_name(item["file"])
            if filename not in files: raise ValueError("Referenced image is missing from archive")
            # A file package cannot claim that the human has already verified the source or image.
            source = Source.model_validate({**item.get("source", {}), "source_confirmed": False})
            key = str(item.get("id", ""))
            if not key: raise ValueError("Each candidate needs a stable id")
            batch = str(manifest.get("batch_id", digest(files["manifest.json"].decode("utf-8"))[:16]))
            candidate = CandidateInput(title=item.get("title", ""), source=source,
                import_key=f"package:{batch}:{key}", legacy_notes=item.get("notes", ""), job_id=job_id,
                discovery_intent=item.get("discovery_intent", "unknown"), discovery_reason=item.get("discovery_reason", ""),
                discovery_url=item.get("discovery_url", ""))
            asset = library.ingest_asset(files[filename], filename)
            candidate.asset_sha = asset["id"]
            result = library.add_candidate(project_id, candidate)
            report["created" if result["created"] else "existing"] += 1
            report["reference_ids"].append(result["reference"]["id"])
        except (ValueError, KeyError, TypeError, Problem) as exc:
            report["errors"].append({"index": index, "id": item.get("id") if isinstance(item, dict) else None, "error": str(exc)})
    if job_id and execution:
        if report["errors"]:
            execution = execution.model_copy(update={"status": "blocked", "summary": "部分候选导入失败；" + execution.summary})
        report["job"] = library.record_collection_report(job_id, execution)
    return report


def import_analyses(library: Library, project_id: str, raw: bytes, job_id: str = "") -> dict:
    if len(raw) > 8 * 1024 * 1024:
        raise Problem(413, "Analysis JSON exceeds 8 MiB")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("items"), list) or len(payload["items"]) > 200:
        raise Problem(422, "Expected schema_version=1 and up to 200 analysis items")
    declared = str(payload.get("job_id", ""))
    if job_id and declared != job_id:
        raise Problem(409, "分析结果属于另一个任务")
    job_id = declared or job_id
    library.project(project_id)
    if job_id:
        job = library.job(job_id)
        if job["project_id"] != project_id or job["kind"] != "analysis":
            raise Problem(409, "分析任务不匹配")
    report = {"imported": [], "errors": []}
    for index, item in enumerate(payload["items"]):
        try:
            reference_id = item["reference_id"]
            ref = library.reference(reference_id)
            if ref["project_id"] != project_id: raise Problem(409, "Wrong project")
            data = AnalysisImport.model_validate({key: value for key, value in item.items() if key != "reference_id"})
            library.apply_analysis(reference_id, data.result, data.expected_revision, data.producer, job_id)
            report["imported"].append(reference_id)
        except (Problem, ValueError, KeyError, TypeError) as exc:
            report["errors"].append({"index": index, "error": str(exc)})
    return report


def import_notion(library: Library, project_id: str | None, content: bytes) -> dict:
    """Import Markdown/CSV Notion exports, preserving original text and local image links.

    HTML is deliberately not executed/rendered. Export Markdown & CSV from Notion.
    """
    files = read_archive(content)
    if project_id is not None: library.project(project_id)
    image_map, errors = {}, []
    for name, raw in files.items():
        if PurePosixPath(name).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            try:
                image_map[name] = library.ingest_asset(raw, name)["id"]
            except ValueError as exc:
                errors.append({"file": name, "error": str(exc)})
    imported = []
    unresolved = []
    for name, raw in files.items():
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in {".md", ".csv"}: continue
        try:
            text = raw.decode("utf-8-sig")
            if suffix == ".md":
                def rewrite(match: re.Match) -> str:
                    target = unquote(match.group(2).strip("<>"))
                    if urlsplit(target).scheme: return match.group(0)
                    combined = PurePosixPath(name).parent / target
                    # Normalize relative references without ever writing outside the archive.
                    parts = []
                    for part in combined.parts:
                        if part == "..":
                            if not parts: return match.group(0)
                            parts.pop()
                        elif part != ".": parts.append(part)
                    relative = "/".join(parts)
                    if relative in image_map:
                        return f"![{match.group(1)}](/api/assets/{image_map[relative]}/preview)"
                    unresolved.append({"note": name, "target": target})
                    return match.group(0)
                body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", rewrite, text)
                title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), PurePosixPath(name).stem)
                note = library.add_note(project_id, NoteInput(title=title[:400], body=body, source_path=name[:400]))
                imported.append(note["id"])
            else:
                rows = list(csv.DictReader(io.StringIO(text)))
                if len(rows) > 2000: raise ValueError("CSV exceeds 2000 rows")
                for index, row in enumerate(rows):
                    title = next((str(v) for v in row.values() if v), f"Row {index + 1}")[:400]
                    note = library.add_note(project_id, NoteInput(title=title,
                        body="\n\n".join(f"{key}: {value}" for key, value in row.items()), source_path=f"{name}#{index + 1}"[:400]))
                    imported.append(note["id"])
        except (ValueError, UnicodeError) as exc:
            errors.append({"file": name, "error": str(exc)})
    if not any(PurePosixPath(name).suffix.lower() in {".md", ".csv"} for name in files):
        raise ValueError("No Markdown/CSV notes found; use Notion's Markdown & CSV export")
    return {"notes": len(set(imported)), "images": len(image_map), "unresolved_images": unresolved, "errors": errors}


def legacy_source(item: dict) -> Source:
    old_source = item.get("source") if isinstance(item.get("source"), dict) else {}
    raw_page = item.get("pin_href") or item.get("source_page") or old_source.get("url") or item.get("source_url", "")
    image = item.get("currentSrc") or item.get("url", "")
    if "pinimg.com" in str(raw_page) or "xhscdn.com" in str(raw_page):
        image, raw_page = raw_page, ""
    # Legacy content is untrusted. Invalid URL metadata is retained only in legacy_notes.
    values = dict(page_url=str(raw_page or ""), image_url=str(image or ""),
                  author=str(item.get("source_author") or old_source.get("author") or "")[:400],
                  title=str(item.get("source_note_title") or item.get("title") or "")[:400],
                  search_query=str(item.get("query") or item.get("search_keyword") or "")[:400],
                  search_category=str(item.get("category") or item.get("direction") or "")[:400],
                  obtained_as="unknown", source_confirmed=False)
    try:
        return Source(**values)
    except ValueError:
        values.update(page_url="", image_url="")
        return Source(**values)


def migrate_legacy(library: Library, root: Path, project_id: str | None = None) -> dict:
    root = root.resolve()
    if not root.is_dir(): raise ValueError("Legacy project directory not found")
    project_id = project_id or "legacy-changye-huansheng"
    library.create_project(ProjectInput(character="王昭君", work="王者荣耀", costume="长夜焕生",
        brief="从历史看板迁移；人工选择单独保留，图片内容和旧动作说明必须重新核验。"), ident=project_id)
    decisions = {}
    decision_path = root / "data/live_pose_decisions.json"
    if decision_path.is_file():
        raw = json.loads(decision_path.read_text(encoding="utf-8-sig"))
        for key, value in (("keep_ids", "keep"), ("maybe_ids", "maybe"), ("reject_ids", "reject")):
            for ident in raw.get(key, []): decisions[ident] = value
    manifest_paths = ["data/selected_candidates.yaml", "staging/live_manifest.json", "staging/cosplay_manifest.json",
                      "staging/xhs_manifest.json", "data/references.yaml"]
    report = {"project_id": project_id, "created": 0, "existing": 0, "missing": 0, "manifests": [], "errors": []}
    for relative in manifest_paths:
        path = root / relative
        if not path.is_file(): continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        rows = raw if isinstance(raw, list) else raw.get("items", raw.get("candidates", [])) if isinstance(raw, dict) else []
        if not isinstance(rows, list):
            report["errors"].append({"file": relative, "error": "Manifest items are not a list"})
            continue
        report["manifests"].append(relative)
        for index, item in enumerate(rows):
            try:
                if not isinstance(item, dict): raise ValueError("Invalid legacy record")
                old_id = str(item.get("source_id") or item.get("id") or item.get("selected_id") or index)
                file = item.get("file") or item.get("local_path") or ""
                relative_file = str(file).replace("\\", "/")
                # Some legacy manifests store repository-relative paths instead of project-relative paths.
                repo_prefix = f"references/{root.name}/"
                if relative_file.startswith(repo_prefix): relative_file = relative_file[len(repo_prefix):]
                resolved = (root / relative_file).resolve()
                if not resolved.is_relative_to(root): raise ValueError("Legacy image path escapes project root")
                asset = library.ingest_asset(resolved.read_bytes(), resolved.name) if file and resolved.is_file() else None
                if asset is None: report["missing"] += 1
                source = legacy_source(item)
                historical = {"legacy_id": old_id, "legacy_manifest": relative, "claimed_dimensions": [item.get("width"), item.get("height")],
                              "unverified_description": item.get("observed_pose") or item.get("pose") or item.get("analysis"),
                              "unverified_suitability": item.get("suitability"), "file": file}
                result = library.add_candidate(project_id, CandidateInput(asset_sha=asset["id"] if asset else None,
                    title=str(item.get("title") or item.get("selected_id") or item.get("id") or old_id)[:400], source=source,
                    import_key=f"legacy:{relative}:{old_id}", legacy_notes=encode(historical)[:12000]),
                    decision=decisions.get(old_id, "pending"), actor="legacy_migration")
                report["created" if result["created"] else "existing"] += 1
            except (ValueError, OSError, Problem) as exc:
                report["errors"].append({"file": relative, "index": index, "error": str(exc)})
    if not report["manifests"]: raise ValueError("No supported legacy manifests found")
    return report
