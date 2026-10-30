"""Interaction regressions: target defaults, continue-search and human sync."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ref_lab import collection_queue
from ref_lab.models import JobInput
from conftest import image_bytes


def _job(client, project_id, target=4):
    response = client.post(f"/api/projects/{project_id}/jobs", json={
        "kind": "collection", "collection_mode": "search", "target_count": target,
        "notes": "synthetic interaction regression"})
    assert response.status_code == 201, response.text
    return response.json()


def _queue_row(tmp_path, monkeypatch, job_id, asset_sha, raw):
    root = tmp_path / "runs"
    monkeypatch.setattr(collection_queue, "run_root", lambda: root)
    folder = root / job_id / "current"
    images = folder / "images"
    images.mkdir(parents=True)
    path = images / f"{asset_sha}.png"
    path.write_bytes(raw)
    collection_queue.write_json(folder / "received.json", [{
        "asset_sha": asset_sha, "original_path": str(path.resolve()),
        "page_url": "https://example.org/post", "image_url": "https://example.org/image.png",
        "search_query": "西木野真姬 cos 摄影", "source_text": "西木野真姬 cosplay",
        "width": 800, "height": 1200,
        "relevance": {"tier": "target_named", "label": "名称命中 · 角色相关性待视觉核验"}}])
    return folder


def test_default_target_is_30_and_api_limit_is_100():
    assert JobInput(kind="collection").target_count == 30
    assert JobInput(kind="collection", target_count=100).target_count == 100
    with pytest.raises(ValidationError):
        JobInput(kind="collection", target_count=101)


def test_continue_search_adds_target_without_resetting_candidates(library, client, project, tmp_path, monkeypatch):
    from ref_lab import service
    monkeypatch.setattr(service, "__file__", str(tmp_path / "ref_lab/service.py"))
    monkeypatch.setenv("LAB_DATA_DIR", str(library.settings.data_dir))
    monkeypatch.setenv("LAB_COLLECTION_HISTORY_ROOTS", "[]")
    job = _job(client, project["id"], target=4)
    _, claimed = library.begin_job_preparation(job["id"], "prepare", {})
    assert claimed
    library.prepare_job(job["id"], "prepare")
    updated = library.extend_search(job["id"], 10)
    assert updated["search_extra_target"] == 10
    assert updated["search_state"] == "idle"
    assert updated["target_count"] == 4
    with pytest.raises(Exception) as exc:
        library.extend_search(job["id"], 100)
    assert getattr(exc.value, "status", None) == 422


def test_zero_budget_extension_recovers_dead_owner_and_preserves_same_job_state(
        tmp_path, monkeypatch, library, client, project):
    from ref_lab import agent_collection
    from ref_lab.db import encode

    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "runs")
    job = _job(client, project["id"], target=4)
    raw = image_bytes(88)
    sha = hashlib.sha256(raw).hexdigest()
    folder = _queue_row(tmp_path, monkeypatch, job["id"], sha, raw)
    decision = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision", json={"decision": "keep"})
    assert decision.status_code == 200, decision.text
    original_path = folder / "images" / f"{sha}.png"
    human_path = collection_queue.decide_path(folder)
    original_before = original_path.read_bytes()
    human_before = human_path.read_bytes()

    with library.db.transaction() as con:
        row = con.execute("SELECT data FROM jobs WHERE id=?", (job["id"],)).fetchone()
        stored = json.loads(row["data"])
        stored.update(status="running", search_state="running", active_attempt_id="dead-attempt",
                      search_attempt_id="dead-attempt", search_attempt_started_at=123.0,
                      collection_process_owner={"pid": 999999}, preparation_state="ready",
                      search_timeout_seconds=1375.0, goal_id="")
        con.execute("UPDATE jobs SET status='running',data=? WHERE id=?", (encode(stored), job["id"]))

    running = library.job(job["id"])
    monkeypatch.setattr(agent_collection, "_process_owner_active", lambda owner: True)
    with pytest.raises(Exception) as active:
        library.extend_search(job["id"], 10, additional_seconds=0)
    assert getattr(active.value, "status", None) == 409
    assert library.job(job["id"]) == running

    monkeypatch.setattr(agent_collection, "_process_owner_active", lambda owner: False)
    updated = library.extend_search(job["id"], 10, additional_seconds=0)
    assert updated["id"] == job["id"]
    assert updated["search_extra_target"] == 10
    assert updated["target_count"] == 4
    assert updated["download_target_count"] == 14
    assert updated["search_timeout_seconds"] == 1375.0
    assert updated["search_state"] == "idle" and updated["status"] == "blocked"
    assert updated["search_resume_generation"] == running.get("search_resume_generation", 0) + 1
    assert "active_attempt_id" not in updated and "collection_process_owner" not in updated
    assert original_path.read_bytes() == original_before
    assert human_path.read_bytes() == human_before
    assert library.reference(decision.json()["project_decision"]["id"])["decision"] == "keep"


@pytest.mark.parametrize("additional_seconds", [-1, 901, 1.5, True])
def test_extend_search_rejects_invalid_additional_seconds(library, client, project, additional_seconds):
    job = _job(client, project["id"], target=4)
    with pytest.raises(Exception) as error:
        library.extend_search(job["id"], 1, additional_seconds=additional_seconds)
    assert getattr(error.value, "status", None) == 422


def test_user_alias_is_used_in_job_queries(client, project):
    response = client.post(f"/api/projects/{project['id']}/jobs", json={
        "kind": "collection", "collection_mode": "search", "target_count": 30,
        "search_aliases": ["Maki-Custom"]})
    assert response.status_code == 201, response.text
    job = response.json()
    assert any("Maki-Custom" in query for query in job["queries"])


def test_human_candidate_keep_syncs_to_project_and_is_not_overwritten(
        tmp_path, monkeypatch, library, client, project):
    raw = image_bytes(77)
    asset = client.post("/api/assets", files={"file": ("candidate.png", raw, "image/png")})
    assert asset.status_code == 201, asset.text
    sha = asset.json()["id"]
    created = client.post(f"/api/projects/{project['id']}/references", json={
        "asset_sha": sha, "title": "549b-style generic candidate"})
    assert created.status_code == 201, created.text
    ref = created.json()["reference"]
    job = _job(client, project["id"], target=4)
    _queue_row(tmp_path, monkeypatch, job["id"], sha, raw)

    response = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision",
                           json={"decision": "keep"})
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["status"] == "human_keep"
    current = library.reference(ref["id"])
    assert current["decision"] == "keep"
    assert current["decision_origin"] == "human_candidate_queue"

    # A later formal human choice in the project is authoritative. The gallery
    # must not silently overwrite it with the older candidate-queue value.
    patched = client.patch(f"/api/references/{ref['id']}", json={
        "expected_revision": current["revision"], "decision": "keep"})
    assert patched.status_code == 200, patched.text
    conflict = client.post(f"/api/jobs/{job['id']}/candidates/{sha}/decision",
                           json={"decision": "reject"})
    assert conflict.status_code == 409
    assert library.reference(ref["id"])["decision"] == "keep"
