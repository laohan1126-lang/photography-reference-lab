"""Engineering boundaries only; synthetic fixtures are not visual accuracy data."""
import sqlite3
from pathlib import Path

import pytest

from tools.learning_v1 import (fit_exemplars, grouped_components, human_label,
                               rank_pool, read_only, rule_metrics, rule_state, similarity,
                               canonical_group_hash, attach_review, check_freeze, digest, save_json)


def test_project_decisions_do_not_become_taste_labels():
    for decision in ["keep", "maybe", "pending", "reject"]:
        label = human_label({"decision": decision, "decision_origin": "human_curation"})
        assert label["aesthetic"] is None
    assert human_label({"decision": "reject", "is_aesthetic_negative": True})["aesthetic"] is None
    assert human_label({"decision": "reject", "is_aesthetic_negative": True,
                        "aesthetic_negative_origin": "human_curation"})["aesthetic"] == 0


def test_read_only_connection_rejects_writes(tmp_path):
    path = tmp_path / "db.sqlite"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE test (id INTEGER)")
    con = read_only(path)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO test VALUES(1)")
    con.close()


def test_source_character_and_near_duplicate_groups_are_transitive():
    records = [
        {"asset_sha": "a", "declared_characters": ["A"], "source_pages": ["https://x.com/p/status/1/photo/1"]},
        {"asset_sha": "b", "declared_characters": ["B"], "source_pages": ["https://x.com/p/status/1/photo/2"]},
        {"asset_sha": "c", "declared_characters": ["B"], "source_pages": ["https://x.com/q/status/2"]},
        {"asset_sha": "d", "source_pages": []}, {"asset_sha": "e", "source_pages": []},
    ]
    mapping, report = grouped_components(records)
    assert mapping["a"] == mapping["b"] == mapping["c"]
    assert mapping["d"] == mapping["e"]
    assert report["group_count"] == 2


def test_no_title_to_visual_fact_and_unknown_does_not_match():
    record = {"asset_sha": "a", "title": "perfect cosplay correct costume", "features": {}}
    assert rule_state(record) == "needs_evidence"
    record["visual"] = {"asset_sha": "stale", "observed": True, "evidence": ["visible"], "kind": "cosplay_photo", "identity": "match", "costume": "match"}
    assert rule_state(record) == "needs_evidence"


def test_missing_features_abstain_and_no_color_histogram_used():
    assert similarity({"framing": "full_body"}, {"framing": "full_body"}) == (None, 1)
    assert similarity({"framing": "full_body", "pose": "standing"}, {"framing": "full_body", "pose": "standing"}) == (2 / 6, 2)


def test_holdout_cannot_enter_fit_and_no_parametric_claim():
    with pytest.raises(ValueError, match="Holdout"):
        fit_exemplars([{"asset_sha": "a", "title": "Hoshino Ruby"}])
    model = fit_exemplars([{"asset_sha": "a", "aesthetic_label": 1,
                            "aesthetic_label_origin": "explicit_user_message", "features": {}}])
    assert model["positive_count"] == 1
    assert model["trained_parameters"] is False
    assert model["parametric_training_status"] == "NOT_TRAINABLE"


def test_baseline_stable_and_exemplar_identity_not_scored():
    pool = [{"asset_sha": "a", "features": {"pose": "standing", "framing": "full_body"}},
            {"asset_sha": "b", "features": {}}]
    model = {"exemplars": [{"asset_sha": "a", "features": pool[0]["features"]}]}
    assert [r["asset_sha"] for r in rank_pool(pool, "baseline0")] == ["a", "b"]
    assert rank_pool(pool, "candidate2", model)[0]["similarity"] is None
    with pytest.raises(ValueError, match="unique"):
        rank_pool([pool[0], pool[0]], "baseline0")


def test_no_human_truth_is_not_scorable_and_abstentions_visible():
    assert rule_metrics([])["precision"]["value"] is None
    metrics = rule_metrics([{"human_rule_origin": "human", "human_rule_label": 1, "rule_state": "needs_evidence"}])
    assert metrics["abstained"] == 1
    assert metrics["recall_including_abstentions"]["value"] == 0


def test_cross_pool_hash_uses_original_pixels_and_exif_orientation(tmp_path):
    from PIL import Image
    image = Image.new("L", (54, 48))
    image.putdata([(x * 7 + y * 11) % 256 for y in range(48) for x in range(54)])
    exif = Image.Exif()
    exif[274] = 6
    tagged = tmp_path / "tagged.png"
    rotated = tmp_path / "rotated.png"
    image.save(tagged, exif=exif)
    image.transpose(Image.Transpose.ROTATE_270).save(rotated)
    assert canonical_group_hash(tagged) == canonical_group_hash(rotated)
    assert len(canonical_group_hash(tagged)) == 16


def test_review_cannot_follow_a_replaced_image(tmp_path):
    from PIL import Image
    import hashlib
    image = tmp_path / "image.png"
    Image.new("RGB", (8, 8)).save(image)
    sha = hashlib.sha256(image.read_bytes()).hexdigest()
    record = {"asset_sha": sha, "original_path": str(image)}
    review = {"asset_sha": sha, "visual": {"asset_sha": sha, "observed": True, "evidence": ["opened image"]},
              "features": {key: "unknown" for key in ["viewpoint", "framing", "pose", "lighting", "background", "gesture"]}}
    attach_review(record, review)
    Image.new("RGB", (8, 8), (100, 100, 100)).save(image)
    with pytest.raises(ValueError, match="bytes changed"):
        attach_review(record, review)


def test_frozen_parameter_tampering_is_detected(tmp_path, monkeypatch):
    import hashlib
    import tools.learning_v1 as experiment
    monkeypatch.setattr(experiment, "ROOT", tmp_path)
    monkeypatch.setattr(experiment, "EXPERIMENT", tmp_path)
    model = tmp_path / "model.json"
    model.write_text('{"weights":[1,1]}', encoding="utf-8")
    save_json(tmp_path / "freeze.json", {"file_hashes": {"model.json": hashlib.sha256(model.read_bytes()).hexdigest()}})
    check_freeze()
    model.write_text('{"weights":[2,1]}', encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen"):
        check_freeze()
