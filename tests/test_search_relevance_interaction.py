"""Interaction regressions: target defaults, continue-search and human sync."""
from __future__ import annotations

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


def test_continue_search_adds_target_without_resetting_candidates(library, client, project):
    job = _job(client, project["id"], target=4)
    updated = library.extend_search(job["id"], 10)
    assert updated["search_extra_target"] == 10
    assert updated["search_state"] == "idle"
    assert updated["target_count"] == 4
    with pytest.raises(Exception) as exc:
        library.extend_search(job["id"], 100)
    assert getattr(exc.value, "status", None) == 422


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
