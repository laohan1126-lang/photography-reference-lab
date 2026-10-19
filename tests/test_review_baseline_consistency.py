"""Read-only consistency check for the four accepted baseline photographs.

The private run is intentionally not copied into Git. When the owner's local
artifacts are present this test proves that the frozen ``accepted`` /
``CollectionVision`` / schema3 packaging contract still classifies the same four
originals the same way and preserves the same bytes. It makes no model call.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ref_lab.verified_collection import accepted, CollectionVision, scope_sha
from tools import collect_verified as worker

BASELINE = Path(r"D:\AI PROJECTS\photography-reference-lab\.local\worktrees"
                r"\collection-performance-20261019\root\.local\supply-ui-fixed-20261019")

pytestmark = pytest.mark.skipif(not (BASELINE / "manifest.json").is_file(),
                                reason="owner's private four-photo baseline is not present")


def _json(name):
    return json.loads((BASELINE / name).read_text("utf8"))


def test_four_accepted_baseline_judgments_and_bytes_are_unchanged(tmp_path):
    job = _json("job.json")
    project = {**job["project_snapshot"], "notes": ""}
    manifest = _json("manifest.json")
    audit = _json("visual-audit.json")
    references = _json("reference-research/report.json")["references"]
    assert len(audit) == 4 and len(manifest["candidates"]) == 4
    assert scope_sha(project)
    received = []
    items = {}
    for index, record in enumerate(audit):
        source = BASELINE / "images" / (record["asset_sha"] + ".webp")
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record["asset_sha"]
        target = tmp_path / "images" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        row = {"asset_sha": record["asset_sha"], "original_path": str(target),
               "page_url": record["source_page"], "image_url": "https://example.org/image",
               "width": 1040, "height": 1560, "search_query": "baseline query"}
        received.append(row)
        value = CollectionVision.model_validate(record["review"])
        assert value.context_sha == scope_sha(project)
        assert accepted(value, project, references=references) is True
        assert record["accepted"] is True
        items[record["asset_sha"]] = {
            "asset_sha": record["asset_sha"], "status": "accepted", "accepted": True,
            "decision": record["decision"], "review": record["review"], "references": references,
            "attempts": 1, "completed_at": 0,
        }
    state = {"batch_id": manifest["batch_id"], "checks": {}, "queries": []}
    packaged, images, summary = worker._review_package(
        job, project, tmp_path, state, received, items, {}, status="completed",
        stop_reason="review_complete", started=0, agent=SimpleNamespace(producer="four-photo-consistency"))
    assert len(packaged["candidates"]) == 4 and len(images) == 4
    assert [c["id"] for c in packaged["candidates"]] == [
        "verified-" + record["asset_sha"][:20] for record in audit]
    assert all(c["preflight"]["identity_prediction"] == "match" for c in packaged["candidates"])
    assert summary["counts"]["accepted"] == 4
    for record in audit:
        assert hashlib.sha256(images[record["asset_sha"] + ".webp"]).hexdigest() == record["asset_sha"]


def test_no_visual_review_call_is_made_during_the_consistency_projection(tmp_path, monkeypatch):
    job = _json("job.json")
    project = {**job["project_snapshot"], "notes": ""}
    audit = _json("visual-audit.json")
    references = _json("reference-research/report.json")["references"]
    received = []
    items = {}
    for record in audit:
        source = BASELINE / "images" / (record["asset_sha"] + ".webp")
        target = tmp_path / source.name
        target.write_bytes(source.read_bytes())
        received.append({"asset_sha": record["asset_sha"], "original_path": str(target),
                         "page_url": record["source_page"], "image_url": "https://example.org/image"})
        items[record["asset_sha"]] = {"asset_sha": record["asset_sha"], "status": "accepted",
                                       "accepted": True, "decision": "CONFIRMED",
                                       "review": record["review"], "references": references}
    monkeypatch.setattr(worker, "AntigravityCollectionAgent",
                        lambda *a, **k: pytest.fail("Consistency projection must not instantiate a model agent"))
    worker._review_package(job, project, tmp_path, {"batch_id": "x", "checks": {}, "queries": []},
                           received, items, {}, status="completed", stop_reason="baseline",
                           started=0, agent=SimpleNamespace(producer="four-photo-consistency"))
    assert references and all(accepted(CollectionVision.model_validate(record["review"]), project,
                                        references=references) for record in audit)
