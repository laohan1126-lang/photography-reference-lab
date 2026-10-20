"""Offline proof that Review consumes the real Search output without re-searching.

The visual verdicts in this test are synthetic (a fake in-process agent), so it is
not evidence of character accuracy. It proves the data flow: same original bytes,
same job binding, per-image audit, schema3 package, no new browser/network call.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from ref_lab.verified_collection import CollectionVision, NamePlan, scope_sha
from tools import collect_verified as worker

SOURCE = Path(r"D:\AI PROJECTS\photography-reference-lab\.local\worktrees"
              r"\search-review-decouple-20261020\root\.local\collection-runs"
              r"\549b320fa82343e9911d5f1c4a919c42\current")
pytestmark = pytest.mark.skipif(not (SOURCE / "search-summary.json").is_file(),
                                reason="owner's accepted real Search run is not present")


class ReviewAgent:
    producer = "synthetic-review-agent-for-data-flow-only"
    candidate_calls = 0
    vision_cli_calls = 0
    candidate_limit = 20
    deadline = float("inf")

    def __init__(self, model):
        self.model = model
        self.references = []
        self.review_calls = 0

    def plan(self, project):
        return NamePlan(names=[project["character"]])

    def prepare(self, project, plan):
        self.references = [{"asset_sha": "e" * 64, "path": str(Path(__file__)),
                            "page_url": "https://example.org/synthetic-reference",
                            "label": "synthetic reference", "authority": "official_licensed_manufacturer"}]

    def review(self, path, project):
        self.review_calls += 1
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return CollectionVision(
            asset_sha=sha, context_sha=scope_sha(project), kind="cosplay_photo",
            identity="match", costume="not_required", confidence="high",
            kind_evidence=["synthetic single real-photo frame"],
            identity_evidence=["synthetic flow-test evidence"],
            costume_evidence=[], photography_usable="yes",
            photography_evidence=["synthetic flow-test evidence"],
            reason="Synthetic flow test; not a character or aesthetic judgment.",
            reference_comparisons=[{"reference_sha": "e" * 64, "assessment": "supports",
                                    "scope": "identity",
                                    "supporting_features": ["synthetic feature one", "synthetic feature two"],
                                    "conflicting_features": []}])


def test_review_reuses_real_search_originals_and_produces_schema3(tmp_path):
    folder = tmp_path / "run"
    (folder / "images").mkdir(parents=True)
    for name in ("received.json", "collector-state.json", "search-summary.json", "duplicates.json",
                 "run-info.json", "name-plan.json"):
        shutil.copy2(SOURCE / name, folder / name)
    for image in (SOURCE / "images").iterdir():
        shutil.copy2(image, folder / "images" / image.name)
    task = json.loads((SOURCE / "task" / "job.json").read_text("utf8"))
    job = task.get("job") or task
    received = json.loads((folder / "received.json").read_text("utf8"))
    for row in received:
        row["original_path"] = str(folder / "images" / Path(row["original_path"]).name)
    (folder / "received.json").write_text(json.dumps(received, ensure_ascii=False), encoding="utf8")
    state = json.loads((folder / "collector-state.json").read_text("utf8"))
    state["received"] = received
    (folder / "collector-state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf8")
    model = json.loads((folder / "run-info.json").read_text("utf8"))["model"]
    agent = ReviewAgent(model)
    manifest, images, summary = worker.review_candidates(job, agent, folder, history=None)
    assert agent.review_calls == 4
    assert len(manifest["candidates"]) == len(images) == 4
    assert summary["counts"]["accepted"] == 4
    by_prefix = {row["asset_sha"][:20]: row["asset_sha"] for row in received}
    for candidate in manifest["candidates"]:
        prefix = candidate["id"].removeprefix("verified-")
        assert by_prefix[prefix] == hashlib.sha256(images[Path(candidate["file"]).name]).hexdigest()
    result = folder / "review-result.zip"
    worker.write_result(result, manifest, images)
    assert result.is_file()
