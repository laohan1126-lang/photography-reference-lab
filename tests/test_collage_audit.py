"""Audit regressions: denser grids, record version, integrity, canonical counts.

These encode the *correct* behaviour agreed for the audit. The previous build
failed several of them: a 4-part grid was cut as two large blocks, an old-version
record was reused as a valid result, a damaged tile was silently regenerated, and
the web/queue/summary counts could disagree with the search target.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from PIL import Image

from ref_lab import collage, collection_queue
from ref_lab.collection_counts import compute
from ref_lab.integrity import reset_cache, sha_matches
from tests.test_collage_split import _collage, _textured, _write_original


@pytest.fixture(autouse=True)
def _fresh_integrity_cache():
    reset_cache()
    yield
    reset_cache()


def _run_root(tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    (root / "job-audit" / "current").mkdir(parents=True)
    return root


def _folder(tmp_path: Path) -> Path:
    return _run_root(tmp_path) / "job-audit" / "current"


def _make_run(tmp_path: Path, *, rows=2, cols=1, tile=(800, 600), name="parent.png"):
    folder = _folder(tmp_path)
    row = _write_original(folder, _collage(rows, cols, tile=tile), name=name)
    row["relevance"] = {"tier": "target_named", "label": "名称命中"}
    record = collage.process_original(folder, row)
    return folder, row, record


def _rewrite_record(folder: Path, parent_sha: str, mutator) -> dict:
    path = folder / "derived.json"
    data = json.loads(path.read_text("utf8"))
    mutator(data["items"][parent_sha])
    path.write_text(json.dumps(data, ensure_ascii=False), "utf8")
    return data["items"][parent_sha]


# --- detection --------------------------------------------------------------

@pytest.mark.parametrize("rows,cols,tile,reason", [
    (4, 1, (800, 600), "dense_grid_4_part"),
    (1, 4, (800, 600), "dense_grid_4_part"),
    (4, 4, (600, 480), "dense_grid_4_part"),
    (2, 4, (800, 600), "dense_grid_4_part"),
    (5, 1, (800, 600), "dense_grid_5_part"),
])
def test_dense_grid_is_for_manual_cropping_and_counts_nothing(tmp_path, rows, cols, tile, reason):
    folder, row, record = _make_run(tmp_path, rows=rows, cols=cols, tile=tile)
    assert record["status"] == collage.STATUS_NEEDS_MANUAL
    assert record["reason"] == reason
    assert record["children"] == []
    counts = compute(folder, [row], {row["asset_sha"]: record})
    assert counts["usable_independent"] == 0
    assert counts["awaiting_manual"] == 1


@pytest.mark.parametrize("rows,cols,layout", [
    (2, 1, "grid_2x1"), (1, 2, "grid_1x2"), (2, 2, "grid_2x2"),
    (3, 1, "grid_3x1"), (3, 3, "grid_3x3"),
])
def test_supported_grids_still_split(tmp_path, rows, cols, layout):
    folder, row, record = _make_run(tmp_path, rows=rows, cols=cols)
    assert record["status"] in {collage.STATUS_SPLIT_OK, collage.STATUS_SPLIT_PARTIAL}
    assert record["layout"] == layout


def test_dense_grid_never_falls_back_to_a_coarse_two_block_split(tmp_path):
    """A 4-row grid also satisfies a 2-part split; that must not be used."""
    folder, row, record = _make_run(tmp_path, rows=4, cols=1)
    assert record["rows"] == 1 and record["cols"] == 1
    assert record["children"] == []
    assert record["detections"]["row_parts_found"] == [2, 4]


# --- version, integrity, migration -----------------------------------------

def test_old_version_record_is_snapshotted_then_recomputed(tmp_path):
    folder, row, record = _make_run(tmp_path)
    old_children = [child["child_sha"] for child in record["children"]]
    _rewrite_record(folder, row["asset_sha"], lambda value: value.pop("algorithm_version", None))
    again = collage.process_original(folder, row)
    assert again["algorithm_version"] == collage.ALGORITHM_VERSION
    assert again["previous_algorithm_version"] == "legacy"
    snapshots = list((folder / "derived-snapshots").glob("*.json"))
    assert snapshots and again["previous_record_snapshot"] == str(snapshots[0])
    for sha in old_children:
        assert (folder / "derived" / f"{sha}.png").is_file()


def test_read_only_view_reports_outdated_record_without_migrating(tmp_path, monkeypatch):
    folder, row, record = _make_run(tmp_path)
    (folder / "received.json").write_text(json.dumps([row]), "utf8")
    _rewrite_record(folder, row["asset_sha"], lambda value: value.pop("algorithm_version", None))
    before = (folder / "derived.json").read_bytes()
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "runs")
    snapshot = collection_queue.snapshot("job-audit", limit=20)
    assert snapshot["counts"]["outdated_records"] == 1
    assert snapshot["counts"]["usable_independent"] == 0
    assert [item for item in snapshot["items"] if item["derived"]] == []
    assert any(item["collage"] and item["collage"]["outdated"] for item in snapshot["items"])
    assert (folder / "derived.json").read_bytes() == before


def test_corrupt_child_is_kept_and_excluded_from_counts(tmp_path):
    folder, row, record = _make_run(tmp_path)
    child = record["children"][0]
    target = Path(child["path"])
    target.write_bytes(b"damaged-bytes")
    again = collage.process_original(folder, row)
    assert again["status"] in {collage.STATUS_SPLIT_PARTIAL, collage.STATUS_SPLIT_OK}
    assert again["reason"].startswith("integrity_failure:")
    assert target.read_bytes() == b"damaged-bytes"          # never overwritten
    assert any(item["status"] == collage.CORRUPT for item in again["children"])
    counts = compute(folder, [row], {row["asset_sha"]: again})
    assert counts["derived_valid"] == 1                     # the intact sibling
    assert counts["usable_independent"] == 1
    assert counts["integrity_failures"] == 1                # anomaly visible
    assert counts["awaiting_manual"] == 1


def test_missing_child_is_not_regenerated(tmp_path):
    folder, row, record = _make_run(tmp_path)
    child = record["children"][1]
    Path(child["path"]).unlink()
    again = collage.process_original(folder, row)
    assert not Path(child["path"]).exists()                 # not regenerated
    assert any(item["status"] == collage.CORRUPT for item in again["children"])
    counts = compute(folder, [row], {row["asset_sha"]: again})
    assert counts["derived_valid"] == 1 and counts["integrity_failures"] == 1


def test_changed_original_marks_failed_and_preserves_bytes(tmp_path):
    folder, row, record = _make_run(tmp_path)
    original = Path(row["original_path"])
    original.write_bytes(b"replaced-original")
    again = collage.process_original(folder, row)
    assert again["status"] == collage.STATUS_FAILED
    assert original.read_bytes() == b"replaced-original"
    counts = compute(folder, [row], {row["asset_sha"]: again})
    assert counts["usable_independent"] == 0
    assert counts["integrity_failures"] == 1


def test_child_path_outside_derived_is_rejected(tmp_path):
    folder, row, record = _make_run(tmp_path)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not-a-tile")

    def mutate(value):
        value["children"][0]["path"] = str(outside)
    _rewrite_record(folder, row["asset_sha"], mutate)
    again = collage.process_original(folder, row)
    assert again["status"] == collage.STATUS_FAILED
    assert "child_path_outside_derived" in again["reason"]


def test_child_parent_binding_mismatch_is_rejected(tmp_path):
    folder, row, record = _make_run(tmp_path)
    _rewrite_record(folder, row["asset_sha"],
                    lambda value: value["children"][0].__setitem__("parent_sha", "f" * 64))
    again = collage.process_original(folder, row)
    assert again["status"] == collage.STATUS_FAILED
    assert "child_parent_mismatch" in again["reason"]


def test_integrity_cache_invalidates_when_the_file_changes(tmp_path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"one")
    sha = hashlib.sha256(b"one").hexdigest()
    assert sha_matches(path, sha)
    os.utime(path, ns=(1, 1))
    path.write_bytes(b"two")
    os.utime(path, ns=(2, 2))
    assert not sha_matches(path, sha)


def test_recompute_with_new_child_sha_does_not_inherit_old_decision(tmp_path):
    folder, row, record = _make_run(tmp_path)
    old_shas = [child["child_sha"] for child in record["children"]]
    # Build a legacy record whose children are the old files but a different
    # algorithm version: the recomputation will produce the current crops.
    legacy_children = []
    for index, child in enumerate(record["children"]):
        legacy_path = folder / "derived" / f"legacy-{index}.png"
        # A different algorithm would have produced different crop bytes.
        legacy_path.write_bytes(b"legacy-tile-" + str(index).encode())
        legacy = dict(child)
        legacy["child_sha"] = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
        legacy["path"] = str(legacy_path)
        legacy_children.append(legacy)

    def mutate(value):
        value.pop("algorithm_version", None)
        value["children"] = legacy_children
    _rewrite_record(folder, row["asset_sha"], mutate)
    decisions = {"version": 1, "items": {legacy_children[0]["child_sha"]: {
        "decision": "keep", "asset_sha": legacy_children[0]["child_sha"], "actor": "human"}}}
    (folder / "human-decisions.json").write_text(json.dumps(decisions), "utf8")

    again = collage.process_original(folder, row)
    assert again["algorithm_version"] == collage.ALGORITHM_VERSION
    new_shas = [child["child_sha"] for child in again["children"]]
    assert new_shas and all(sha not in decisions["items"] for sha in new_shas)
    kept = json.loads((folder / "human-decisions.json").read_text("utf8"))
    assert legacy_children[0]["child_sha"] in kept["items"]      # old decision kept
    assert all(Path(child["path"]).is_file() for child in legacy_children)  # old files kept
    assert set(old_shas) == set(new_shas)                        # deterministic re-crop


def test_repeat_processing_of_a_current_record_reuses_files(tmp_path):
    folder, row, record = _make_run(tmp_path)
    files = sorted(path.name for path in (folder / "derived").glob("*.png"))
    payload = (folder / "derived.json").read_bytes()
    again = collage.process_original(folder, row)
    assert again.get("reused") is True
    assert sorted(path.name for path in (folder / "derived").glob("*.png")) == files
    assert (folder / "derived.json").read_bytes() == payload


# --- canonical counts -------------------------------------------------------

def test_one_named_collage_with_two_tiles_counts_two_photos(tmp_path):
    folder, row, record = _make_run(tmp_path, rows=2, cols=1)
    counts = compute(folder, [row], {row["asset_sha"]: record})
    assert counts["found"] == 1
    assert counts["target_confirmed"] == 1
    assert counts["original_singles"] == 0
    assert counts["derived_valid"] == 2
    assert counts["usable_independent"] == 2
    assert counts["usable_named"] == 2
    assert counts["awaiting_manual"] == 0


def test_duplicate_tile_across_parents_counts_once(tmp_path):
    folder = _folder(tmp_path)
    shared = _textured((800, 600), 11, (198, 62, 54))
    first = Image.new("RGB", (800, 1200))
    first.paste(shared, (0, 0))
    first.paste(_textured((800, 600), 12, (52, 150, 196)), (0, 600))
    row1 = _write_original(folder, first, name="first.png")
    row1["relevance"] = {"tier": "target_named"}
    record1 = collage.process_original(folder, row1)
    second = Image.new("RGB", (800, 1200))
    second.paste(shared, (0, 0))
    second.paste(_textured((800, 600), 13, (240, 214, 70)), (0, 600))
    row2 = _write_original(folder, second, name="second.png")
    row2["relevance"] = {"tier": "target_named"}
    known = {child["child_sha"] for child in record1["children"]}
    record2 = collage.process_original(folder, row2, known_shas=known)
    counts = compute(folder, [row1, row2], {row1["asset_sha"]: record1, row2["asset_sha"]: record2})
    assert counts["usable_independent"] == 3
    assert counts["derived_valid"] == 3
    assert len({child["child_sha"] for record in (record1, record2)
                for child in record["children"] if child["status"] == collage.VALID}) == 3


def test_human_keep_does_not_change_acquisition_counts(tmp_path, monkeypatch):
    folder, row, record = _make_run(tmp_path)
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "runs")
    (folder / "received.json").write_text(json.dumps([row]), "utf8")
    before = collection_queue.snapshot("job-audit", limit=20)["counts"]
    collection_queue.decide("job-audit", record["children"][0]["child_sha"], "keep")
    after = collection_queue.snapshot("job-audit", limit=20)["counts"]
    assert after["usable_independent"] == before["usable_independent"]
    assert after["usable_named"] == before["usable_named"]
    assert after["human_keep"] == 1


def test_queue_compute_and_summary_report_the_same_numbers(tmp_path, monkeypatch):
    folder, row, record = _make_run(tmp_path)
    (folder / "received.json").write_text(json.dumps([row]), "utf8")
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "runs")
    queue_counts = collection_queue.snapshot("job-audit", limit=20)["counts"]
    canonical = compute(folder, [row], {row["asset_sha"]: record})
    from tools.collect_verified import write_search_summary
    summary = write_search_summary(
        folder, status="completed", stop_reason="target_reached", received=[row],
        queries=[], checks={}, searches={}, started=0.0, first_received=None,
        duplicates=[], errors=[], extra={"target": 15, "target_reached": True,
                                         "canonical": canonical, "search_only": True})
    keys = ("found", "target_confirmed", "original_singles", "derived_valid",
            "usable_independent", "usable_named", "awaiting_manual")
    for key in keys:
        assert queue_counts[key] == canonical[key], key
        assert summary["counts"][key] == canonical[key], key
    assert summary["counts_source"] == "ref_lab.collection_counts.compute"
