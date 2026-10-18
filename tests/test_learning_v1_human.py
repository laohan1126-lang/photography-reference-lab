"""Synthetic engineering tests for the single-image Ruby human review.

These fixtures are not visual accuracy evidence. They verify identity binding,
dedupe, independent dimensions, persistence, frozen-input checks, honest
missing-label handling and the loopback save/report path.
"""
from __future__ import annotations

import json
import os
import re
import stat
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

from tools.learning_v1 import EXPERIMENT, check_freeze
from tools.learning_v1_human import (AlreadySubmitted, ExperimentDrift, AESTHETIC_SCORE,
                                     LABELS_FINAL, LABELS_WORKING, METRICS_FILE, REPORT_PAGE,
                                     REVIEW_PAGE, LabelStore, build_review, compute_metrics,
                                     create_server, load_image_blobs, load_labels_for_report,
                                     ndcg_at_k, score_map, verify_against_baseline,
                                     write_report)

COLORS = [(12, 24, 36), (200, 30, 40), (30, 200, 40), (40, 30, 200), (120, 120, 20), (20, 120, 120)]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_experiment(tmp_path: Path, *, duplicate: bool = False, identical: bool = False,
                    order: dict | None = None) -> Path:
    experiment = tmp_path / "experiment"
    images = experiment / "images"
    images.mkdir(parents=True)
    records = []
    for index, color in enumerate(COLORS):
        path = images / f"sample-{index}.png"
        Image.new("RGB", (8, 8), color).save(path)
        sha = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        records.append({
            "asset_sha": sha,
            "id": f"cand-{index + 1:03d}",
            "title": f"synthetic sample {index + 1}",
            "original_path": str(path),
            "width": 8,
            "height": 8,
            "dhash": f"{0x1111111111111111 * (index + 1):016x}",
            "source": {"page_url": f"https://example.com/pin/{index + 1}", "author": "", "title": f"sample {index + 1}"},
            "visual": {"asset_sha": sha, "observed": True, "evidence": ["synthetic fixture"],
                       "kind": "cosplay_photo", "identity": "uncertain", "costume": "not_required"},
            "features": {},
            "holdout_overlap_detected": False,
        })
    unique = list(records)
    pool = list(records)
    if duplicate:
        pool = pool + [dict(records[0], source={"page_url": "https://example.com/pin/duplicate"})]
    shas = [record["asset_sha"] for record in unique]
    sequences = order or {
        "baseline0": shas,
        "baseline1": shas if identical else shas[:3] + list(reversed(shas[3:])),
        "candidate2": shas if identical else list(reversed(shas)),
    }
    predictions = {}
    for method, sequence in sequences.items():
        predictions[method] = [dict(unique[shas.index(sha)], rule_state="candidate" if index < 3 else "needs_evidence")
                               for index, sha in enumerate(sequence)]
    write_json(experiment / "ruby-pool.json", pool)
    write_json(experiment / "ruby-predictions.json", predictions)
    write_json(experiment / "ruby-evaluation.json", {"at": "2026-10-18T00:00:00+00:00", "holdout_eligible_count": 6,
                                                     "overlap_quarantined": []})
    write_json(experiment / "freeze.json", {"version": 1, "at": "2026-10-18T00:00:00+00:00",
                                            "status": "SYNTHETIC_TEST_FIXTURE", "file_hashes": {}})
    write_json(experiment / "model.json", {"exemplars": []})
    (experiment / "index.html").write_text("<!doctype html><title>synthetic overview</title>", encoding="utf-8")
    return experiment


def make_labels(experiment: Path, aesthetic: dict[str, str] | None = None,
                identity: dict[str, str] | None = None) -> dict:
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    for sha, value in (aesthetic or {}).items():
        store.draft({"asset_sha": sha, "labels": {"aesthetic": value}})
    for sha, value in (identity or {}).items():
        store.draft({"asset_sha": sha, "labels": {"identity": value}})
    labels, _ = load_labels_for_report(experiment, doc)
    return {"doc": doc, "labels": labels, "store": store}


def cleanup_readonly(path: Path) -> None:
    try:
        if path.exists():
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
            path.unlink()
    except OSError:
        pass


def test_dedupe_and_page_has_one_entry_per_sha(tmp_path):
    experiment = make_experiment(tmp_path, duplicate=True)
    doc = build_review(experiment)
    assert len(doc["assets"]) == 6
    assert len(doc["duplicates"]) == 1
    page = (experiment / REVIEW_PAGE).read_text(encoding="utf-8")
    boot = json.loads(page.split("window.__BOOT__=", 1)[1].split(";window.__TOKEN__", 1)[0])
    assert len(boot["assets"]) == 6
    assert len({asset["asset_sha"] for asset in boot["assets"]}) == 6
    assert [asset["review_id"] for asset in boot["assets"]] == [f"R{index:02d}" for index in range(1, 7)]
    for term in ("candidate2", "baseline0", "baseline1", "NDCG", "规则排序", "正例相似", "similarity"):
        assert term not in page


def test_duplicate_sha_is_not_counted_twice(tmp_path):
    experiment = make_experiment(tmp_path, duplicate=True)
    doc = build_review(experiment)
    labels = LabelStore(experiment, doc).base()
    metrics = compute_metrics(doc, labels)
    assert metrics["coverage"]["assets_total"] == 6
    assert len(doc["review_order"]) == len(set(doc["review_order"])) == 6


def test_skip_is_missing_not_dislike(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    skipped_sha = doc["review_order"][0]
    store.draft({"asset_sha": skipped_sha, "labels": {}, "skipped": True})
    labels, _ = load_labels_for_report(experiment, doc)
    scores, reasons = score_map(doc, labels)
    assert scores[skipped_sha] is None
    assert reasons[skipped_sha] == "已跳过"
    assert labels["assets"][skipped_sha]["labels"]["aesthetic"] is None
    metrics = compute_metrics(doc, labels)
    assert metrics["coverage"]["missing_breakdown"]["skipped"] == 1
    assert metrics["coverage"]["aesthetic_rated"] == 0
    assert metrics["methods"]["candidate2"]["top5_like"] is None
    assert metrics["methods"]["candidate2"]["ndcg_at_5"] is None
    assert metrics["outcome"]["status"] == "NO_HUMAN_LABELS"


def test_empty_draft_is_not_persisted(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    result = store.draft({"asset_sha": doc["review_order"][0], "labels": {}, "skipped": False})
    assert result["status"] == "noop"
    assert not (experiment / LABELS_WORKING).exists()


def test_three_dimensions_do_not_overwrite_each_other(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    sha = doc["review_order"][0]
    store.draft({"asset_sha": sha, "labels": {"identity": "target_cosplay"}})
    store.draft({"asset_sha": sha, "labels": {"aesthetic": "like"}})
    store.draft({"asset_sha": sha, "labels": {"photography": "useful"}})
    entry = store.load()["assets"][sha]
    assert entry["labels"] == {"identity": "target_cosplay", "photography": "useful", "aesthetic": "like"}
    assert entry["status"] == "rated"


def test_draft_is_atomic_and_resumes_after_store_restart(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    sha = doc["review_order"][1]
    store.draft({"asset_sha": sha, "labels": {"aesthetic": "neutral"}, "reason": "构图参考"})
    assert (experiment / LABELS_WORKING).is_file()
    assert not list(experiment.glob(".*.tmp"))
    restarted = LabelStore(experiment, build_review(experiment))
    entry = restarted.load()["assets"][sha]
    assert entry["labels"]["aesthetic"] == "neutral"
    assert entry["reason"] == "构图参考"
    state = restarted.state()
    assert state["progress"]["rated"] == 1
    assert next(asset for asset in state["assets"] if asset["asset_sha"] == sha)["labels"]["aesthetic"] == "neutral"


def test_final_submission_is_write_once_and_read_only(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    sha = doc["review_order"][0]
    store.draft({"asset_sha": sha, "labels": {"aesthetic": "like"}})
    result = store.submit()
    final = experiment / LABELS_FINAL
    try:
        assert final.is_file()
        assert result["report"] == REPORT_PAGE
        assert not (final.stat().st_mode & stat.S_IWRITE)
        snapshot = json.loads(final.read_text(encoding="utf-8"))
        assert snapshot["status"] == "submitted"
        assert snapshot["snapshot"]["read_only"] is True
        assert (experiment / REPORT_PAGE).is_file()
        assert (experiment / METRICS_FILE).is_file()
        with pytest.raises(AlreadySubmitted):
            store.submit()
        with pytest.raises(AlreadySubmitted):
            store.draft({"asset_sha": sha, "labels": {"aesthetic": "dislike"}})
    finally:
        cleanup_readonly(final)


def test_no_labels_never_produce_fake_accuracy(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    labels, source = load_labels_for_report(experiment, doc)
    assert source == "NO_LABELS_FILE"
    metrics = compute_metrics(doc, labels, labels_source=source, mode="pre_submit_dry_run")
    assert metrics["outcome"]["status"] == "NO_HUMAN_LABELS"
    assert metrics["outcome"]["conclusion"] == "NOT_PROVEN"
    assert metrics["outcome"]["prior_conclusion"] == "NOT_PROVEN"
    for method in ("baseline0", "baseline1", "candidate2"):
        assert metrics["methods"][method]["top5_like"] is None
        assert metrics["methods"][method]["ndcg_at_5"] is None
        assert metrics["methods"][method]["photography_useful"] is None
        assert metrics["methods"][method]["ndcg_status"] == "MISSING_LABELS"
    written = write_report(experiment, doc, labels, mode="pre_submit_dry_run", labels_source=source)
    assert written["coverage"]["aesthetic_rated"] == 0
    page = (experiment / REPORT_PAGE).read_text(encoding="utf-8")
    assert "尚无人完成逐图评价" in page
    assert "尚无人工作答，无法判断" in page
    assert "N/A" in page
    assert "NO_RANKING_DIFFERENCE" not in page


def test_identical_rankings_report_no_ranking_difference(tmp_path):
    experiment = make_experiment(tmp_path, identical=True)
    doc = build_review(experiment)
    labels = LabelStore(experiment, doc).base()
    metrics = compute_metrics(doc, labels)
    assert metrics["ranking_difference"]["no_ranking_difference"] is True
    assert metrics["ranking_difference"]["candidate2_vs_baseline1_top5_identical"] is True
    assert metrics["ranking_difference"]["candidate2_vs_baseline1_ranking_identical"] is True
    write_report(experiment, doc, labels, mode="pre_submit_dry_run")
    page = (experiment / REPORT_PAGE).read_text(encoding="utf-8")
    assert "NO_RANKING_DIFFERENCE" in page


def test_candidate2_equal_to_rule_still_reports_no_ranking_difference(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    predictions = json.loads((experiment / "ruby-predictions.json").read_text(encoding="utf-8"))
    predictions["candidate2"] = list(predictions["baseline1"])
    write_json(experiment / "ruby-predictions.json", predictions)
    doc = build_review(experiment)
    labels = LabelStore(experiment, doc).base()
    metrics = compute_metrics(doc, labels)
    assert metrics["ranking_difference"]["no_ranking_difference"] is False
    assert metrics["ranking_difference"]["candidate2_vs_baseline1_ranking_identical"] is True
    write_report(experiment, doc, labels, mode="pre_submit_dry_run")
    page = (experiment / REPORT_PAGE).read_text(encoding="utf-8")
    assert "NO_RANKING_DIFFERENCE" in page


def test_partial_labels_are_na_and_never_zero(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    top = [record["asset_sha"] for record in doc["predictions"]["candidate2"][:5]]
    labels = make_labels(experiment, aesthetic={top[0]: "like", top[1]: "neutral"})
    method = compute_metrics(labels["doc"], labels["labels"])["methods"]["candidate2"]
    assert method["top5_rated"] == 2
    assert method["top5_missing"] == 3
    assert method["top5_like"] == 1
    assert method["ndcg_at_5"] is None
    assert method["ndcg_status"] == "MISSING_LABELS"
    coverage = compute_metrics(labels["doc"], labels["labels"])["coverage"]
    assert coverage["aesthetic_rated"] == 2
    assert coverage["aesthetic_missing"] == 4
    assert coverage["missing_breakdown"]["unrated"] == 4


def test_graded_ndcg_matches_manual_calculation(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    shas = doc["review_order"]
    ratings = {shas[0]: "like", shas[1]: "neutral", shas[2]: "dislike",
               shas[3]: "like", shas[4]: "neutral", shas[5]: "dislike"}
    labels = make_labels(experiment, aesthetic=ratings)
    labels["store"].submit()
    labels, _ = load_labels_for_report(experiment, doc)
    metrics = compute_metrics(doc, labels)
    assert metrics["outcome"]["status"] == "SCORED"
    scores = {sha: AESTHETIC_SCORE[value] for sha, value in ratings.items()}
    ranking = [record["asset_sha"] for record in doc["predictions"]["candidate2"]]
    expected = ndcg_at_k(ranking, scores)
    assert expected is not None
    assert metrics["methods"]["candidate2"]["ndcg_at_5"] == pytest.approx(expected)
    # Recompute the same graded NDCG independently from the actual top-5 relevance order.
    import math
    relevances = [scores[sha] for sha in ranking[:5]]
    dcg = sum((2 ** relevance - 1) / math.log2(position + 2)
              for position, relevance in enumerate(relevances))
    ideal = sorted(relevances, reverse=True)
    idcg = sum((2 ** relevance - 1) / math.log2(position + 2)
               for position, relevance in enumerate(ideal))
    manual = dcg / idcg
    assert expected == pytest.approx(manual)
    assert metrics["methods"]["candidate2"]["top5_like"] == sum(1 for value in relevances if value == 2)
    assert metrics["outcome"]["candidate2_exceeds_both_baselines"] in (True, False)
    assert metrics["outcome"]["conclusion"] == "NOT_PROVEN"


def test_interrupted_or_changed_frozen_inputs_are_refused(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    store = LabelStore(experiment, doc)
    store.draft({"asset_sha": doc["review_order"][0], "labels": {"aesthetic": "like"}})
    pool = json.loads((experiment / "ruby-pool.json").read_text(encoding="utf-8"))
    pool[0]["title"] = "changed after review"
    write_json(experiment / "ruby-pool.json", pool)
    with pytest.raises(ExperimentDrift, match="inputs changed"):
        LabelStore(experiment, build_review(experiment)).load()


def test_images_are_verified_and_loaded_from_bytes(tmp_path):
    experiment = make_experiment(tmp_path)
    doc = build_review(experiment)
    blobs = load_image_blobs(doc)
    assert set(blobs) == {asset["asset_sha"] for asset in doc["assets"]}
    for sha, (data, content_type) in blobs.items():
        assert __import__("hashlib").sha256(data).hexdigest() == sha
        assert content_type.startswith("image/")


def test_loopback_http_save_resume_submit_and_report(tmp_path):
    experiment = make_experiment(tmp_path)
    server = create_server(experiment, 0)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, *, method="GET", payload=None, token=True):
        headers = {"X-Review-Token": server.token} if token else {}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()

    try:
        status, page = request("/")
        assert status == 200
        assert server.token.encode() in page
        assert b"TOKEN.length > 20" in page
        assert b"TOKEN.indexOf" not in page
        status, overview = request("/index.html")
        assert status == 200 and b"synthetic overview" in overview
        assert not (experiment / LABELS_WORKING).exists()
        status, body = request("/api/state")
        state = json.loads(body)
        assert len(state["assets"]) == 6 and state["submitted"] is False
        sha = state["assets"][0]["asset_sha"]
        status, body = request("/api/draft", method="POST",
                               payload={"asset_sha": sha, "labels": {"identity": "target_cosplay",
                                                                    "photography": "useful",
                                                                    "aesthetic": "like"},
                                        "reason": "合成浏览器路径"})
        assert status == 200 and json.loads(body)["ok"] is True
        # Simulate a refreshed page: a brand new state read must return the saved draft.
        status, body = request("/api/state")
        refreshed = json.loads(body)
        saved = next(asset for asset in refreshed["assets"] if asset["asset_sha"] == sha)
        assert saved["labels"] == {"identity": "target_cosplay", "photography": "useful", "aesthetic": "like"}
        assert saved["reason"] == "合成浏览器路径"
        status, image = request("/image/" + sha)
        assert status == 200 and image
        status, body = request("/api/submit", method="POST")
        assert status == 200 and json.loads(body)["ok"] is True
        status, body = request("/api/state")
        assert json.loads(body)["submitted"] is True
        status, report = request("/ruby-human-report.html")
        assert status == 200 and "结果表".encode() in report
        with pytest.raises(urllib.error.HTTPError) as denied:
            request("/api/draft", method="POST", payload={"asset_sha": sha, "labels": {}})
        assert denied.value.code == 409
        with pytest.raises(urllib.error.HTTPError) as forbidden:
            request("/api/state", token=False)
        assert forbidden.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        cleanup_readonly(experiment / LABELS_FINAL)


def test_pre_submit_report_is_explicitly_refused_without_flag(tmp_path):
    experiment = make_experiment(tmp_path)
    from tools.learning_v1_human import main
    with pytest.raises(SystemExit):
        main(["report", "--experiment", str(experiment)])
    assert not (experiment / REPORT_PAGE).exists()
    main(["report", "--experiment", str(experiment), "--allow-unsubmitted"])
    assert (experiment / REPORT_PAGE).is_file()


def test_real_frozen_experiment_hashes_still_verify():
    if not (EXPERIMENT / "freeze.json").is_file():
        pytest.skip("Real frozen experiment is not present in this checkout")
    frozen = check_freeze()
    assert frozen["status"] == "FROZEN_BEFORE_RUBY_SEARCH"
    assert len(frozen["file_hashes"]) == 20


def test_optional_real_baseline_comparison_still_passes():
    baseline = EXPERIMENT / "human-review-before.json"
    if not baseline.is_file():
        pytest.skip("No recorded private baseline in this checkout")
    result = verify_against_baseline(EXPERIMENT, baseline)
    assert result["pass"] is True, result["failures"]
