"""Read-only, rebuildable image catalogue for the owner's local library."""
from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from PIL import Image, ImageOps, UnidentifiedImageError

from .collection_history import _is_link_or_junction, _run_bases


CATALOG_VERSION = 1
GENERATOR_ID = "photography-reference-lab/local-catalog"
PREVIEW_SIZE = 1800
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
ALIAS_GROUPS = (("渡边曜", "渡辺曜"),)
DECISIONS = {"pending": "待筛选", "keep": "保留", "maybe": "待定", "reject": "淘汰"}


class CatalogError(ValueError):
    pass


def _json(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        decoded = json.loads(value)
        return decoded
    except (TypeError, ValueError):
        return fallback


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (OSError, ValueError):
        return False


def _assert_no_links(path: Path, anchor: Path) -> None:
    """Reject links/reparse points from an existing anchor through ``path``."""
    path = path.absolute()
    anchor = anchor.absolute()
    if not _inside(path, anchor):
        raise CatalogError(f"路径越过允许边界：{path}")
    if anchor.exists() and _is_link_or_junction(anchor):
        raise CatalogError(f"不允许使用链接或重解析点：{anchor}")
    cursor = anchor
    for part in path.relative_to(anchor).parts:
        cursor /= part
        if cursor.exists() and _is_link_or_junction(cursor):
            raise CatalogError(f"不允许使用链接或重解析点：{cursor}")


def _safe_existing_file(path: Path, root: Path) -> Path | None:
    try:
        _assert_no_links(path, root)
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or not _inside(resolved, root):
            return None
        _assert_no_links(resolved, root)
        return resolved
    except (CatalogError, OSError):
        return None


def _safe_name(value: object, *, fallback: str = "未命名", limit: int = 72) -> str:
    text = str(value or "").strip()
    text = "".join(" " if ord(char) < 32 else char for char in text)
    text = re.sub(r'[<>:"/\\|?*]', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    stem = text.split(".", 1)[0].upper()
    if stem in WIN_RESERVED:
        text = "_" + text
    return (text[:limit].rstrip(" .") or fallback)


def _friendly_title(*values: object, sha: str) -> str:
    """Choose human metadata over digests or opaque collector identifiers."""
    opaque_words = {"未登记下载图", "未命名参考", "未命名", "untitled"}
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        stem = Path(text.replace("\\", "/")).stem.strip()
        compact = re.sub(r"[\s_-]", "", stem).casefold()
        digest_like = bool(SHA_RE.fullmatch(compact)) or bool(re.fullmatch(r"[0-9a-f]{16,63}", compact))
        internal = bool(re.fullmatch(r"(?:dot[:#-]?)?[a-z]?\d{1,10}", compact))
        if stem.casefold() in opaque_words or digest_like or internal:
            continue
        return stem
    return f"参考图_{sha[:12]}"


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".catalog-writing-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(10):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.05)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _atomic_json(path: Path, payload: object) -> None:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    _atomic_bytes(path, raw)


def _owned_write(output: Path, relative: str, data: bytes, previous_files: dict[str, str],
                 errors: list[dict], *, recoverable: str = "") -> str:
    """Write an owned file and return the digest actually written."""
    rel = _relative_owned(relative)
    if rel is None:
        errors.append({"kind": "catalog_owned_path_invalid", "path": relative})
        return ""
    target = output / rel
    if not _inside(target, output):
        errors.append({"kind": "catalog_owned_path_escape", "path": relative})
        return ""
    if target.exists():
        if _is_link_or_junction(target) or not target.is_file():
            errors.append({"kind": "catalog_user_path_conflict", "path": relative, "reason": "链接、目录或重解析点"})
            return ""
        prior = previous_files.get(rel.as_posix())
        current = _sha_file(target)
        if not prior and recoverable and current == recoverable:
            prior = current
        if not prior or current != prior:
            errors.append({"kind": "catalog_user_path_conflict", "path": relative, "reason": "用户新增或修改，保留原文件"})
            return ""
    _atomic_bytes(target, data)
    return _sha_file(target)


def _owned_preview(path: Path, relative: str, expected_sha: str,
                   previous_files: dict[str, str]) -> str:
    """Recover ownership only from an explicit preview hash on its generated path."""
    if not expected_sha or _is_link_or_junction(path) or not path.is_file():
        return ""
    digest = _sha_file(path)
    if digest != expected_sha:
        return ""
    if previous_files.get(relative) not in {None, digest}:
        return ""
    return digest


def _record_owned_file(owned: dict[str, str], path: Path, relative: str,
                       expected_sha: str, previous_files: dict[str, str], *, fresh: bool = False) -> bool:
    if fresh and expected_sha and not _is_link_or_junction(path) and path.is_file():
        digest = _sha_file(path)
        if digest != expected_sha:
            return False
    else:
        digest = _owned_preview(path, relative, expected_sha, previous_files)
    if not digest:
        return False
    owned[_relative_owned(relative).as_posix()] = digest
    return True


def _record_written(owned: dict[str, str], relative: str, digest: str) -> None:
    rel = _relative_owned(relative)
    if rel is not None and SHA_RE.fullmatch(digest):
        owned[rel.as_posix()] = digest


def _legacy_owned_paths(output: Path, previous: dict, projects: dict) -> dict[str, str]:
    """Recover only old generated copies uniquely implied by the manifest."""
    if previous.get("generator") != GENERATOR_ID or not isinstance(previous.get("items"), list):
        return {}
    recovered: dict[str, str] = {}
    for item in previous["items"]:
        if not isinstance(item, dict):
            continue
        sha = str(item.get("sha") or "").lower()
        digest = str(item.get("preview_sha256") or "").lower()
        browse = str(item.get("browse_path") or "").replace("\\", "/")
        if not SHA_RE.fullmatch(sha) or not SHA_RE.fullmatch(digest) or not browse.startswith("images/"):
            continue
        relative = _relative_owned(browse)
        if relative is not None and _owned_preview(output / relative, browse, digest, {}):
            recovered[browse] = digest
        stem = Path(browse).stem
        groups = set()
        for relation in item.get("relations", []) if isinstance(item.get("relations"), list) else []:
            project_id = str(relation.get("project_id") or "")
            character = relation.get("character") or projects.get(project_id, {}).get("character")
            if relation.get("kind") in {"project", "run"} and (character or project_id):
                groups.add(_canonical_group(str(character or project_id)))
        for group in groups:
            folder = _safe_name(group, limit=80)
            candidate = Path("角色项目") / folder / f"{stem}.jpg"
            if _owned_preview(output / candidate, candidate.as_posix(), digest, {}):
                recovered[candidate.as_posix()] = digest
        categories = {str(value) for value in item.get("categories", []) if isinstance(value, str)}
        for folder in (["其他/全局收藏"] if "全局收藏" in categories else []) + (
                ["其他/学习候选"] if "学习候选" in categories else []):
            candidate = Path(folder) / f"{stem}.jpg"
            if _owned_preview(output / candidate, candidate.as_posix(), digest, {}):
                recovered[candidate.as_posix()] = digest
        if not groups and not ({"全局收藏", "学习候选"} & categories) and "角色引用" not in categories:
            candidate = Path("其他/未分类（待归属）") / f"{stem}.jpg"
            if _owned_preview(output / candidate, candidate.as_posix(), digest, {}):
                recovered[candidate.as_posix()] = digest
    return recovered


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(str(right.resolve(strict=False)))


def _relative_owned(path: str) -> Path | None:
    relative = Path(str(path).replace("\\", "/"))
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    return relative


def _load_owned_manifest(output: Path, repo_root: Path) -> tuple[dict, list[dict]]:
    """Accept only a nonempty output previously created by this tool and repo."""
    manifest = output / "manifest.json"
    if not output.exists():
        return {}, []
    if _is_link_or_junction(output) or not output.is_dir():
        raise CatalogError(f"输出目录不能是链接或文件：{output}")
    entries = list(output.iterdir())
    if not entries:
        return {}, []
    if _is_link_or_junction(manifest) or not manifest.is_file():
        raise CatalogError("输出目录非空且不是本工具创建的专用目录；拒绝覆盖")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError("已有 manifest.json 无法校验；拒绝覆盖输出目录") from exc
    if (not isinstance(payload, dict) or payload.get("generator") != GENERATOR_ID
            or payload.get("repo_root") != str(repo_root.resolve())
            or not isinstance(payload.get("owned_files"), dict)):
        raise CatalogError("输出目录不属于当前仓库的图片目录生成器；拒绝覆盖")
    return payload, []


def _prepare_output(output: Path, repo_root: Path, data_dir: Path, source_roots: Iterable[Path]) -> tuple[dict, list[dict]]:
    """Limit output to a dedicated data child and prove ownership before reuse."""
    if not output.is_absolute():
        output = repo_root / output
    output = output.resolve(strict=False)
    if not _same_path(output.parent, data_dir):
        raise CatalogError("输出必须是资料目录下的专用子目录")
    protected = [data_dir / "assets", data_dir / "web",
                 repo_root / "web", repo_root / "ref_lab", repo_root / "tools", repo_root / "tests",
                 repo_root / ".local" / "collection-runs", *source_roots]
    for path in protected:
        if _same_path(output, path) or _inside(output, path) or _inside(path, output):
            raise CatalogError(f"输出会覆盖受保护路径或其祖先：{path}")
    _assert_no_links(output, repo_root)
    previous, _ = _load_owned_manifest(output, repo_root)
    return previous, []


@contextmanager
def _open_library(data_dir: Path):
    db = data_dir / "library.sqlite3"
    if db.is_symlink() or _is_link_or_junction(db) or not db.is_file():
        raise CatalogError(f"找不到可读取的资料库：{db}")
    try:
        con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only=ON")
        yield con
    except sqlite3.Error as exc:
        raise CatalogError(f"资料库只读读取失败：{exc}") from exc
    finally:
        if "con" in locals():
            con.close()


def _has_table(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _rows(con: sqlite3.Connection, table: str, columns: str = "*") -> list[sqlite3.Row]:
    return con.execute(f"SELECT {columns} FROM {table}").fetchall() if _has_table(con, table) else []


def resolve_data_dir(repo_root: Path, configured: Path | None = None) -> Path:
    if configured is not None:
        path = configured if configured.is_absolute() else repo_root / configured
    else:
        runtime = repo_root / ".local" / "windows-runtime.json"
        if _is_link_or_junction(runtime):
            raise CatalogError("windows-runtime.json 不能是链接")
        if not runtime.is_file():
            raise CatalogError(f"缺少运行配置：{runtime}")
        try:
            payload = json.loads(runtime.read_text(encoding="utf-8-sig"))
            value = payload["data_dir"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CatalogError(f"无法读取 data_dir：{runtime}") from exc
        path = Path(value)
        if not path.is_absolute():
            path = repo_root / path
    if not path.is_dir():
        raise CatalogError(f"资料目录不存在：{path}")
    _assert_no_links(path, repo_root)
    return path.resolve()


def _canonical_group(character: str) -> str:
    for group in ALIAS_GROUPS:
        if character in group:
            return f"{group[0]}（{group[1]}）"
    return character


def _project_label(project: dict) -> str:
    character = str(project.get("character") or "未命名角色")
    context = " / ".join(str(project.get(key) or "") for key in ("work", "costume") if project.get(key))
    return f"{character} · {context}" if context else character


def _load_database(data_dir: Path) -> tuple[dict[str, dict], list[dict], dict[str, dict], list[dict], list[dict], dict[str, dict]]:
    projects: dict[str, dict] = {}
    refs: list[dict] = []
    assets: dict[str, dict] = {}
    inspirations: list[dict] = []
    studies: list[dict] = []
    jobs: dict[str, dict] = {}
    with _open_library(data_dir) as con:
        for row in _rows(con, "projects", "id,data"):
            data = _json(row["data"], {})
            if isinstance(data, dict):
                ident = str(data.get("id") or row["id"])
                projects[ident] = {**data, "id": ident}
        for row in _rows(con, "assets", "id,data"):
            data = _json(row["data"], {})
            if isinstance(data, dict):
                assets[str(row["id"])] = {**data, "id": str(row["id"])}
        for row in _rows(con, "refs", "id,project_id,asset_sha,decision,state,data"):
            data = _json(row["data"], {})
            if isinstance(data, dict):
                refs.append({"id": row["id"], "project_id": row["project_id"],
                             "asset_sha": row["asset_sha"], "decision": row["decision"],
                             "state": row["state"], **data})
        for row in _rows(con, "inspirations", "id,asset_sha,active,data"):
            data = _json(row["data"], {})
            if isinstance(data, dict):
                inspirations.append({"id": row["id"], "asset_sha": row["asset_sha"],
                                     "active": bool(row["active"]), **data})
        for row in _rows(con, "study_candidates", "id,batch_id,asset_sha,status,data"):
            data = _json(row["data"], {})
            if isinstance(data, dict):
                studies.append({"id": row["id"], "batch_id": row["batch_id"],
                                "asset_sha": row["asset_sha"], "status": row["status"], **data})
        for row in _rows(con, "jobs", "id,project_id,kind,status,data"):
            if row["kind"] != "collection":
                continue
            data = _json(row["data"], {})
            jobs[str(row["id"])] = {"id": str(row["id"]), "project_id": str(row["project_id"]),
                                     "status": row["status"], **(data if isinstance(data, dict) else {})}
    return projects, refs, assets, inspirations, studies, jobs


def _asset_file(data_dir: Path, meta: dict) -> Path | None:
    sha = str(meta.get("id") or "")
    if not SHA_RE.fullmatch(sha):
        return None
    ext = str(meta.get("ext") or "").lower()
    likely = [data_dir / "assets" / sha[:2] / sha / f"original.{ext}"] if ext else []
    likely += [data_dir / "assets" / sha[:2] / sha / f"original{suffix}" for suffix in IMAGE_SUFFIXES]
    for path in dict.fromkeys(likely):
        safe = _safe_existing_file(path, data_dir / "assets")
        if safe is not None:
            return safe
    return None


def _read_inventory(path: Path | None, repo_root: Path, source_roots: Iterable[Path], errors: list[dict]) -> list[dict]:
    if path is None:
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise CatalogError(f"盘点报告无法读取：{path}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != 1 or not isinstance(payload.get("extra_images"), list):
        raise CatalogError("盘点报告必须是 schema=1，并含 extra_images 数组")
    root = Path(str(payload.get("root") or ""))
    if not root.is_absolute() or not _same_path(root, repo_root):
        raise CatalogError("盘点报告的 root 必须等于当前已确认仓库，不能自行扩大读取边界")
    roots = []
    for item in source_roots:
        item = item if item.is_absolute() else repo_root / item
        if (not _inside(item, repo_root) or _same_path(item, repo_root)
                or _is_link_or_junction(item) or not item.is_dir()):
            raise CatalogError(f"显式源边界必须是授权仓库内的非链接子目录：{item}")
        roots.append(item.resolve())
    allowed_prefixes = [root / name for name in ("images", "batches", "staging")]
    allowed_prefixes += roots
    accepted = []
    for index, row in enumerate(payload["extra_images"]):
        if not isinstance(row, dict) or not all(key in row for key in ("path", "sha256", "bytes")):
            errors.append({"kind": "inventory_invalid", "index": index, "reason": "缺少 path/sha256/bytes"})
            continue
        raw = Path(str(row["path"]))
        if not raw.is_absolute():
            errors.append({"kind": "inventory_unsafe", "path": str(raw), "reason": "必须是绝对路径"})
            continue
        if not any(_inside(raw, prefix) for prefix in allowed_prefixes):
            errors.append({"kind": "inventory_unsafe", "path": str(raw), "reason": "不在允许的源边界内"})
            continue
        parent = next((prefix for prefix in allowed_prefixes if _inside(raw, prefix)), None)
        safe = _safe_existing_file(raw, parent) if parent else None
        if safe is None:
            errors.append({"kind": "inventory_unsafe", "path": str(raw), "reason": "文件不存在、是链接或越界"})
            continue
        actual = _sha_file(safe)
        expected = str(row["sha256"]).lower()
        if not SHA_RE.fullmatch(expected) or actual != expected:
            errors.append({"kind": "inventory_hash_mismatch", "path": str(raw), "expected": expected, "actual": actual})
            continue
        try:
            size_ok = safe.stat().st_size == int(row["bytes"])
        except (OSError, ValueError, TypeError):
            size_ok = False
        if not size_ok:
            errors.append({"kind": "inventory_size_mismatch", "path": str(raw)})
            continue
        accepted.append({"sha": actual, "path": safe, "source_hint": str(row.get("source_hint") or ""),
                         "category": str(row.get("category") or "未分类")})
    for index, item in enumerate(payload.get("errors", []) if isinstance(payload.get("errors"), list) else []):
        errors.append({"kind": "inventory_report_error", "index": index,
                       "reason": item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)})
    return accepted


def _job_id_for_base(base: Path, runs_root: Path) -> str:
    try:
        return base.resolve().relative_to(runs_root.resolve()).parts[0]
    except (OSError, ValueError, IndexError):
        return ""


def _scan_runs(repo_root: Path, jobs: dict[str, dict], projects: dict[str, dict], errors: list[dict]) -> list[dict]:
    runs_root = repo_root / ".local" / "collection-runs"
    if not runs_root.is_dir():
        return []
    owners = {job_id: str(job.get("project_id") or "") for job_id, job in jobs.items()}
    attributed, unattributed = _run_bases(repo_root, owners)
    found = []
    seen_paths: set[str] = set()
    bases = [(base, owner, True) for base, owner in attributed] + [(base, "", False) for base in unattributed]
    for base, owner, attributed_owner in bases:
        if not _inside(base, runs_root) or _is_link_or_junction(base):
            continue
        job_id = _job_id_for_base(base, runs_root)
        project_id = owner if attributed_owner else ""
        if project_id not in projects:
            project_id = ""
        job_root = runs_root / job_id if job_id else base
        received = base / "received.json"
        if received.is_file() and not _is_link_or_junction(received):
            try:
                payload = json.loads(received.read_text(encoding="utf-8"))
                records = payload.get("candidates", []) if isinstance(payload, dict) else payload
                if not isinstance(records, list):
                    raise ValueError("不是数组")
            except (OSError, ValueError) as exc:
                errors.append({"kind": "run_manifest_invalid", "path": str(received), "reason": str(exc)})
                records = []
            for index, row in enumerate(records):
                if not isinstance(row, dict):
                    errors.append({"kind": "run_record_invalid", "path": str(received), "index": index})
                    continue
                raw = Path(str(row.get("original_path") or ""))
                safe = _safe_existing_file(raw, job_root)
                if safe is None:
                    errors.append({"kind": "run_image_unsafe_or_missing", "path": str(raw), "job_id": job_id})
                    continue
                if str(safe) in seen_paths:
                    continue
                seen_paths.add(str(safe))
                actual = _sha_file(safe)
                declared = str(row.get("asset_sha") or "").lower()
                if declared and declared != actual:
                    errors.append({"kind": "run_hash_mismatch", "path": str(safe), "expected": declared, "actual": actual})
                    continue
                detail = row.get("author_detail") if isinstance(row.get("author_detail"), dict) else {}
                title = row.get("title") or detail.get("title") or safe.name
                found.append({"sha": actual, "path": safe, "title": str(title), "project_id": project_id,
                              "job_id": job_id, "run_status": jobs.get(job_id, {}).get("status", ""),
                              "source_kind": "collection_run"})
        images = base / "images"
        if images.is_dir() and not _is_link_or_junction(images):
            for path in images.iterdir():
                if path.suffix.lower() not in IMAGE_SUFFIXES or _is_link_or_junction(path):
                    continue
                safe = _safe_existing_file(path, job_root)
                if safe is None:
                    errors.append({"kind": "run_image_unsafe", "path": str(path), "job_id": job_id})
                    continue
                if str(safe) in seen_paths:
                    continue
                seen_paths.add(str(safe))
                actual = _sha_file(safe)
                declared = safe.stem.lower()
                if SHA_RE.fullmatch(declared) and declared != actual:
                    errors.append({"kind": "run_filename_hash_mismatch", "path": str(safe), "expected": declared, "actual": actual})
                    continue
                found.append({"sha": actual, "path": safe, "title": "未登记下载图", "project_id": project_id,
                              "job_id": job_id, "run_status": jobs.get(job_id, {}).get("status", ""),
                              "source_kind": "collection_run"})
    return found


def _verify_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                return False
            image.verify()
        return True
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        return False


def _make_preview(source: Path, target: Path) -> str:
    with Image.open(source) as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("不支持多帧图片")
        image.load()
        display = ImageOps.exif_transpose(image).convert("RGB")
        display.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        display.save(output, "JPEG", quality=88, optimize=True, progressive=True)
    data = output.getvalue()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=".catalog-preview-", suffix=".jpg")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if _is_link_or_junction(target) or os.path.samefile(source, target):
        raise CatalogError("派生预览与原图共享了文件身份")
    return hashlib.sha256(data).hexdigest()


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _local_href(prefix: str, relative: str) -> str:
    if not relative or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", relative):
        return html.escape(relative, quote=True)
    path = (prefix + relative).replace("\\", "/")
    return html.escape(quote(path, safe="/"), quote=True)


def _page(title: str, subtitle: str, items: list[dict], roles: list[dict], prefix: str, *, filters: bool = True,
          browse_field: str = "browse_path") -> str:
    cards = []
    for item in items:
        search = " ".join(str(item.get(key) or "") for key in ("title", "original_name", "sha", "status", "relations_text", "role_groups"))
        categories = " ".join(item.get("categories", []))
        preview = item.get(browse_field)
        image_href = _local_href(prefix, preview) if preview else ""
        image_tag = (f'<img loading="lazy" src="{image_href}" alt="{html.escape(item["title"])}">'
                     if preview else '<div class="missing">暂无可用浏览图</div>')
        original = (f'<a href="{_local_href("", item["original_href"])}">打开原图</a>' if item.get("original_href") else '<span>原图不可用</span>')
        details = html.escape(item.get("relations_text") or "")
        cards.append(f'''<article class="card" data-search="{html.escape(search, quote=True)}" data-category="{html.escape(categories, quote=True)}">
<a href="{image_href}" target="_blank">{image_tag}</a>
<div class="body"><h2>{html.escape(item["title"])}</h2><p>{html.escape(item["status"])}</p>
<small>{details}</small><div class="links">{original}<span>{html.escape(item["sha"][:12])}</span></div></div></article>''')
    role_links = "".join(f'<a href="{_local_href(prefix, role["folder"] + "/index.html")}">{html.escape(role["group"])} <small>{role["count"]}</small></a>' for role in roles)
    script = '' if not filters else '''<script>
const q=document.querySelector('#q');const category=document.querySelector('#category');const role=document.querySelector('#role');
function apply(){const words=q.value.trim().toLocaleLowerCase();const c=category.value;const r=role.value;
document.querySelectorAll('.card').forEach(card=>{const hay=card.dataset.search.toLocaleLowerCase();card.hidden=(words&&!hay.includes(words))||(c&&!card.dataset.category.split(' ').includes(c))||(r&&!hay.includes(r));});}
q.addEventListener('input',apply);category.addEventListener('change',apply);role.addEventListener('change',apply);
</script>'''
    role_options = ''.join(f'<option value="{html.escape(row["group"], quote=True)}">{html.escape(row["group"])}</option>' for row in roles)
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>
:root{{color-scheme:light;--ink:#20221f;--muted:#6a7068;--paper:#f4f1e9;--card:#fffdf8;--line:#d8d3c7;--accent:#9a4f36}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 "Microsoft YaHei",system-ui,sans-serif}}
header{{padding:34px max(20px,5vw) 18px;border-bottom:1px solid var(--line)}}h1{{font:600 clamp(26px,4vw,44px)/1.1 Georgia,"Songti SC",serif;margin:0 0 8px}}header p{{margin:0;color:var(--muted)}}
.tools{{display:flex;gap:10px;flex-wrap:wrap;padding:16px max(20px,5vw)}}input,select{{min-height:42px;border:1px solid var(--line);background:var(--card);padding:8px 12px;border-radius:999px}}input{{flex:1;min-width:240px}}
.roles{{display:flex;gap:8px;overflow:auto;padding:0 max(20px,5vw) 16px}}.roles a{{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:7px 12px;white-space:nowrap;color:inherit;text-decoration:none}}.roles small{{color:var(--muted)}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;padding:8px max(20px,5vw) 48px}}.card{{background:var(--card);border:1px solid var(--line);min-width:0}}
.card>a{{display:block;aspect-ratio:4/5;background:#e6e1d7}}.card img{{width:100%;height:100%;object-fit:contain}}.missing{{height:100%;display:grid;place-items:center;color:var(--muted)}}
.body{{padding:12px}}.body h2{{font-size:15px;line-height:1.35;margin:0 0 6px;overflow-wrap:anywhere}}.body p{{margin:0 0 7px;color:var(--accent);font-weight:600}}small{{color:var(--muted)}}.links{{display:flex;justify-content:space-between;gap:8px;margin-top:10px}}.links a{{color:var(--accent)}}
@media(max-width:520px){{main{{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding-left:10px;padding-right:10px}}.body{{padding:9px}}.body h2{{font-size:13px}}}}</style>
<header><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></header>
<div class="tools"><input id="q" type="search" placeholder="全文搜索角色、标题、项目、状态或 SHA">
<select id="category"><option value="">全部类别</option><option>角色引用</option><option>全局收藏</option><option>学习候选</option><option>采集未入库</option><option>散落待归类</option></select>
<select id="role"><option value="">全部角色/项目</option>{role_options}</select></div>
<div class="roles">{role_links}</div><main>{''.join(cards) or '<p>这里暂时没有图片。</p>'}</main>{script}</html>'''


def _relation_text(relations: list[dict]) -> str:
    lines = []
    for rel in relations:
        kind = rel.get("kind")
        if kind == "project":
            label = _project_label(rel)
            state = DECISIONS.get(rel.get("decision"), rel.get("decision") or "待筛选")
            if rel.get("detached"):
                state = "已移出项目"
            if rel.get("archived"):
                state += "/项目已归档"
            lines.append(f"{label}：{state}")
        elif kind == "favorite":
            lines.append("全局收藏" + ("（当前）" if rel.get("active") else "（历史）"))
        elif kind == "study":
            lines.append(f"学习待筛：{rel.get('status') or '待筛'}")
        elif kind == "run":
            lines.append(f"采集记录：{rel.get('run_status') or '状态未知'}")
        elif kind == "scattered":
            lines.append(f"散落待归类：{rel.get('source_hint') or rel.get('category') or '未分类'}")
    return " · ".join(dict.fromkeys(lines))


def refresh_catalog(*, repo_root: Path, data_dir: Path | None = None, output: Path | None = None,
                    inventory: Path | None = None, source_roots: Iterable[Path] = (),
                    remember_inventory: bool = False, log=None) -> dict:
    repo_root = repo_root.resolve(strict=True)
    data_dir = resolve_data_dir(repo_root, data_dir)
    output = (output or data_dir / "我的参考图")
    output = output if output.is_absolute() else repo_root / output
    source_roots = tuple(source_roots)
    requested_inventory = inventory is not None
    previous, _ = _prepare_output(output, repo_root, data_dir, source_roots)
    if inventory is None and previous.get("inventory"):
        saved = previous["inventory"]
        if isinstance(saved, dict):
            inventory = Path(str(saved.get("path") or "")) if saved.get("path") else None
            source_roots = tuple(Path(str(item)) for item in saved.get("source_roots", []) if str(item))
            remember_inventory = True
    remember_inventory = remember_inventory or requested_inventory
    if remember_inventory and inventory is not None:
        try:
            inventory = inventory.resolve(strict=True)
        except OSError as exc:
            raise CatalogError(f"盘点输入不存在：{inventory}") from exc
        if not _inside(inventory, repo_root) or _is_link_or_junction(inventory):
            raise CatalogError("盘点输入必须是当前仓库内的非链接文件")
    if log:
        log("读取只读数据库")
    projects, refs, assets, inspirations, studies, jobs = _load_database(data_dir)
    errors: list[dict] = []
    entries: dict[str, dict] = {}
    candidates: list[dict] = []
    if log:
        log(f"核验资产原件：{len(assets)}")
    for index, (sha, meta) in enumerate(assets.items(), 1):
        if not SHA_RE.fullmatch(sha):
            errors.append({"kind": "asset_invalid_sha", "asset": sha})
            continue
        path = _asset_file(data_dir, meta)
        if path is None:
            candidates.append({"sha": sha, "path": None, "title": meta.get("received_name") or sha[:12],
                               "source_kind": "asset", "missing": True})
            continue
        actual = _sha_file(path)
        if actual != sha:
            errors.append({"kind": "asset_hash_mismatch", "path": str(path), "expected": sha, "actual": actual})
            candidates.append({"sha": sha, "path": None, "title": meta.get("received_name") or sha[:12],
                               "source_kind": "asset", "missing": True, "corrupt": True})
            continue
        candidates.append({"sha": sha, "path": path, "title": meta.get("received_name") or sha[:12],
                           "source_kind": "asset"})
        if log and index % 250 == 0:
            log(f"已核验资产原件：{index}/{len(assets)}")
    if log:
        log("扫描当前与历史采集记录")
    candidates.extend(_scan_runs(repo_root, jobs, projects, errors))
    if log:
        log(f"合并盘点输入：{inventory if inventory else '未配置'}")
    inventory_rows = _read_inventory(inventory, repo_root, source_roots, errors)
    candidates.extend({**row, "source_kind": "scattered", "title": row["path"].name} for row in inventory_rows)
    referenced_shas = {str(ref.get("asset_sha") or "").lower() for ref in refs}
    for candidate in candidates:
        sha = str(candidate["sha"]).lower()
        entry = entries.setdefault(sha, {"sha": sha, "title": "", "title_priority": 0, "original_name": "", "sources": [],
                                                    "relations": [], "categories": set(), "missing": False, "corrupt": False})
        if candidate.get("path"):
            entry["sources"].append(str(candidate["path"]))
            if not entry["title"] or entry["title"] in {"未登记下载图", Path(candidate["path"]).name, sha[:12]}:
                entry["title"] = _friendly_title(candidate.get("title"), Path(candidate["path"]).name, sha=sha)
            if not entry["original_name"]:
                entry["original_name"] = str(candidate.get("title") or Path(candidate["path"]).name)
        entry["missing"] = entry["missing"] or bool(candidate.get("missing"))
        entry["corrupt"] = entry["corrupt"] or bool(candidate.get("corrupt"))
        if candidate.get("source_kind") == "collection_run":
            entry["categories"].add("角色引用" if sha in referenced_shas else "采集未入库")
            entry["relations"].append({"kind": "run", "job_id": candidate.get("job_id"),
                                       "project_id": candidate.get("project_id"),
                                       "run_status": candidate.get("run_status")})
        if candidate.get("source_kind") == "scattered":
            entry["categories"].add("散落待归类")
            entry["relations"].append({"kind": "scattered", "source_hint": candidate.get("source_hint"),
                                       "category": candidate.get("category")})
    for ref in refs:
        sha = str(ref.get("asset_sha") or "").lower()
        if not SHA_RE.fullmatch(sha):
            errors.append({"kind": "reference_without_valid_asset", "reference_id": ref.get("id"), "asset": sha})
            continue
        entry = entries.setdefault(sha, {"sha": sha, "title": "", "title_priority": 0, "original_name": "", "sources": [],
                                            "relations": [], "categories": set(), "missing": True, "corrupt": False})
        project = projects.get(str(ref.get("project_id") or ""), {})
        if entry.get("title_priority", 0) < 2:
            entry["title"] = _friendly_title(ref.get("title"), (ref.get("source") or {}).get("title"), sha=sha)
            entry["title_priority"] = 2
        entry["original_name"] = entry["original_name"] or str((ref.get("source") or {}).get("title") or "")
        entry["categories"].add("角色引用")
        entry["relations"].append({"kind": "project", "project_id": ref.get("project_id"),
                                   "character": project.get("character") or "项目记录缺失",
                                   "work": project.get("work") or "", "costume": project.get("costume") or "",
                                   "archived": bool(project.get("archived_at")), "decision": ref.get("decision"),
                                   "state": ref.get("state"), "detached": bool(ref.get("detached_at")),
                                   "lane": ref.get("lane"), "reference_id": ref.get("id")})
    for item in inspirations:
        sha = str(item.get("asset_sha") or "").lower()
        if not SHA_RE.fullmatch(sha):
            continue
        entry = entries.setdefault(sha, {"sha": sha, "title": _friendly_title(item.get("title"), sha=sha), "title_priority": 1, "original_name": "",
                                            "sources": [], "relations": [], "categories": set(), "missing": True, "corrupt": False})
        entry["categories"].add("全局收藏")
        entry["relations"].append({"kind": "favorite", "active": bool(item.get("active")), "inspiration_id": item.get("id")})
    for item in studies:
        sha = str(item.get("asset_sha") or "").lower()
        if not SHA_RE.fullmatch(sha):
            continue
        entry = entries.setdefault(sha, {"sha": sha, "title": _friendly_title(item.get("title"), sha=sha), "title_priority": 1, "original_name": "",
                                            "sources": [], "relations": [], "categories": set(), "missing": True, "corrupt": False})
        entry["categories"].add("学习候选")
        entry["relations"].append({"kind": "study", "status": item.get("status"), "study_id": item.get("id")})

    if log:
        log(f"生成派生浏览图：{len(entries)}")
    output.mkdir(parents=True, exist_ok=True)
    images_dir = output / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    _assert_no_links(images_dir, output)
    previous_previews = {row.get("sha"): row for row in previous.get("items", []) if isinstance(row, dict)}
    prior_files = previous.get("owned_files", {}) if isinstance(previous.get("owned_files"), dict) else {}
    prior_files.update(_legacy_owned_paths(output, previous, projects))
    owned_files: dict[str, str] = {}
    used_names: set[str] = set()
    result_items = []
    preview_errors = 0
    generated_previews: dict[str, str] = {}
    for sha, entry in sorted(entries.items(), key=lambda pair: (pair[1]["title"].casefold(), pair[0])):
        source = Path(entry["sources"][0]) if entry["sources"] else None
        status = "原件损坏" if entry["corrupt"] else "原件缺失" if source is None else "可浏览"
        browse_path = ""
        preview_sha = ""
        if source is not None and not entry["corrupt"]:
            base_name = _safe_name(entry["title"] or _friendly_title(entry["original_name"], sha=sha), limit=58)
            filename = f"{base_name}_{sha[:12]}.jpg"
            if filename.casefold() in used_names:
                filename = f"{base_name}_{sha}.jpg"
            used_names.add(filename.casefold())
            destination = images_dir / filename
            relative = f"images/{filename}"
            if destination.exists():
                recovered = _owned_preview(destination, relative,
                                           str(previous_previews.get(sha, {}).get("preview_sha256") or ""),
                                           prior_files)
                if recovered and not prior_files.get(relative):
                    prior_files[relative] = recovered
                if (_is_link_or_junction(destination) or not destination.is_file()
                        or not prior_files.get(relative)):
                    errors.append({"kind": "catalog_user_path_conflict", "path": relative,
                                   "reason": "用户新增或修改，保留原文件"})
                elif _sha_file(destination) == prior_files[relative]:
                    preview_sha = prior_files[relative]
                    browse_path = relative
                else:
                    errors.append({"kind": "catalog_user_path_conflict", "path": relative,
                                   "reason": "用户修改了生成文件，保留原文件"})
            if not destination.exists():
                try:
                    if not _verify_image(source):
                        raise ValueError("不是可解码的单帧图片")
                    preview_sha = _make_preview(source, destination)
                except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
                    preview_errors += 1
                    status = "原件损坏或不可解码"
                    errors.append({"kind": "preview_failed", "sha": sha, "path": str(source), "reason": str(exc)})
                    destination.unlink(missing_ok=True)
                else:
                    browse_path = relative
            if browse_path:
                generated_previews[browse_path] = preview_sha
                _record_written(owned_files, browse_path, preview_sha)
        rel_text = _relation_text(entry["relations"])
        role_groups = " ".join(dict.fromkeys(
            _canonical_group(str(projects[str(rel.get("project_id"))].get("character") or ""))
            for rel in entry["relations"]
            if rel.get("kind") in {"project", "run"} and str(rel.get("project_id") or "") in projects))
        result_items.append({"sha": sha, "title": entry["title"] or sha[:12],
                             "original_name": entry["original_name"], "status": status,
                             "original_path": str(source) if source else "",
                             "sources": list(dict.fromkeys(entry["sources"])),
                             "original_href": _file_uri(source) if source else "",
                             "browse_path": browse_path, "preview_sha256": preview_sha,
                             "relations": entry["relations"], "categories": sorted(entry["categories"]),
                             "role_groups": role_groups,
                             "relations_text": rel_text})

    role_map: dict[str, dict] = {}
    for project_id, project in projects.items():
        group = _canonical_group(str(project.get("character") or "未命名角色"))
        role = role_map.setdefault(group, {"group": group, "projects": [], "items": []})
        role["projects"].append({**project, "id": project_id})
    for item in result_items:
        for rel in item["relations"]:
            project_id = str(rel.get("project_id") or "") if rel.get("kind") in {"project", "run"} else ""
            if project_id and project_id in projects:
                group = _canonical_group(str(projects[project_id].get("character") or "未命名角色"))
                role = role_map.setdefault(group, {"group": group, "projects": []})
                if item not in role.setdefault("items", []):
                    role["items"].append(item)
    for role in role_map.values():
        role.setdefault("items", [])
    role_folder_names: dict[str, str] = {}
    used_role_names: set[str] = set()
    for role in sorted(role_map.values(), key=lambda row: row["group"].casefold()):
        name = _safe_name(role["group"], limit=80)
        if name.casefold() in used_role_names:
            name = f"{name}-{hashlib.sha256(role['group'].encode('utf-8')).hexdigest()[:8]}"
        used_role_names.add(name.casefold())
        role_folder_names[role["group"]] = f"角色项目/{name}"
    roles = [{"group": role["group"], "count": len(role["items"]), "folder": role_folder_names[role["group"]]}
             for role in sorted(role_map.values(), key=lambda row: row["group"].casefold())]
    favorites = [item for item in result_items if any(rel.get("kind") == "favorite" for rel in item["relations"])]
    study_items = [item for item in result_items if any(rel.get("kind") == "study" for rel in item["relations"])]
    unknown = [item for item in result_items if not any(
        rel.get("kind") == "favorite" or rel.get("kind") == "study" or
        (rel.get("kind") in {"project", "run"} and rel.get("project_id") in projects)
        for rel in item["relations"])]
    pages: dict[str, str] = {}
    main_roles = roles + [{"group": "全局收藏", "count": len(favorites), "folder": "其他/全局收藏"},
                          {"group": "学习候选", "count": len(study_items), "folder": "其他/学习候选"},
                          {"group": "未分类（待归属）", "count": len(unknown), "folder": "其他/未分类（待归属）"}]
    pages["index.html"] = _page("我的参考图", f"共 {len(result_items)} 张独立图片；角色关联只说明项目查找关系，不宣称已验证身份。",
                               result_items, main_roles, "")
    preview_files: dict[str, str] = {}
    previous_by_sha = {row.get("sha"): row for row in previous.get("items", []) if isinstance(row, dict)}
    for role_name, role in role_map.items():
        folder = role_folder_names[role_name]
        for item in role.get("items", []):
            preview = item.get("browse_path")
            if not preview:
                continue
            source_preview = output / preview
            relative = Path(folder) / Path(preview).name
            destination = output / relative
            old = previous_by_sha.get(item["sha"], {})
            fresh = False
            just_written = False
            if not destination.exists() and source_preview.is_file():
                digest = _owned_write(output, relative.as_posix(), source_preview.read_bytes(), prior_files, errors)
                fresh = bool(digest)
                just_written = fresh
            digest = ""
            if destination.is_file() and not _is_link_or_junction(destination):
                digest = _sha_file(destination)
                if not just_written and prior_files.get(relative.as_posix()) != digest:
                    digest = ""
            role_paths = item.setdefault("role_paths", {})
            if digest == item.get("preview_sha256"):
                role_paths[folder] = relative.as_posix()
                preview_files[relative.as_posix()] = digest
                _record_written(owned_files, relative.as_posix(), digest)
            elif digest:
                errors.append({"kind": "catalog_user_path_conflict", "path": relative.as_posix(),
                               "reason": "用户新增或修改，保留原文件"})
    for folder, items, title, subtitle in (
            ("其他/全局收藏", favorites, "全局收藏", "当前与历史收藏；移除收藏不会删除原图。"),
            ("其他/学习候选", study_items, "学习候选", "Dot 摄影待筛与学习候选，状态保持原记录。"),
            ("其他/未分类（待归属）", unknown, "未分类（待归属）", "无法证明项目归属的采集或盘点图片；不会从文件名推断角色。")):
        for item in items:
            preview = item.get("browse_path")
            if not preview:
                continue
            relative = Path(folder) / Path(preview).name
            destination = output / relative
            fresh = False
            just_written = False
            if not destination.exists() and (output / preview).is_file():
                digest = _owned_write(output, relative.as_posix(), (output / preview).read_bytes(), prior_files, errors)
                fresh = bool(digest)
                just_written = fresh
            digest = ""
            if destination.is_file() and not _is_link_or_junction(destination):
                digest = _sha_file(destination)
                if not just_written and prior_files.get(relative.as_posix()) != digest:
                    digest = ""
            role_paths = item.setdefault("role_paths", {})
            if digest == item.get("preview_sha256"):
                role_paths[folder] = relative.as_posix()
                preview_files[relative.as_posix()] = digest
                _record_written(owned_files, relative.as_posix(), digest)
            elif digest:
                errors.append({"kind": "catalog_user_path_conflict", "path": relative.as_posix(),
                               "reason": "用户新增或修改，保留原文件"})
    for role in roles:
        project_lines = "、".join(_project_label(project) for project in role_map[role["group"]]["projects"]) or "仅历史关联"
        shown = []
        for item in role_map[role["group"]]["items"]:
            shown.append({**item, "browse_path": item.get("role_paths", {}).get(role["folder"], "")})
        pages[f'{role["folder"]}/index.html'] = _page(role["group"], f"{project_lines}。包含待筛、淘汰、移出与归档项目图片。",
                                                       shown, roles, "../../")
    for folder, items, title, subtitle in (
            ("其他/全局收藏", favorites, "全局收藏", "当前与历史收藏；移除收藏不会删除原图。"),
            ("其他/学习候选", study_items, "学习候选", "Dot 摄影待筛与学习候选，状态保持原记录。"),
            ("其他/未分类（待归属）", unknown, "未分类（待归属）", "无法证明项目归属的采集或盘点图片；不会从文件名推断角色。")):
        shown = [{**item, "browse_path": item.get("role_paths", {}).get(folder, "")} for item in items]
        pages[f"{folder}/index.html"] = _page(title, subtitle, shown, main_roles, "../../")

    current_owned = {item["browse_path"] for item in result_items if item.get("browse_path")}
    current_owned |= {path for item in result_items for path in item.get("role_paths", {}).values()}
    stale = set(prior_files) - current_owned - set(preview_files) - set(pages)
    stale.add("manifest.json")
    for relative_name in stale:
        if relative_name == "manifest.json":
            continue
        relative = _relative_owned(relative_name)
        if relative is None:
            continue
        candidate = output / relative
        if not _inside(candidate, output) or not candidate.is_file() or _is_link_or_junction(candidate):
            continue
        expected = prior_files.get(relative_name)
        if not expected or _sha_file(candidate) != expected:
            errors.append({"kind": "catalog_user_path_conflict", "path": relative_name,
                           "reason": "旧生成文件已被修改，保留"})
            continue
        candidate.unlink()
        parent = candidate.parent
        while not _same_path(parent, output):
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    for relative, content in pages.items():
        digest = _owned_write(output, relative, content.encode("utf-8"), prior_files, errors)
        _record_written(owned_files, relative, digest)
    for relative, expected_sha in generated_previews.items():
        if relative in owned_files and owned_files[relative] == expected_sha and (output / relative).is_file():
            continue
        if _record_owned_file(owned_files, output / relative, relative, expected_sha, prior_files):
            continue
        errors.append({"kind": "catalog_owned_preview_unverified", "path": relative})
    for relative in sorted(preview_files):
        path = output / relative
        if not path.is_file() or _is_link_or_junction(path):
            errors.append({"kind": "catalog_owned_preview_missing", "path": relative})
            continue
        digest = _sha_file(path)
        if digest == preview_files[relative] and (relative in owned_files or _record_owned_file(
                owned_files, path, relative, preview_files[relative], prior_files)):
            owned_files[relative] = digest
        else:
            errors.append({"kind": "catalog_owned_preview_unverified", "path": relative})
    manifest = {"schema": 1, "catalog_version": CATALOG_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "generator": GENERATOR_ID, "repo_root": str(repo_root), "items": result_items, "roles": roles,
                "owned_pages": sorted(pages), "owned_files": owned_files, "errors": errors,
                "inventory": {"path": str(inventory) if inventory else "",
                              "source_roots": [str(path.resolve()) for path in source_roots]} if remember_inventory else previous.get("inventory", {}),
                "summary": {"images": len(result_items), "available": sum(item["status"] == "可浏览" for item in result_items),
                            "missing_or_corrupt": sum(item["status"] != "可浏览" for item in result_items),
                            "project_references": len(refs), "projects": len(projects), "roles": len(roles),
                            "favorites": len(favorites), "study_candidates": len(study_items), "unknown": len(unknown)}}
    _atomic_json(output / "manifest.json", manifest)
    return {"output": str(output), "manifest": str(output / "manifest.json"), **manifest["summary"],
            "errors": errors, "ok": not errors}
