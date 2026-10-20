"""Second-audit regressions: legacy upgrade identity, name association, quality.

Each test encodes a defect that the second independent audit reproduced on
``7c0773c``:

* a v1 Job whose tiles were already imported into the library had both
  recomputed tiles marked ``duplicate_history`` (usable 2 -> 0);
* a name-hit association was dropped when the same tile appeared in a second
  parent record, so ``usable_named`` depended on parent order;
* one valid and one blurry tile left ``awaiting_manual`` at 0.

Synthetic images protect the counting and identity rules only; they are not
visual-accuracy evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from ref_lab import collage
from ref_lab.collection_counts import compute
from ref_lab.collection_history import ImageHistory
from ref_lab.integrity import reset_cache
from tests.test_collage_split import _textured, _write_original
from tools.collect_verified import restore_history_index


@pytest.fixture(autouse=True)
def _fresh_integrity_cache():
    reset_cache()
    yield
    reset_cache()


def _job(tmp_path: Path, name: str = "job-audit") -> Path:
    folder = tmp_path / "runs" / name / "current"
    folder.mkdir(parents=True)
    return folder


def _stack(top: Image.Image, bottom: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (top.width, top.height + bottom.height))
    canvas.paste(top, (0, 0))
    canvas.paste(bottom, (0, top.height))
    return canvas


def _records(folder: Path) -> dict:
    return collage.DerivedStore(folder).items()


def _downgrade(folder: Path, parent_sha: str) -> dict:
    """Turn a current record into an old-version record, keeping its children."""
    path = folder / "derived.json"
    data = json.loads(path.read_text("utf8"))
    record = data["items"][parent_sha]
    record.pop("algorithm_version")
    path.write_text(json.dumps(data, ensure_ascii=False), "utf8")
    return record


def _import_tiles(tmp_path: Path, children) -> list[Path]:
    """Copy this Job's tiles into the library asset store, as v1 did."""
    store = tmp_path / "library-assets"
    store.mkdir(exist_ok=True)
    imported = []
    for child in children:
        target = store / f"{child['child_sha']}.png"
        target.write_bytes(Path(child["path"]).read_bytes())
        imported.append(target)
    return imported


# --- 1. legacy upgrade must not treat this Job's own tiles as history -------

def test_legacy_job_upgrade_keeps_its_own_already_imported_tiles(tmp_path):
    folder = _job(tmp_path)
    row = _write_original(folder, _stack(_textured((800, 600), 1, (28, 30, 34)),
                                         _textured((800, 600), 2, (222, 220, 214))),
                          name="parent.png")
    record = collage.process_original(folder, row)
    assert [child["status"] for child in record["children"]] == [collage.VALID, collage.VALID]
    old_shas = [child["child_sha"] for child in record["children"]]
    imported = _import_tiles(tmp_path, record["children"])
    _downgrade(folder, row["asset_sha"])
    decisions = {"version": 1, "items": {old_shas[0]: {
        "decision": "keep", "asset_sha": old_shas[0], "actor": "human"}}}
    (folder / "human-decisions.json").write_text(json.dumps(decisions), "utf8")

    history = ImageHistory(imported)
    try:
        restored = restore_history_index(history, folder, [row])
        assert restored["children"] == 0                  # legacy tiles are not pre-approved

        again = collage.process_original(folder, row, history=history,
                                         known_shas={row["asset_sha"]})
    finally:
        history.close()

    assert again["algorithm_version"] == collage.ALGORITHM_VERSION
    assert [child["child_sha"] for child in again["children"]] == old_shas
    assert [child["status"] for child in again["children"]] == [collage.VALID, collage.VALID]
    counts = compute(folder, [row], _records(folder))
    assert counts["usable_independent"] == 2
    assert counts["usable_named"] == 2
    assert counts["derived_duplicate"] == 0
    # Old files, old decision and the migration snapshot survive.
    for sha in old_shas:
        assert (folder / "derived" / f"{sha}.png").is_file()
    assert Path(again["previous_record_snapshot"]).is_file()
    assert json.loads((folder / "human-decisions.json").read_text("utf8"))["items"][old_shas[0]]["decision"] == "keep"


def test_legacy_upgrade_still_excludes_external_history_tiles(tmp_path):
    folder = _job(tmp_path)
    external_tile = _textured((800, 600), 2, (222, 220, 214))
    external = tmp_path / "external-history"
    external.mkdir()
    external_path = external / "already-owned.png"
    external_tile.save(external_path)

    row = _write_original(folder, _stack(_textured((800, 600), 1, (28, 30, 34)), external_tile),
                          name="parent.png")
    history = ImageHistory([external_path])
    try:
        record = collage.process_original(folder, row, history=history)
    finally:
        history.close()

    statuses = [child["status"] for child in record["children"]]
    assert statuses.count(collage.DUPLICATE_HISTORY) == 1
    assert statuses.count(collage.VALID) == 1
    counts = compute(folder, [row], _records(folder))
    assert counts["usable_independent"] == 1
    assert counts["usable_named"] == 1          # external history adds no usable photo


def test_restore_then_second_collage_sharing_a_tile_counts_three(tmp_path):
    folder = _job(tmp_path)
    shared = _textured((800, 600), 1, (28, 30, 34))
    row_ab = _write_original(folder, _stack(shared, _textured((800, 600), 2, (222, 220, 214))),
                             name="ab.png")
    record_ab = collage.process_original(folder, row_ab)
    history = ImageHistory([])
    try:
        restored = restore_history_index(history, folder, [row_ab])
        assert restored["originals"] == 1 and restored["children"] == 2
        row_ac = _write_original(folder, _stack(shared, _textured((800, 600), 3, (52, 150, 196))),
                                 name="ac.png")
        record_ac = collage.process_original(folder, row_ac, history=history)
    finally:
        history.close()
    assert [child["status"] for child in record_ac["children"]].count(collage.DUPLICATE_HISTORY) == 1
    counts = compute(folder, [row_ab, row_ac], _records(folder))
    assert counts["usable_independent"] == 3
    assert counts["derived_valid"] == 3


# --- 2. name association is aggregated separately from photo uniqueness ----

def _name_association_run(tmp_path):
    folder = _job(tmp_path)
    shared = _textured((800, 600), 1, (28, 30, 34))
    row_ab = _write_original(folder, _stack(shared, _textured((800, 600), 2, (222, 220, 214))),
                             name="unconfirmed.png")
    row_ab["relevance"] = {"tier": "unconfirmed", "label": "角色相关性未确认"}
    record_ab = collage.process_original(folder, row_ab)
    row_ac = _write_original(folder, _stack(shared, _textured((800, 600), 3, (52, 150, 196))),
                             name="named.png")
    row_ac["relevance"] = {"tier": "target_named", "label": "名称命中"}
    known = {child["child_sha"] for child in record_ab["children"] if child["status"] == collage.VALID}
    record_ac = collage.process_original(folder, row_ac, known_shas=known)
    return folder, row_ab, row_ac, record_ab, record_ac


def test_name_hit_is_aggregated_by_unique_photo_not_by_parent_order(tmp_path):
    folder, row_ab, row_ac, _, record_ac = _name_association_run(tmp_path)
    # The second A is a this-run repeat; its name association must still count.
    assert [child["status"] for child in record_ac["children"]].count(collage.DUPLICATE_RUN) == 1
    records = _records(folder)
    first = compute(folder, [row_ab, row_ac], records)
    second = compute(folder, [row_ac, row_ab], records)
    for counts in (first, second):
        assert counts["usable_independent"] == 3
        assert counts["usable_named"] == 2
        assert counts["awaiting_manual"] == first["awaiting_manual"]
    assert first["usable_named"] == second["usable_named"] == 2


def test_name_hit_does_not_count_an_external_history_tile(tmp_path):
    folder = _job(tmp_path)
    external = tmp_path / "external-history"
    external.mkdir()
    shared = _textured((800, 600), 1, (28, 30, 34))
    external_path = external / "old.png"
    shared.save(external_path)
    row = _write_original(folder, _stack(shared, _textured((800, 600), 2, (222, 220, 214))),
                          name="named.png")
    history = ImageHistory([external_path])
    try:
        record = collage.process_original(folder, row, history=history)
    finally:
        history.close()
    assert [child["status"] for child in record["children"]].count(collage.DUPLICATE_HISTORY) == 1
    counts = compute(folder, [row], _records(folder))
    assert counts["usable_independent"] == 1
    assert counts["usable_named"] == 1
    assert counts["derived_duplicate"] == 1


# --- 3. partial quality stays visible once per original --------------------

def test_partial_quality_keeps_the_valid_sibling_and_one_pending_original(tmp_path):
    folder = _job(tmp_path)
    canvas = Image.new("RGB", (800, 1200), (240, 240, 240))
    canvas.paste(_textured((800, 600), 1, (28, 30, 34)), (0, 0))
    row = _write_original(folder, canvas, name="partial.png")
    record = collage.process_original(folder, row)
    statuses = [child["status"] for child in record["children"]]
    assert statuses.count(collage.VALID) == 1
    assert statuses.count("too_blurry") == 1
    assert record["status"] == collage.STATUS_SPLIT_PARTIAL

    counts = compute(folder, [row], _records(folder))
    assert counts["usable_independent"] == 1
    assert counts["usable_named"] == 1
    assert counts["awaiting_manual"] == 1
    assert counts["derived_rejected"] == 1
    valid = [child for child in record["children"] if child["status"] == collage.VALID][0]
    assert Path(valid["path"]).is_file()          # the qualified sibling stays


def test_duplicate_only_tiles_are_not_a_quality_problem(tmp_path):
    folder = _job(tmp_path)
    first = _textured((800, 600), 1, (28, 30, 34))
    second = _textured((800, 600), 2, (222, 220, 214))
    external = tmp_path / "external-history"
    external.mkdir()
    first.save(external / "one.png")
    second.save(external / "two.png")
    row = _write_original(folder, _stack(first, second), name="repeats.png")
    history = ImageHistory([external / "one.png", external / "two.png"])
    try:
        record = collage.process_original(folder, row, history=history)
    finally:
        history.close()
    assert [child["status"] for child in record["children"]] == [
        collage.DUPLICATE_HISTORY, collage.DUPLICATE_HISTORY]
    assert record["status"] == collage.STATUS_DUPLICATE
    counts = compute(folder, [row], _records(folder))
    assert counts["usable_independent"] == 0
    assert counts["derived_duplicate"] == 2
    assert counts["awaiting_manual"] == 0


# --- 4. refresh / restart / repeated migration leave everything stable -----

def test_repeated_migration_and_restart_keep_files_counts_and_decisions(tmp_path):
    folder = _job(tmp_path)
    row = _write_original(folder, _stack(_textured((800, 600), 1, (28, 30, 34)),
                                         _textured((800, 600), 2, (222, 220, 214))),
                          name="parent.png")
    record = collage.process_original(folder, row)
    shas = [child["child_sha"] for child in record["children"]]
    imported = _import_tiles(tmp_path, record["children"])
    _downgrade(folder, row["asset_sha"])
    (folder / "human-decisions.json").write_text(json.dumps({"version": 1, "items": {
        shas[1]: {"decision": "reject", "asset_sha": shas[1], "actor": "human"}}}), "utf8")

    history = ImageHistory(imported)
    try:
        collage.process_original(folder, row, history=history, known_shas={row["asset_sha"]})
    finally:
        history.close()
    first = compute(folder, [row], _records(folder))
    files = sorted(path.name for path in (folder / "derived").glob("*.png"))
    snapshot = _records(folder)[row["asset_sha"]]["previous_record_snapshot"]

    # Repeat the migration in a new process view: current record is reused.
    history = ImageHistory(imported)
    try:
        restored = restore_history_index(history, folder, [row])
        again = collage.process_original(folder, row, history=history,
                                         known_shas={row["asset_sha"]})
    finally:
        history.close()
    assert restored["children"] == 2
    assert again.get("reused") is True
    second = compute(folder, [row], _records(folder))
    assert second == first
    assert sorted(path.name for path in (folder / "derived").glob("*.png")) == files
    decisions = json.loads((folder / "human-decisions.json").read_text("utf8"))["items"]
    assert decisions[shas[1]]["decision"] == "reject"
    assert _records(folder)[row["asset_sha"]]["previous_record_snapshot"] == snapshot
    assert Path(snapshot).is_file()
