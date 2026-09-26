"""Asset/use/discovery separation, reversible curation, and credential-free Agent handoff."""
from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from conftest import add_reference, image_bytes, ready_reference, review_data, card_data
from ref_lab.config import Settings
from ref_lab.db import SCHEMA, encode
from ref_lab.export import build_job_pack
from ref_lab.cli import doctor, backup, main
from ref_lab.imports import import_candidates, import_analyses
from ref_lab.models import JobInput, ProjectInput, CandidateInput
from ref_lab.service import Library, Problem
from ref_lab.recycle import cleanup


def choose(client, ref, decision, **extra):
    r = client.patch(f"/api/references/{ref['id']}", json={"expected_revision": ref["revision"], "decision": decision, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def save_global(client, ref):
    r = client.post(f"/api/references/{ref['id']}/inspiration", json={"expected_revision": ref["revision"]})
    assert r.status_code == 200, r.text
    return r.json()["item"]


def candidate_zip(job, **overrides):
    manifest = {"schema_version": 2, "batch_id": "synthetic-batch", "job_id": job["id"],
                "candidates": [{"id": "one", "file": "images/one.png", "title": "not proof of character",
                    "source": {"page_url": "https://example.com/posts/1", "search_query": "王昭君 cosplay", "source_confirmed": True},
                    "discovery_intent": "transferable_pose", "discovery_reason": "Synthetic protocol test only",
                    "discovery_url": "https://example.com/search?q=cosplay"}],
                "execution_report": {"producer": "synthetic-not-live-search", "status": "completed", "summary": "fixture only",
                    "source_checks": [{"source": "pinterest", "status": "untested", "detail": "No live test"}],
                    "query_log": [{"source": "synthetic", "query": "回眸", "kept": 1, "stop_reason": "fixture"}],
                    "gaps": ["No actual platform acquisition"]}}
    manifest.update(overrides)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("images/one.png", image_bytes())
    return stream.getvalue()


def age_rejections(library):
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    with library.db.transaction() as con:
        for row in con.execute("SELECT id,data FROM refs WHERE decision='reject'").fetchall():
            data = json.loads(row[1]); data["rejected_at"] = old
            con.execute("UPDATE refs SET data=? WHERE id=?", (encode(data), row[0]))
        for row in con.execute("SELECT id,data FROM inspirations WHERE active=0").fetchall():
            data = json.loads(row[1]); data["removed_at"] = old
            con.execute("UPDATE inspirations SET data=? WHERE id=?", (encode(data), row[0]))


def test_reject_hides_default_and_restore_is_reversible(client, project, library):
    ref = choose(client, add_reference(client, project), "maybe", preference="keep my note")
    ref = choose(client, ref, "reject")
    assert client.get(f"/api/projects/{project['id']}/references").json()["total"] == 0
    assert library.references(project["id"], decision="reject")["total"] == 1
    assert library.references(project["id"], include_rejected=True)["total"] == 1
    stale = client.post(f"/api/references/{ref['id']}/restore", json={"expected_revision": 1})
    assert stale.status_code == 409
    restored = client.post(f"/api/references/{ref['id']}/restore", json={"expected_revision": ref["revision"]}).json()
    assert restored["decision"] == "maybe" and restored["preference"] == "keep my note"
    assert restored["accepted_fingerprint"] is None
    assert Library(library.settings).references(project["id"])["total"] == 1


def test_global_inspiration_without_any_project(client, library):
    assert library.projects() == []
    asset = library.ingest_asset(image_bytes())
    r = client.post("/api/inspirations", json={"asset_sha": asset["id"], "title": "电影色彩", "borrow": ["色彩"]})
    assert r.status_code == 201
    item = r.json()["item"]
    assert "project_id" not in item
    assert client.get("/api/inspirations?q=色彩").json()["total"] == 1
    assert client.get(f"/api/assets/{asset['id']}/context").json()["observations"] == []
    assert library.projects() == []


def test_global_choice_does_not_claim_role_fact_or_auto_card(client, project, library):
    ref = choose(client, add_reference(client, project), "keep", lane="inspiration", preference="喜欢手势", borrow=["动作"])
    assert not ref["selected_for_project"] and ref["inspiration_id"]
    assert ref["review"] is None and ref["card"] is None and not ref["field_ready"]
    item = library.inspirations()["items"][0]
    assert item["preference"] == "喜欢手势"
    choose(client, ref, "reject")
    assert library.inspirations()["total"] == 1
    assert library.assets.path(item["asset"]).is_file()


def test_multi_project_reuse_same_bytes_without_inherited_review_or_acceptance(client, project, library):
    ref = ready_reference(client, project)
    item = save_global(client, ref)
    target = library.create_project(ProjectInput(character="食蜂操祈"))
    result = client.post(f"/api/inspirations/{item['id']}/use", json={"expected_revision": item["revision"], "project_id": target["id"]})
    assert result.status_code == 200, result.text
    reused = result.json()["reference"]
    assert reused["selected_for_project"] and reused["asset_sha"] == ref["asset_sha"]
    assert reused["review"] is None and reused["card"] is None and reused["accepted_fingerprint"] is None
    assert reused["source"]["source_confirmed"] is False
    context = library.asset_context(ref["asset_sha"])
    assert len(context["project_uses"]) == 2
    assert len(context["discoveries"]) == 1  # Reuse is not a made-up new search.
    assert all("character_match" not in o["facts"] for o in context["observations"])
    with library.db.read() as con:
        assert con.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 1
    assert library.reference(ref["id"])["field_ready"]
    assert len(library.inspiration(item["id"])["used_in_projects"]) == 2
    # Rejecting one role never destroys another role's acceptance or the global membership.
    choose(client, reused, "reject")
    age_rejections(library)
    assert cleanup(library, apply=True)["purged"] == []
    assert library.reference(ref["id"])["field_ready"]


def test_existing_rejected_reuse_preserves_user_choice(client, project, library):
    ref = choose(client, add_reference(client, project), "reject")
    item = save_global(client, ref)
    result = library.use_inspiration(item["id"], project["id"], item["revision"])
    assert not result["created"] and result["preserved_existing_choice"]
    assert result["reference"]["decision"] == "reject"
    assert result["reference"]["revision"] == ref["revision"]


def test_global_remove_restore_conflict_and_other_project_survives(client, project, library):
    ref = choose(client, add_reference(client, project), "keep")
    item = save_global(client, ref)
    r = client.patch(f"/api/inspirations/{item['id']}", json={"expected_revision": item["revision"], "active": False})
    assert r.status_code == 200
    assert library.inspirations()["total"] == 0 and library.inspirations(recycled=True)["total"] == 1
    assert library.reference(ref["id"])["selected_for_project"]
    assert client.post(f"/api/inspirations/{item['id']}/use", json={"expected_revision": item["revision"], "project_id": project["id"]}).status_code == 409
    restored = client.patch(f"/api/inspirations/{item['id']}", json={"expected_revision": r.json()["revision"], "active": True})
    assert restored.status_code == 200


def test_collection_intent_frozen_context_and_real_report(client, project, library):
    job = library.create_job(project["id"], JobInput(kind="collection", notes="完整自由要求\n只要自然手势", target_count=90))
    revised = {k: project[k] for k in ("character", "work", "costume", "brief", "gear")}
    revised["character"] = "另一角色"
    library.edit_project(project["id"], ProjectInput(**revised), project["revision"])
    bundle = library.job_bundle(job["id"])
    assert bundle["project"]["character"] == "王昭君" and bundle["job"]["notes"].endswith("只要自然手势")
    report = import_candidates(library, project["id"], candidate_zip(job), job["id"])
    assert report["created"] == 1 and report["errors"] == [] and report["job"]["status"] == "succeeded"
    ref = library.reference(report["reference_ids"][0])
    assert ref["decision"] == "pending" and ref["review"] is None and ref["card"] is None
    assert not ref["source"]["source_confirmed"]
    context = library.asset_context(ref["asset_sha"])
    assert context["discoveries"][0]["intent"] == "transferable_pose"
    assert context["discoveries"][0]["project_snapshot"]["character"] == "王昭君"
    assert context["observations"] == []
    assert library.references(project["id"], job_id=job["id"])["total"] == 1
    assert import_candidates(library, project["id"], candidate_zip(job), job["id"])["existing"] == 1


def test_wrong_job_blocked_empty_and_invalid_candidate_not_success(client, project, library):
    job = library.create_job(project["id"], JobInput(kind="collection"))
    other = library.create_job(project["id"], JobInput(kind="collection"))
    with pytest.raises(Problem): import_candidates(library, project["id"], candidate_zip(job), other["id"])
    report = import_candidates(library, project["id"], candidate_zip(job, candidates=[]), job["id"])
    assert report["job"]["status"] == "blocked" and report["created"] == 0
    report = import_candidates(library, project["id"], candidate_zip(job, candidates=[{"id": "bad", "file": "images/one.png", "review": {"kind": "cosplay_photo"}}]), job["id"])
    assert report["errors"] and report["job"]["status"] == "blocked"
    with library.db.read() as con: assert con.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0


def test_task_pack_complete_no_credentials_and_no_api_required(client, project, library, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    job = library.create_job(project["id"], JobInput(kind="collection", notes="保留所有自由要求", preferred_sources=["xiaohongshu", "pinterest"]))
    pack = build_job_pack(library, job["id"])
    with zipfile.ZipFile(pack) as z:
        assert {"job.json", "AGENT_TASK.md", "candidate-package.schema.json", "analysis-package.schema.json", "manifest.example.json"} <= set(z.namelist())
        data = json.loads(z.read("job.json"))
        assert set(data["acquisition"]["intents"]) == {"exact_character", "transferable_pose", "aesthetic"}
        assert data["job"]["notes"] == "保留所有自由要求" and data["acquisition"]["target_is_soft"]
        assert library.settings.token not in z.read("job.json").decode()
        assert "bsk doctor" in z.read("AGENT_TASK.md").decode()
    capabilities = client.get("/api/capabilities").json()
    assert not capabilities["independent_api_required"] and "openai_configured" not in capabilities


def test_agent_to_draft_to_human_accept_one_image_one_card(client, project, library):
    refs = [choose(client, add_reference(client, project, i), "keep") for i in range(2)]
    job = library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[r["id"] for r in refs]))
    assert library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[r["id"] for r in refs]))["id"] == job["id"]
    assert library.reference(refs[0]["id"])["workflow_stage"] == "waiting_analysis"
    def payload(ref, card):
        return json.dumps({"schema_version": 1, "job_id": job["id"], "items": [{"reference_id": ref["id"],
            "expected_revision": ref["revision"], "producer": "synthetic-not-vision",
            "result": {"review": review_data(ref["asset_sha"]), "card": card}}]}).encode()
    assert import_analyses(library, project["id"], payload(refs[0], card_data()), job["id"])["errors"] == []
    assert [r["id"] for r in library.job_bundle(job["id"])["references"]] == [refs[1]["id"]]
    assert import_analyses(library, project["id"], payload(refs[1], None), job["id"])["errors"] == []
    assert library.job(job["id"])["status"] == "succeeded" and library.stats(project["id"])["ready"] == 0
    ref = library.reference(refs[0]["id"])
    assert ref["workflow_stage"] == "card_draft"
    assert library.reference(refs[1]["id"])["workflow_stage"] == "analyzed"
    assert library.reference(refs[1]["id"])["card"] is None
    accepted = client.post(f"/api/references/{ref['id']}/accept", json={"expected_revision": ref["revision"],
        "source": {**ref["source"], "rights": "owned", "rights_note": "Synthetic fixture", "source_confirmed": True}})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["field_ready"] and library.stats(project["id"])["ready"] == 1
    replay = import_analyses(library, project["id"], payload(refs[0], card_data()), job["id"])
    assert replay["errors"] and library.reference(ref["id"])["field_ready"]


def test_changed_selection_and_context_do_not_export_stale_analysis(client, project, library):
    ref = choose(client, add_reference(client, project), "keep")
    job = library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[ref["id"]]))
    ref = choose(client, ref, "maybe")
    with pytest.raises(Problem): library.job_bundle(job["id"])
    assert library.reference(ref["id"])["workflow_stage"] == "candidate"


def test_global_notes_work_without_role_and_safe_import(client, library):
    response = client.post("/api/notes", json={"title": "构图经验", "body": "<script>not executed</script>"})
    assert response.status_code == 201, response.text
    assert response.json()["project_id"] is None
    assert len(client.get("/api/notes").json()) == 1
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z: z.writestr("my.md", "# note\n观察与复盘")
    imported = client.post("/api/imports/notion", files={"file": ("notes.zip", stream.getvalue())})
    assert imported.status_code == 200, imported.text
    assert library.projects() == []


def test_focus_id_opens_reused_image_not_first_page(client, project, library):
    asset = library.ingest_asset(image_bytes())
    # Null-asset legacy records avoid manufacturing 70 unnecessary image files.
    for i in range(65): library.add_candidate(project["id"], CandidateInput(title=f"metadata {i}", import_key=f"test:{i}"))
    ref = library.add_candidate(project["id"], CandidateInput(asset_sha=asset["id"], title="target"))["reference"]
    response = client.get(f"/api/projects/{project['id']}/references?focus_id={ref['id']}").json()
    assert response["offset"] == 60 and response["items"][-1]["id"] == ref["id"]


def test_cleanup_dry_run_delay_delete_restore_reimport_doctor_backup(client, project, library, tmp_path):
    ref = choose(client, add_reference(client, project), "reject")
    assert cleanup(library, apply=True)["purged"] == []
    age_rejections(library)
    preview = cleanup(library)
    assert len(preview["eligible"]) == 1 and preview["purged"] == []
    assert library.assets.path(ref["asset"]).exists()
    result = cleanup(library, apply=True)
    assert result["purged"] == [ref["asset_sha"]]
    assert not library.assets.path(ref["asset"]).exists()
    assert client.post(f"/api/references/{ref['id']}/restore", json={"expected_revision": ref["revision"]}).status_code == 409
    assert doctor(library)["ok"]
    saved = backup(library, tmp_path / "after-cleanup.zip")
    assert saved["assets"] == 1  # One metadata record; purged bytes intentionally excluded.
    assert library.ingest_asset(image_bytes())["storage_status"] == "available"
    assert client.post(f"/api/references/{ref['id']}/restore", json={"expected_revision": ref["revision"]}).status_code == 200


@pytest.mark.parametrize("protection", ["other_project", "inspiration", "note", "job"])
def test_cleanup_protects_every_active_reference(client, project, library, protection):
    ref = choose(client, add_reference(client, project), "keep")
    if protection == "other_project":
        target = library.create_project(ProjectInput(character="另一项目"))
        library.add_candidate(target["id"], CandidateInput(asset_sha=ref["asset_sha"]))
    elif protection == "inspiration": save_global(client, ref)
    elif protection == "note": client.post("/api/notes", json={"title": "图片笔记", "body": f"![image](/api/assets/{ref['asset_sha']}/preview)"})
    else: library.create_job(project["id"], JobInput(kind="analysis", reference_ids=[ref["id"]]))
    choose(client, ref, "reject"); age_rejections(library)
    assert cleanup(library, apply=True)["purged"] == []
    assert library.assets.path(ref["asset"]).exists()


def test_true_v1_migration_preserves_choices_acceptance_and_aggregates_inspiration(client, project, library, tmp_path):
    ready = ready_reference(client, project)
    a = choose(client, add_reference(client, project, 1), "keep", lane="inspiration", preference="侧光", borrow=["光线"])
    other = library.create_project(ProjectInput(character="第二角色"))
    b = library.add_candidate(other["id"], CandidateInput(asset_sha=a["asset_sha"]))["reference"]
    b = choose(client, b, "keep", lane="inspiration", preference="喜欢手势", borrow=["动作"])
    rejected = choose(client, add_reference(client, project, 2), "reject")
    client.post(f"/api/projects/{project['id']}/notes", json={"title": "旧笔记", "body": "不丢正文"})
    # Build the actual old schema, not a v2 database with a forged version number.
    old_path = library.settings.data_dir / "v1-fixture.sqlite3"
    old_tables = ("projects", "assets", "refs", "aliases", "jobs", "notes", "events")
    with sqlite3.connect(old_path) as old, library.db.read() as source:
        old.executescript(SCHEMA)
        for table in old_tables:
            rows = source.execute(f"SELECT * FROM {table}").fetchall()
            for row in rows: old.execute(f"INSERT INTO {table} VALUES({','.join('?' for _ in row)})", tuple(row))
        old.execute("PRAGMA user_version=1")
    # No open database connection remains. Preserve all asset bytes at their existing CAS paths.
    for suffix in ("", "-wal", "-shm"):
        Path(str(library.db.path)+suffix).unlink(missing_ok=True)
    old_path.rename(library.db.path)
    upgraded = Library(library.settings)
    assert upgraded.db.migration_report["from"] == 1
    assert Path(upgraded.db.migration_report["backup"]).is_file()
    assert upgraded.reference(ready["id"])["field_ready"]
    for original in (ready, a, b, rejected):
        current = upgraded.reference(original["id"])
        for key in ("decision", "lane", "preference", "borrow", "revision", "review", "card", "accepted_fingerprint"):
            assert current[key] == original[key], key
        assert upgraded.assets.verify(current["asset"])
    global_item = upgraded.inspirations()["items"][0]
    assert upgraded.inspirations()["total"] == 1
    assert {n["preference"] for n in global_item["context_notes"]} == {"侧光", "喜欢手势"}
    assert all(d["project_snapshot"] is None for d in upgraded.asset_context(a["asset_sha"])["discoveries"])
    assert upgraded.notes()[0]["body"] == "不丢正文"
    second = Library(library.settings)
    assert second.db.migration_report is None and second.inspirations()["total"] == 1
    assert doctor(second)["ok"]


def test_cli_exports_and_imports_without_provider(client, project, library, tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_DATA_DIR", str(library.settings.data_dir))
    monkeypatch.setenv("LAB_ACCESS_TOKEN", library.settings.token)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    job = library.create_job(project["id"], JobInput(kind="collection"))
    path = tmp_path / "job.zip"
    assert main(["export-job", "--job", job["id"], "--output", str(path)]) == 0
    result = tmp_path / "result.zip"; result.write_bytes(candidate_zip(job))
    assert main(["import-job", "--job", job["id"], "--input", str(result)]) == 0
    assert library.job(job["id"])["status"] == "succeeded"
