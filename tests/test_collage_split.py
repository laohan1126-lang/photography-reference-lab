"""Deterministic regressions for local collage detection, splitting and counting.

These tests build their own images: they protect the *rules* (geometry, seam
discontinuity, tile quality, idempotency, counting), not a platform's current
rendering. Real-image evidence lives in the task record and the private run
directory; a synthetic pass is not visual accuracy evidence.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

from ref_lab import collage
from ref_lab import collection_queue


def _textured(size, seed, base):
    """A photo-like tile: smooth structure plus local detail.

    Pure per-pixel noise would make every row boundary equally strong, so a seam
    would be indistinguishable from ordinary texture. Real photographs have
    smooth regions; the generator must too, or the test would not exercise the
    actual decision.
    """
    width, height = size
    rng = np.random.default_rng(seed)
    noise = rng.integers(-40, 41, (height, width, 3), dtype=np.int16)
    ramp = np.linspace(-24, 24, width, dtype=np.int16)[None, :, None]
    array = np.clip(np.array(base, np.int16) + noise + ramp, 0, 255).astype(np.uint8)
    image = Image.fromarray(array, "RGB").filter(ImageFilter.GaussianBlur(0.8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((width // 5, height // 4, width * 3 // 5, height * 7 // 10),
                 fill=tuple(int(value) for value in base))
    draw.rectangle((width // 6, height // 2, width // 3, height * 4 // 5),
                   fill=tuple(min(255, int(value) + 60) for value in base))
    draw.line((0, height // 3, width, height // 3), fill=(250, 250, 250), width=3)
    return image


def _collage(rows, cols, tile=(600, 480), bases=None):
    # Distinct luminance per panel: a real collage seam is a grey-level step, and
    # two panels of nearly identical brightness would (correctly) stay unproven.
    bases = bases or [(28, 30, 34), (222, 220, 214), (198, 62, 54), (52, 150, 196),
                      (240, 214, 70), (86, 88, 208), (236, 138, 58), (58, 196, 122),
                      (148, 58, 178)]
    canvas = Image.new("RGB", (cols * tile[0], rows * tile[1]))
    for row in range(rows):
        for col in range(cols):
            canvas.paste(_textured(tile, row * cols + col + 1, bases[(row * cols + col) % len(bases)]),
                         (col * tile[0], row * tile[1]))
    return canvas


def _write_original(run: Path, image: Image.Image, name="parent.png") -> dict:
    run.mkdir(parents=True, exist_ok=True)
    images = run / "images"
    images.mkdir(exist_ok=True)
    path = images / name
    image.save(path, format="PNG")
    raw = path.read_bytes()
    return {"asset_sha": hashlib.sha256(raw).hexdigest(), "original_path": str(path),
            "page_url": "https://example.invalid/note/1", "image_url": "https://example.invalid/1.jpg",
            "search_query": "测试查询", "author": "测试作者", "width": image.width,
            "height": image.height, "relevance": {"tier": "target_named", "label": "名称命中"}}


def test_two_row_collage_splits_into_two_lossless_tiles(tmp_path):
    row = _write_original(tmp_path, _collage(2, 1, tile=(800, 600)))
    record = collage.process_original(tmp_path, row)
    assert record["status"] == collage.STATUS_SPLIT_OK
    assert record["layout"] == "grid_2x1"
    assert len(record["children"]) == 2
    for index, child in enumerate(record["children"]):
        assert child["status"] == "valid"
        assert child["parent_sha"] == row["asset_sha"]
        assert child["crop"][3] >= 479
        raw = Path(child["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == child["child_sha"]
        with Image.open(child["path"]) as tile:
            assert tile.format == "PNG"
            assert tile.size == tuple(child["size"])
        assert child["quality"]["sharpness"] > collage.MIN_SHARPNESS
    # The original bytes are untouched and still the parent.
    assert hashlib.sha256(Path(row["original_path"]).read_bytes()).hexdigest() == row["asset_sha"]


def test_three_by_three_low_resolution_tiles_are_rejected(tmp_path):
    row = _write_original(tmp_path, _collage(3, 3, tile=(360, 480)))
    record = collage.process_original(tmp_path, row)
    assert record["layout"] == "grid_3x3"
    assert record["status"] == collage.STATUS_LOW_RESOLUTION
    assert len(record["children"]) == 9
    assert all(child["status"] == "low_resolution" for child in record["children"])
    assert record["counts"]["independent"] == 0
    # Tiles still exist for inspection; they are simply not counted as usable.
    assert all(Path(child["path"]).is_file() for child in record["children"])


def test_single_photo_with_a_hard_horizontal_edge_is_not_split(tmp_path):
    width, height = 900, 1200
    canvas = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        if y < height // 2:
            draw.line((0, y, width, y), fill=(int(30 + y / 12), int(60 + y / 20), 120))
        else:
            draw.line((0, y, width, y), fill=(150, 90, 60))
    row = _write_original(tmp_path, canvas)
    record = collage.process_original(tmp_path, row)
    assert record["status"] == collage.STATUS_NO_COLLAGE
    assert record["children"] == []
    assert record["counts"] == {"independent": 1, "parent_counts": True,
                                "usable_children": 0, "rejected_children": 0}


def test_five_row_grid_is_reported_for_manual_cropping_not_silently_counted(tmp_path):
    row = _write_original(tmp_path, _collage(5, 1, tile=(600, 400)))
    record = collage.process_original(tmp_path, row)
    assert record["status"] == collage.STATUS_NEEDS_MANUAL
    assert record["children"] == []
    assert record["counts"]["independent"] == 0


def test_repeat_processing_reuses_the_same_record_and_files(tmp_path):
    row = _write_original(tmp_path, _collage(2, 2))
    first = collage.process_original(tmp_path, row)
    files_before = sorted(path.name for path in (tmp_path / "derived").glob("*.png"))
    record_before = (tmp_path / "derived.json").read_bytes()
    second = collage.process_original(tmp_path, row)
    files_after = sorted(path.name for path in (tmp_path / "derived").glob("*.png"))
    assert first == second or second.get("reused") is True
    assert files_before == files_after
    assert len(files_after) == len(first["children"])
    assert (tmp_path / "derived.json").read_bytes() == record_before


def test_child_that_matches_history_is_not_counted_as_usable(tmp_path):
    row = _write_original(tmp_path, _collage(2, 1, tile=(800, 600)))
    first_pass = collage.process_original(tmp_path, row)
    expected = [child["child_sha"] for child in first_pass["children"]]

    class History:
        def __init__(self):
            self.seen = []
        def consider(self, path, **kwargs):
            self.seen.append(path)
            return {"duplicate_of": "b" * 64, "reason": "same_bytes"}

    shutil.rmtree(tmp_path / "derived")
    (tmp_path / "derived.json").unlink()
    history = History()
    record = collage.process_original(tmp_path, row, history=history)
    assert record["status"] == collage.STATUS_DUPLICATE
    assert {child["status"] for child in record["children"]} == {"duplicate_history"}
    assert {child["child_sha"] for child in record["children"]} == set(expected)
    assert record["counts"]["independent"] == 0
    assert len(history.seen) == 2


def test_parent_and_children_never_double_count():
    assert collage.count_summary(collage.STATUS_NO_COLLAGE, [])["independent"] == 1
    usable = [{"status": "valid"}, {"status": "valid"}]
    summary = collage.count_summary(collage.STATUS_SPLIT_OK, usable)
    assert summary["independent"] == 2 and summary["parent_counts"] is False
    mixed = [{"status": "valid"}, {"status": "low_resolution"}]
    assert collage.count_summary(collage.STATUS_SPLIT_PARTIAL, mixed)["independent"] == 1
    assert collage.count_summary(collage.STATUS_LOW_RESOLUTION,
                                 [{"status": "low_resolution"}])["independent"] == 0
    assert collage.count_summary(collage.STATUS_NEEDS_MANUAL, [])["independent"] == 0


def test_tampered_original_is_refused(tmp_path):
    row = _write_original(tmp_path, _collage(2, 1, tile=(800, 600)))
    path = Path(row["original_path"])
    path.write_bytes(b"not the received image")
    with pytest.raises(collage.CollageError):
        collage.process_original(tmp_path, row)


def test_white_gutter_grid_is_detected_on_both_axes(tmp_path):
    """A platform 3x3 grid with white separators has almost no seam gradient.

    A single-axis-only reading (3 vertical strips) would be a wrong crop, even
    though the tiles are rejected for resolution either way. Both axes must be
    reported.
    """
    tile_w, tile_h, gutter = 352, 464, 12
    canvas = Image.new("RGB", (tile_w * 3 + gutter * 2, tile_h * 3 + gutter * 2), (250, 250, 250))
    for row in range(3):
        for col in range(3):
            canvas.paste(_textured((tile_w, tile_h), row * 3 + col + 1,
                                   [(28, 30, 34), (198, 62, 54), (52, 150, 196),
                                    (240, 214, 70), (86, 88, 208), (236, 138, 58),
                                    (58, 196, 122), (148, 58, 178), (222, 220, 214)][row * 3 + col]),
                         (col * (tile_w + gutter), row * (tile_h + gutter)))
    row = _write_original(tmp_path, canvas)
    record = collage.process_original(tmp_path, row)
    assert record["layout"] == "grid_3x3"
    assert record["status"] == collage.STATUS_LOW_RESOLUTION
    assert len(record["children"]) == 9
    assert all(child["status"] == "low_resolution" for child in record["children"])
    # Cut inside the gutters: no tile may contain the separator line.
    for child in record["children"]:
        assert child["size"][0] <= tile_w and child["size"][1] <= tile_h


def test_queue_exposes_usable_children_and_routes_decisions(tmp_path, monkeypatch):
    run_root = tmp_path / "runs"
    monkeypatch.setattr(collection_queue, "run_root", lambda: run_root)
    job_id = "job-collage-1"
    folder = run_root / job_id / "current"
    row = _write_original(folder, _collage(2, 1, tile=(800, 600)))
    second = _write_original(folder, _textured((600, 800), 99, (80, 120, 160)), name="single.png")
    received = [row, second]
    (folder / "received.json").write_text(json.dumps(received), "utf8")
    (folder / "search-summary.json").write_text(json.dumps({"status": "completed", "counts": {
        "found": 2, "target_confirmed": 2}}), "utf8")
    collage.process_original(folder, row)
    collage.process_original(folder, second)

    snapshot = collection_queue.snapshot(job_id, limit=50)
    counts = snapshot["counts"]
    assert counts["found"] == 2
    assert counts["original_singles"] == 1
    assert counts["collages"] == 1
    assert counts["derived_valid"] == 2
    # Two usable tiles + the non-collage original; the collage parent is excluded.
    assert counts["independent_candidates"] == 3
    assert counts["named_candidates"] == 3
    children = [item for item in snapshot["items"] if item["derived"]]
    assert len(children) == 2
    child = children[0]
    assert child["parent_sha"] == row["asset_sha"]
    assert child["crop"] and child["child_index"] in {1, 2}

    path, raw = collection_queue.original_bytes(job_id, child["asset_sha"])
    assert hashlib.sha256(raw).hexdigest() == child["asset_sha"]
    assert path.suffix == ".png"

    decided = collection_queue.decide(job_id, child["asset_sha"], "keep")
    assert next(item for item in decided["items"]
                if item["asset_sha"] == child["asset_sha"])["human_decision"] == "keep"
    with pytest.raises(ValueError):
        collection_queue.original_bytes(job_id, "f" * 64)


def test_queue_refuses_derived_path_outside_the_run(tmp_path, monkeypatch):
    run_root = tmp_path / "runs"
    monkeypatch.setattr(collection_queue, "run_root", lambda: run_root)
    job_id = "job-collage-2"
    folder = run_root / job_id / "current"
    row = _write_original(folder, _collage(2, 1, tile=(800, 600)))
    (folder / "received.json").write_text(json.dumps([row]), "utf8")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not an image")
    (folder / "derived.json").write_text(json.dumps({"version": 1, "items": {
        row["asset_sha"]: {"status": "split_ok", "layout": "grid_2x1",
                           "counts": {"parent_counts": False},
                           "children": [{"child_sha": "a" * 64, "status": "valid",
                                         "path": str(outside), "crop": [0, 0, 10, 10],
                                         "size": [10, 10]}]}}}), "utf8")
    snapshot = collection_queue.snapshot(job_id, limit=50)
    assert [item for item in snapshot["items"] if item["derived"]] == []

