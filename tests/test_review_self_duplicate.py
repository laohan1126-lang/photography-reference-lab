"""Review must not treat the Search batch's own imported bytes as history duplicates."""
from __future__ import annotations

import hashlib
from pathlib import Path

from test_collection_stages import FakeReviewAgent, seed_search_rows

from ref_lab.collection_history import ImageHistory
from tools import collect_verified as worker


def _project_asset_copy(tmp_path: Path, row: dict) -> Path:
    """Simulate Search's pending import into the project asset store."""
    sha = row["asset_sha"]
    target = tmp_path / "project-assets" / sha[:2] / sha / "original.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(Path(row["original_path"]).read_bytes())
    return target


def test_review_does_not_quarantine_the_jobs_own_imported_candidates(tmp_path):
    task, rows = seed_search_rows(tmp_path, 2)
    copies = [_project_asset_copy(tmp_path, row) for row in rows]
    history = ImageHistory(copies)
    # Failure shape: without the exclusion the same bytes match history (self).
    assert history.match(Path(rows[0]["original_path"]))["reason"] == "same_bytes"

    agent = FakeReviewAgent()
    manifest, images, summary = worker.review_candidates(task, agent, tmp_path, history=history)

    assert agent.review_calls == 2, "self-duplicate history must not skip real vision calls"
    assert summary["counts"]["accepted"] == 2
    assert summary["stop_reason"] == "review_complete"
    assert len(manifest["candidates"]) == 2
    audit = __import__("json").loads((tmp_path / "review-audit.json").read_text("utf8"))["items"]
    assert all(item["status"] == "accepted" for item in audit.values())
    for row, copied in zip(rows, copies):
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == row["asset_sha"]
