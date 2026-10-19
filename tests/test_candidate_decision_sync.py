"""Human keep/reject from the candidate gallery must reach the project ref.

Failure shape (measured on the previous branch): a decision taken while Search is
still downloading, or before the finished Search imports its candidates, was only
written to ``human-decisions.json``. ``_import_search`` then created the project
reference as ``pending``, so the gallery said "人工保留" while the project said
"未选择". These tests fail before the fix and protect the sync/conflict rules.
"""
from __future__ import annotations

import hashlib
import json
import threading

from ref_lab import collection_queue, collection_stages
from ref_lab.models import JobInput
from ref_lab.service import Library
from conftest import image_bytes


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _queue_row(folder, sha: str, raw: bytes, index: int = 1, tier: str = "target_named"):
    images = folder / "images"
    images.mkdir(parents=True, exist_ok=True)
    path = images / f"{sha}.png"
    path.write_bytes(raw)
    collection_queue.write_json(folder / "received.json", [{
        "asset_sha": sha, "original_path": str(path.resolve()),
        "page_url": f"https://example.org/post/{index}", "image_url": f"https://example.org/image/{index}.png",
        "search_query": "西木野真姬 cos 摄影", "source_text": "西木野真姬 cosplay",
        "width": 800, "height": 1200,
        "relevance": {"tier": tier, "label": "名称命中 · 角色相关性待视觉核验"}}])


def _job(library, project, *, mode="search", target=2):
    return library.create_job(project["id"], JobInput(kind="collection", collection_mode=mode,
                                                      target_count=target, notes="synthetic decision sync"))


def _one_ref(library, project_id, sha):
    with library.db.read() as con:
        found = con.execute("SELECT id FROM refs WHERE project_id=? AND asset_sha=?",
                            (project_id, sha)).fetchone()
    return library.reference(found["id"]) if found else None


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(collection_queue, "run_directory", lambda job_id: tmp_path / "q")


def test_human_keep_while_search_is_running_creates_the_project_reference(
        tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    job = _job(library, project)
    attempt = "a" * 32
    library.start_collection_attempt(job["id"], job["revision"], attempt)
    raw = image_bytes(501)
    sha = _sha(raw)
    _queue_row(tmp_path / "q", sha, raw)

    response = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision",
                           json={"decision": "keep"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"][0]["status"] == "human_keep"
    decision = body.get("project_decision")
    assert decision is not None, "a running search decision must not wait for the final import"
    assert decision["decision"] == "keep"
    assert decision["decision_origin"] == "human_candidate_queue"
    # Human keep is still not an AI acceptance.
    assert decision["review"] is None


def test_decision_before_import_is_applied_when_search_imports(
        tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    job = _job(library, project)
    raw = image_bytes(502)
    sha = _sha(raw)
    _queue_row(tmp_path / "q", sha, raw)

    response = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision",
                           json={"decision": "reject"})
    assert response.status_code == 200, response.text
    immediate = _one_ref(library, project["id"], sha)
    assert immediate is not None and immediate["decision"] == "reject"
    assert immediate["decision_origin"] == "human_candidate_queue"
    # The later Search import reuses the same ref and must not downgrade it.
    imported = collection_stages._import_search(library, job["id"])
    assert imported["created"] == 0 and imported["errors"] == 0
    ref = _one_ref(library, project["id"], sha)
    assert ref["id"] == immediate["id"]
    assert ref["decision"] == "reject" and ref["decision_origin"] == "human_candidate_queue"
    assert ref["review"] is None


def test_clear_after_import_keeps_project_and_gallery_consistent(
        tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    job = _job(library, project)
    raw = image_bytes(503)
    sha = _sha(raw)
    _queue_row(tmp_path / "q", sha, raw)
    collection_stages._import_search(library, job["id"])

    kept = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "keep"})
    assert kept.status_code == 200, kept.text
    assert _one_ref(library, project["id"], sha)["decision"] == "keep"
    cleared = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "clear"})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["items"][0]["status"] == "pending"
    assert _one_ref(library, project["id"], sha)["decision"] == "pending"
    # Repeating the import must not resurrect the old keep either.
    collection_stages._import_search(library, job["id"])
    assert _one_ref(library, project["id"], sha)["decision"] == "pending"


def test_repeated_import_does_not_undo_a_human_decision(
        tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    job = _job(library, project)
    raw = image_bytes(504)
    sha = _sha(raw)
    _queue_row(tmp_path / "q", sha, raw)
    response = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "keep"})
    assert response.status_code == 200, response.text
    first = collection_stages._import_search(library, job["id"])
    second = collection_stages._import_search(library, job["id"])
    assert first["created"] == 0 and second["created"] == 0
    ref = _one_ref(library, project["id"], sha)
    assert ref["decision"] == "keep" and ref["decision_origin"] == "human_candidate_queue"
    assert ref["review"] is None


def test_import_does_not_overwrite_an_existing_formal_project_decision(
        tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    raw = image_bytes(505)
    sha = _sha(raw)
    asset = client.post("/api/assets", files={"file": ("candidate.png", raw, "image/png")})
    assert asset.status_code == 201, asset.text
    created = client.post(f"/api/projects/{project['id']}/references",
                          json={"asset_sha": sha, "title": "formal project choice"})
    assert created.status_code == 201, created.text
    ref = created.json()["reference"]
    formal = client.patch(f"/api/references/{ref['id']}", json={
        "expected_revision": ref["revision"], "decision": "keep"}).json()
    assert formal["decision_origin"] in {"human_curation", "human"}

    job = _job(library, project)
    _queue_row(tmp_path / "q", sha, raw)
    collection_queue.write_json(collection_queue.decide_path(tmp_path / "q"), {
        "version": 1, "items": {sha: {"decision": "reject", "asset_sha": sha, "actor": "human"}}})
    result = collection_stages._import_search(library, job["id"])
    assert result["conflicts"] >= 1
    current = library.reference(ref["id"])
    assert current["decision"] == "keep"
    assert current["decision_origin"] in {"human_curation", "human"}


def test_concurrent_import_and_human_decision_converge(
        tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    job = _job(library, project)
    raw = image_bytes(506)
    sha = _sha(raw)
    _queue_row(tmp_path / "q", sha, raw)
    started = threading.Event()
    release = threading.Event()
    original = Library.add_candidate
    calls = {"count": 0}

    def slow_add_candidate(self, *args, **kwargs):
        if threading.current_thread().name == "importer" and calls["count"] == 0:
            calls["count"] += 1
            started.set()
            assert release.wait(15)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Library, "add_candidate", slow_add_candidate)
    errors: list[BaseException] = []

    def import_candidates():
        try:
            collection_stages._import_search(library, job["id"])
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    importer = threading.Thread(target=import_candidates, name="importer")
    importer.start()
    assert started.wait(15)
    response = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "keep"})
    assert response.status_code == 200, response.text
    release.set()
    importer.join(20)
    assert not importer.is_alive() and not errors, errors
    ref = _one_ref(library, project["id"], sha)
    assert ref is not None
    assert ref["decision"] == "keep", "candidate-queue choice was lost by a concurrent import"
    assert ref["decision_origin"] == "human_candidate_queue"
    snapshot = collection_queue.snapshot(job["id"])
    assert snapshot["items"][0]["status"] == "human_keep"


def test_decision_survives_a_new_library_process(tmp_path, monkeypatch, library, client, project):
    _isolate(tmp_path, monkeypatch)
    job = _job(library, project)
    raw = image_bytes(507)
    sha = _sha(raw)
    _queue_row(tmp_path / "q", sha, raw)
    response = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "keep"})
    assert response.status_code == 200, response.text
    from ref_lab.api import create_app
    from fastapi.testclient import TestClient
    from conftest import TOKEN
    with TestClient(create_app(library.settings)) as fresh:
        auth = fresh.post("/api/session", json={"token": TOKEN})
        fresh.headers["X-Lab-CSRF"] = auth.json()["csrf"]
        body = fresh.get(f"/api/jobs/{job['id']}/candidates").json()
        assert body["items"][0]["status"] == "human_keep"
        refs = fresh.get(f"/api/projects/{project['id']}/references?include_rejected=1").json()
        ref = next(item for item in refs["items"] if item["asset_sha"] == sha)
        assert ref["decision"] == "keep" and ref["decision_origin"] == "human_candidate_queue"
