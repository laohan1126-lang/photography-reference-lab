"""Audit regressions: history restore, historical tiles, static page, timing.

The previous build restored only originals into the duplicate index, never put
un-imported historical tiles into it, wrote static pages that referenced tiles
they had not copied, and recorded Pinterest navigation twice (outer + inner
span). Each test below fails on that build and passes on the current one.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from ref_lab import collage, collection_history, collection_queue
from ref_lab.collection_timing import CollectionTiming
from tests.test_collage_split import _collage, _textured, _write_original


def _run(tmp_path: Path, *, rows=2, cols=1, tile=(800, 600)):
    folder = tmp_path / "runs" / "job" / "current"
    folder.mkdir(parents=True)
    row = _write_original(folder, _collage(rows, cols, tile=tile), name="parent.png")
    row["relevance"] = {"tier": "target_named", "label": "名称命中"}
    record = collage.process_original(folder, row)
    (folder / "received.json").write_text(json.dumps([row]), "utf8")
    return folder, row, record


def _history_root(tmp_path: Path, name="old-run"):
    root = tmp_path / "history"
    local = root / ".local"
    local.mkdir(parents=True)
    data = tmp_path / "data"
    (data / "assets").mkdir(parents=True)
    run = local / name
    (run / "images").mkdir(parents=True)
    return root, local, data, run


# --- history index ----------------------------------------------------------

def test_historical_valid_child_enters_the_history_index(tmp_path, monkeypatch):
    root, local, data, run = _history_root(tmp_path)
    row = _write_original(run, _collage(2, 1, tile=(800, 600)))
    (run / "received.json").write_text(json.dumps([row]), "utf8")
    record = collage.process_original(run, row)
    child = record["children"][0]
    monkeypatch.setenv("LAB_DATA_DIR", str(data))
    paths = collection_history.historical_paths(root, local / "current-job")
    assert Path(child["path"]).resolve() in paths
    assert Path(row["original_path"]).resolve() in paths


def test_historical_outdated_child_is_not_indexed(tmp_path, monkeypatch):
    root, local, data, run = _history_root(tmp_path)
    row = _write_original(run, _collage(2, 1, tile=(800, 600)))
    (run / "received.json").write_text(json.dumps([row]), "utf8")
    record = collage.process_original(run, row)
    path = run / "derived.json"
    data_json = json.loads(path.read_text("utf8"))
    data_json["items"][row["asset_sha"]].pop("algorithm_version")
    path.write_text(json.dumps(data_json), "utf8")
    monkeypatch.setenv("LAB_DATA_DIR", str(data))
    paths = collection_history.historical_paths(root, local / "current-job")
    assert Path(record["children"][0]["path"]).resolve() not in paths


def test_historical_corrupt_child_cannot_prove_no_repeat(tmp_path, monkeypatch):
    root, local, data, run = _history_root(tmp_path)
    row = _write_original(run, _collage(2, 1, tile=(800, 600)))
    (run / "received.json").write_text(json.dumps([row]), "utf8")
    record = collage.process_original(run, row)
    Path(record["children"][0]["path"]).write_bytes(b"damaged")
    monkeypatch.setenv("LAB_DATA_DIR", str(data))
    with pytest.raises(ValueError, match="Historical derived tile SHA changed"):
        collection_history.historical_paths(root, local / "current-job")


class _RecordingHistory:
    def __init__(self):
        self.seen: list[str] = []

    def consider(self, path):
        self.seen.append(str(Path(path).resolve()))
        return None


def test_restore_registers_originals_and_verified_tiles(tmp_path):
    from tools.collect_verified import restore_history_index
    folder, row, record = _run(tmp_path)
    history = _RecordingHistory()
    result = restore_history_index(history, folder, [row])
    valid = [child for child in record["children"] if child["status"] == collage.VALID]
    assert result["originals"] == 1
    assert result["children"] == len(valid) == 2
    assert str(Path(row["original_path"]).resolve()) in history.seen
    for child in valid:
        assert str(Path(child["path"]).resolve()) in history.seen


def test_restore_skips_tiles_of_an_outdated_record(tmp_path):
    from tools.collect_verified import restore_history_index
    folder, row, record = _run(tmp_path)
    path = folder / "derived.json"
    data = json.loads(path.read_text("utf8"))
    data["items"][row["asset_sha"]].pop("algorithm_version")
    path.write_text(json.dumps(data), "utf8")
    history = _RecordingHistory()
    result = restore_history_index(history, folder, [row])
    assert result["originals"] == 1 and result["children"] == 0
    assert all(str(folder / "derived") not in seen for seen in history.seen)


def test_queue_shows_a_shared_tile_only_once(tmp_path, monkeypatch):
    folder = tmp_path / "runs" / "job" / "current"
    folder.mkdir(parents=True)
    shared = _textured((800, 600), 21, (198, 62, 54))
    rows = []
    for name, seed, colour in (("a.png", 22, (52, 150, 196)), ("b.png", 23, (240, 214, 70))):
        image = Image.new("RGB", (800, 1200))
        image.paste(shared, (0, 0))
        image.paste(_textured((800, 600), seed, colour), (0, 600))
        row = _write_original(folder, image, name=name)
        row["relevance"] = {"tier": "target_named"}
        rows.append(row)
    known: set[str] = set()
    records = {}
    for row in rows:
        records[row["asset_sha"]] = collage.process_original(folder, row, known_shas=known)
    (folder / "received.json").write_text(json.dumps(rows), "utf8")
    monkeypatch.setattr(collection_queue, "run_root", lambda: tmp_path / "runs")
    snapshot = collection_queue.snapshot("job", limit=50)
    cards = [item for item in snapshot["items"] if item["derived"]]
    assert len(cards) == 3
    assert len({card["asset_sha"] for card in cards}) == 3
    assert snapshot["counts"]["derived_valid"] == 3


# --- static candidate page --------------------------------------------------

def test_static_page_copies_and_verifies_every_referenced_tile(tmp_path):
    from tools.collect_verified import render_search_gallery
    folder, row, record = _run(tmp_path)
    render_search_gallery(folder, [row])
    page = (folder / "public" / "search-index.html").read_text("utf8")
    original = folder / "public" / Path(row["original_path"]).name
    assert original.is_file()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == row["asset_sha"]
    for child in record["children"]:
        target = folder / "public" / f"{child['child_sha']}.png"
        assert target.is_file()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == child["child_sha"]
        assert f"{child['child_sha']}.png" in page


def test_static_page_does_not_promise_tiles_that_do_not_exist(tmp_path):
    from tools.collect_verified import render_search_gallery
    folder, row, record = _run(tmp_path, rows=3, cols=1, tile=(360, 480))
    assert record["status"] == collage.STATUS_LOW_RESOLUTION
    render_search_gallery(folder, [row])
    page = (folder / "public" / "search-index.html").read_text("utf8")
    assert "原拼图仍可查看" in page
    assert "<figcaption" not in page
    for child in record["children"]:
        assert f"{child['child_sha']}.png" not in page


def test_static_page_marks_outdated_record_as_pending_update(tmp_path):
    from tools.collect_verified import render_search_gallery
    folder, row, record = _run(tmp_path)
    path = folder / "derived.json"
    data = json.loads(path.read_text("utf8"))
    data["items"][row["asset_sha"]].pop("algorithm_version")
    path.write_text(json.dumps(data), "utf8")
    render_search_gallery(folder, [row])
    page = (folder / "public" / "search-index.html").read_text("utf8")
    assert "版本待更新" in page
    for child in record["children"]:
        assert f"{child['child_sha']}.png" not in page


# --- timing -----------------------------------------------------------------

def test_pinterest_navigation_is_recorded_once_and_dom_separately(tmp_path, monkeypatch):
    from tools import collect_verified
    browser = collect_verified.Browser(tmp_path)
    browser.bsk, browser.session = "bsk", "session"
    browser.command = lambda *args, **kwargs: "{}"
    from tests.test_search_detail_timing import _png
    raw = _png(size=(500, 700))
    sha = hashlib.sha256(raw).hexdigest()
    previews = tmp_path / "discovery-previews"
    previews.mkdir()
    preview = previews / f"{sha}.png"
    preview.write_bytes(raw)
    browser.preview = {"url": "https://i.pinimg.com/x.png", "sha": sha, "path": str(preview)}
    timing = CollectionTiming(tmp_path)
    browser.timing = timing

    def fake_fetch(bsk, session, page, env, timing=None):
        with timing.span("detail_navigate"):
            pass
        with timing.span("detail_dom_wait"):
            pass
        return {"image_url": "https://i.pinimg.com/x.png"}

    monkeypatch.setattr(collect_verified, "fetch_pinterest_detail_metadata", fake_fetch)
    monkeypatch.setattr(collect_verified.httpx, "stream",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")))
    rows = browser.receive({"page": "https://www.pinterest.com/pin/123/"}, {"source": "pinterest"})
    assert rows and rows[0]["asset_sha"] == sha
    stages = [json.loads(line)["stage"]
              for line in (tmp_path / "timings.jsonl").read_text("utf8").splitlines()]
    assert stages.count("detail_navigate") == 1
    assert stages.count("detail_dom_wait") == 1
    assert "detail_download" in stages and "detail_return" in stages
