from __future__ import annotations

import io
import json
import stat
import zipfile
from pathlib import Path
import pytest
import yaml
from ref_lab.imports import import_candidates, import_notion, migrate_legacy, read_archive
from ref_lab.models import AnalysisResult, CandidateInput, JobInput
from ref_lab.service import Problem
from ref_lab.cli import backup, doctor
from conftest import add_reference, card_data, image_bytes, ready_reference, review_data


def archive_bytes(files: dict[str, bytes | str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items(): archive.writestr(name, data)
    return out.getvalue()


def test_candidate_package_idempotency_and_partial_failure(library, project):
    manifest = {"schema_version": 1, "batch_id": "test", "candidates": [
        {"id": "one", "file": "images/a.png", "source": {"search_category": "cosplay", "source_confirmed": True}},
        {"id": "missing", "file": "images/missing.png"}]}
    data = archive_bytes({"manifest.json": json.dumps(manifest), "images/a.png": image_bytes()})
    result = import_candidates(library, project["id"], data)
    assert result["created"] == 1 and len(result["errors"]) == 1
    ref = library.reference(result["reference_ids"][0])
    assert ref["review"] is None and ref["decision"] == "pending"
    assert not ref["source"]["source_confirmed"]
    result = import_candidates(library, project["id"], data)
    assert result["created"] == 0 and result["existing"] == 1


@pytest.mark.parametrize("path", ["../escape.jpg", "/absolute.jpg", "C:/windows.jpg", "bad\\path.jpg"])
def test_zip_path_traversal_rejected(path):
    with pytest.raises(ValueError): read_archive(archive_bytes({path: b"x"}))


def test_zip_symlink_duplicate_and_unsupported_notes_rejected(library, project):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        info = zipfile.ZipInfo("link");info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
        z.writestr(info, "../../outside")
    with pytest.raises(ValueError): read_archive(out.getvalue())
    with pytest.raises(ValueError): import_notion(library, project["id"], archive_bytes({"note.html": "<script>alert(1)</script>"}))


def test_notion_markdown_assets_and_idempotency(library, project):
    data = archive_bytes({"notes/摄影.md": "# 光线笔记\n\n![图](My%20Photo.png)\n<script>not executable</script>", "notes/My Photo.png": image_bytes(), "索引.csv": "Name,Topic\n姿势,引导\n"})
    report = import_notion(library, project["id"], data)
    assert report["notes"] == 2 and report["images"] == 1 and not report["unresolved_images"]
    notes = library.notes(project["id"])
    assert any("/api/assets/" in n["body"] for n in notes)
    import_notion(library, project["id"], data)
    assert len(library.notes(project["id"])) == 2


def test_legacy_choices_preserved_but_descriptions_not_verified(library, tmp_path):
    root = tmp_path / "legacy"
    (root / "data").mkdir(parents=True)
    (root / "pictures").mkdir()
    (root / "pictures/one.png").write_bytes(image_bytes())
    (root / "data/live_pose_decisions.json").write_text(json.dumps({"keep_ids": ["LIVE_A"]}))
    records = [{"selected_id": "SEL_A", "source_id": "LIVE_A", "file": "pictures/one.png", "width": 9000,
                "observed_pose": "单人高清写真姿势", "suitability": "适合漫展实拍参考", "direction": "A_STANDING"},
               {"id": "missing", "file": "pictures/missing.png"}]
    (root / "data/selected_candidates.yaml").write_text(yaml.safe_dump(records, allow_unicode=True), encoding="utf-8")
    report = migrate_legacy(library, root)
    assert report["created"] == 2 and report["missing"] == 1
    refs = library.references(report["project_id"])["items"]
    selected = next(r for r in refs if r["asset"])
    assert selected["decision"] == "keep" and selected["review"] is None and selected["card"] is None
    assert selected["asset"]["width"] == 800
    assert "单人高清写真姿势" in selected["legacy_notes"]
    assert not selected["field_ready"]
    second = migrate_legacy(library, root)
    assert second["created"] == 0 and second["existing"] == 2


def test_legacy_repo_relative_image_path_resolves_without_guessing(library, client, tmp_path):
    root = tmp_path / 'references/changye-huansheng'
    (root / 'staging/xhs_downloads').mkdir(parents=True)
    (root / 'staging/xhs_downloads/one.jpg').write_bytes(image_bytes())
    (root / 'staging/xhs_manifest.json').write_text(json.dumps([
        {'id': 'one', 'file': 'references/changye-huansheng/staging/xhs_downloads/one.jpg'},
        {'id': 'absent', 'file': 'references/changye-huansheng/staging/xhs_downloads/absent.jpg'}]))
    first = migrate_legacy(library, root)
    assert (first['created'], first['missing'], first['errors']) == (2, 1, [])
    refs = library.references(first['project_id'])['items']
    assert sum(bool(ref['asset']) for ref in refs) == 1
    chosen = next(ref for ref in refs if ref['asset'])
    changed = client.patch(f"/api/references/{chosen['id']}", json={"expected_revision": chosen['revision'], "decision": "keep"}).json()
    second = migrate_legacy(library, root)
    assert (second['created'], second['existing'], second['missing']) == (0, 2, 1)
    assert library.reference(chosen['id'])['decision'] == 'keep'
    assert library.reference(chosen['id'])['revision'] == changed['revision']


def test_job_cannot_fake_success_and_rejects_wrong_project(client, project, library):
    job = library.create_job(project["id"], JobInput(kind="collection"))
    assert job["status"] == "blocked"
    job = library.transition_job(job["id"], "running", job["revision"], "manual")
    with pytest.raises(Problem): library.transition_job(job["id"], "succeeded", job["revision"], "fake")
    other = client.post("/api/projects", json={"character": "另一角色"}).json()
    with pytest.raises(Problem): library.add_candidate(other["id"], CandidateInput(job_id=job["id"]))
    asset = library.ingest_asset(image_bytes())
    library.add_candidate(project["id"], CandidateInput(asset_sha=asset["id"], job_id=job["id"]))
    latest = library.job(job["id"])
    done = library.transition_job(job["id"], "succeeded", latest["revision"], "实际导入")
    assert done["status"] == "succeeded" and len(done["imported_ids"]) == 1
    with pytest.raises(Problem): library.transition_job(job["id"], "running", done["revision"], "replay")


def test_analysis_snapshot_blocks_stale_agent_result(client, project, library):
    ref = add_reference(client, project)
    ref = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"}).json()
    job = library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[ref["id"]]))
    result = AnalysisResult(review=review_data(ref["asset_sha"]), card=card_data())
    client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "preference": "新的意图"})
    with pytest.raises(Problem): library.apply_analysis(ref["id"], result, ref["revision"], "test", job["id"])
    assert library.reference(ref["id"])["card"] is None


def test_analysis_bundle_contains_individual_original_and_schema(client, project, library):
    ref = add_reference(client, project)
    ref = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": "keep"}).json()
    job = library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[ref["id"]]))
    result = client.get(f"/api/jobs/{job['id']}/download")
    assert result.status_code == 200
    with zipfile.ZipFile(io.BytesIO(result.content)) as archive:
        bundle = json.loads(archive.read("job.json"))
        assert archive.read(bundle["references"][0]["bundle_image"]) == image_bytes()
        assert "analysis-result.schema.json" in archive.namelist()


def test_backup_excludes_secrets_and_doctor_detects_corruption(client, project, library, tmp_path):
    ref = ready_reference(client, project)
    assert doctor(library)["ok"]
    report = backup(library, tmp_path / "backup.zip")
    with zipfile.ZipFile(report["backup"]) as archive:
        assert "library.sqlite3" in archive.namelist()
        assert not any("token" in name for name in archive.namelist())
    library.assets.path(ref["asset"]).write_bytes(b"corrupt")
    report = doctor(library)
    assert not report["ok"] and ref["asset_sha"] in report["missing_or_corrupt"]
