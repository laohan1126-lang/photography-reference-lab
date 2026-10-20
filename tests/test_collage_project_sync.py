"""Collage children become normal project candidates, without double counting.

Synthetic regression: it protects the import and human-decision path, not any
real photograph or visual identity claim.
"""
from __future__ import annotations

import json

import pytest

from ref_lab import collage, collection_queue
from ref_lab.models import JobInput, ProjectInput
from tests.test_collage_split import _collage, _textured, _write_original


def _run_folder(tmp_path, monkeypatch, job_id):
    run_root = tmp_path / "runs"
    monkeypatch.setattr(collection_queue, "run_root", lambda: run_root)
    folder = run_root / job_id / "current"
    folder.mkdir(parents=True)
    return folder


def _project_and_job(library):
    project = library.create_project(ProjectInput(character="渡边曜", work="Love Live! Sunshine!!",
                                                  brief="合成回归，不是真实搜索"))
    job = library.create_job(project["id"], JobInput(kind="collection", notes="合成回归",
                                                     target_count=5, preferred_sources=["xiaohongshu"]))
    return project, job


def test_children_are_imported_with_crop_provenance_and_human_keep(app, tmp_path, monkeypatch):
    library = app.state.library
    project, job = _project_and_job(library)
    folder = _run_folder(tmp_path, monkeypatch, job["id"])
    parent = _write_original(folder, _collage(2, 1, tile=(800, 600)))
    single = _write_original(folder, _textured((900, 1200), 7, (60, 120, 90)), name="single.png")
    (folder / "received.json").write_text(json.dumps([parent, single]), "utf8")
    parent_record = collage.process_original(folder, parent)
    collage.process_original(folder, single)
    child_sha = parent_record["children"][0]["child_sha"]

    result = library.import_search_candidates(job["id"])
    assert result["errors"] == 0
    assert result["created"] == 4  # collage parent + 2 tiles + the non-collage original

    with library.db.read() as con:
        rows = con.execute("SELECT id, data FROM refs WHERE project_id=?",
                           (project["id"],)).fetchall()
    refs = {json.loads(row["data"])["asset_sha"]: row for row in rows}
    tiles = [ref for sha, ref in refs.items() if sha != parent["asset_sha"] and sha != single["asset_sha"]]
    assert len(tiles) == 2
    payloads = [json.loads(ref["data"]) for ref in tiles]
    assert all("拼图子图" in payload["title"] for payload in payloads)
    assert all("裁切矩形" in (payload.get("discovery_reason") or "") for payload in payloads)
    parent_payload = json.loads(refs[parent["asset_sha"]]["data"])
    assert "拼图原件" in parent_payload["title"]

    decided = library.decide_candidate_human(job["id"], child_sha, "keep")
    assert decided["project_decision"]["decision"] == "keep"
    assert decided["project_decision"]["decision_origin"] == "human_candidate_queue"
    assert decided["project_decision"]["review"] in (None, "")
    # Human keep is not AI acceptance.
    assert decided["project_decision"].get("accepted") in (None, False)


def test_import_is_repeatable_and_keeps_one_decision_per_tile(app, tmp_path, monkeypatch):
    library = app.state.library
    project, job = _project_and_job(library)
    folder = _run_folder(tmp_path, monkeypatch, job["id"])
    parent = _write_original(folder, _collage(2, 1, tile=(800, 600)))
    (folder / "received.json").write_text(json.dumps([parent]), "utf8")
    record = collage.process_original(folder, parent)
    child_sha = record["children"][1]["child_sha"]
    library.import_search_candidates(job["id"])
    library.decide_candidate_human(job["id"], child_sha, "reject")
    second = library.import_search_candidates(job["id"])
    assert second["created"] == 0
    with library.db.read() as con:
        rows = con.execute("SELECT data FROM refs WHERE project_id=?", (project["id"],)).fetchall()
    payloads = {json.loads(row["data"])["asset_sha"]: json.loads(row["data"]) for row in rows}
    assert len(payloads) == 3  # parent + two tiles, not three tiles
    assert payloads[child_sha]["decision"] == "reject"
    assert sum(1 for payload in payloads.values() if payload["asset_sha"] == child_sha) == 1
