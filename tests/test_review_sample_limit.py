"""Bounded real-review sample: stop after N images and leave the rest pending."""
from __future__ import annotations

from test_collection_stages import FakeReviewAgent, seed_search_rows

from tools import collect_verified as worker


def test_review_sample_limit_reviews_fewer_images_and_keeps_the_rest_pending(tmp_path, monkeypatch):
    task, rows = seed_search_rows(tmp_path, 4)
    monkeypatch.setenv("LAB_REVIEW_MAX_IMAGES", "2")
    agent = FakeReviewAgent()
    manifest, images, summary = worker.review_candidates(task, agent, tmp_path, history=None)

    assert agent.review_calls == 2
    assert summary["sample_limit"] == 2
    assert summary["stop_reason"] == "review_sample_limit"
    assert summary["status"] == "partial"
    assert summary["counts"]["accepted"] == 2 and summary["counts"]["pending"] == 2
    assert len(manifest["candidates"]) == 2 and len(images) == 2
    audit = __import__("json").loads((tmp_path / "review-audit.json").read_text("utf8"))["items"]
    assert sorted(item["status"] for item in audit.values()) == ["accepted", "accepted"]
    # Un-reviewed images are not written as rejected; only their absence marks them pending.
    assert len(audit) == 2 and len(rows) == 4

    # Continuing the same review consumes only the unfinished images; completed
    # judgments are never sent to the model again.
    monkeypatch.delenv("LAB_REVIEW_MAX_IMAGES")
    agent2 = FakeReviewAgent()
    manifest2, images2, summary2 = worker.review_candidates(task, agent2, tmp_path, history=None)
    assert agent2.review_calls == 2
    assert summary2["stop_reason"] == "review_complete"
    assert summary2["counts"]["accepted"] == 4 and summary2["counts"]["pending"] == 0
    assert len(manifest2["candidates"]) == 4 and len(images2) == 4


def test_review_sample_limit_zero_means_unlimited(tmp_path, monkeypatch):
    task, rows = seed_search_rows(tmp_path, 2)
    monkeypatch.setenv("LAB_REVIEW_MAX_IMAGES", "0")
    agent = FakeReviewAgent()
    manifest, images, summary = worker.review_candidates(task, agent, tmp_path, history=None)
    assert agent.review_calls == 2
    assert summary["stop_reason"] == "review_complete"
    assert summary["counts"]["accepted"] == 2
