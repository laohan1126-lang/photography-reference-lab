"""Detail-phase attribution and byte-reuse regressions.

The previous run's ``browser_receive`` was one opaque 319-second block. These
tests protect the split: click/return are recorded, image location and download
are timed separately, and an already-downloaded Pinterest cover is not fetched
twice for the same URL.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from ref_lab import collage
from ref_lab.collection_timing import CollectionTiming
from tools import collect_verified, exact_recall


def _png(size=(400, 600), colour=(120, 80, 60)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
    return buffer.getvalue()


def _stages(path: Path) -> list[str]:
    return [json.loads(line)["stage"] for line in path.read_text("utf8").splitlines() if line.strip()]


def test_capture_note_records_locate_download_store(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "a" * 24
    payload = {"ok": True, "value": {"page_url": page, "text": "标题正文",
                                     "images": [{"url": "https://sns-img.xhscdn.com/one.jpg",
                                                 "width": 400, "height": 600}]}}

    class Completed:
        returncode = 0
        stdout = json.dumps(payload)

    monkeypatch.setattr(exact_recall.subprocess, "run", lambda *args, **kwargs: Completed())

    class Response:
        content = _png()

        def raise_for_status(self):
            return None

    monkeypatch.setattr(exact_recall.httpx, "get", lambda *args, **kwargs: Response())
    timing = CollectionTiming(tmp_path)
    rows = exact_recall.capture_note("bsk", "session", tmp_path, page, limit=3, timing=timing)
    assert len(rows) == 1 and rows[0]["width"] == 400
    stages = _stages(tmp_path / "timings.jsonl")
    for expected in ("detail_locate", "detail_download", "detail_store"):
        assert expected in stages


def test_xhs_receive_attributes_click_dom_wait_and_return(tmp_path, monkeypatch):
    note = "b" * 24
    page = "https://www.xiaohongshu.com/explore/" + note
    browser = collect_verified.Browser(tmp_path)
    browser.bsk, browser.session = "bsk", "session"
    commands: list[str] = []

    def command(*args, **kwargs):
        commands.append(args[0])
        return json.dumps({"session_id": "session"})

    browser.command = command
    browser._probe_detail = lambda: {"url": page, "login_required": False,
                                     "challenge": False, "not_found": False}
    monkeypatch.setattr(collect_verified, "capture_note",
                        lambda *args, **kwargs: [{"asset_sha": "a" * 64}])
    timing = CollectionTiming(tmp_path)
    browser.timing = timing
    rows = browser.receive({"page": page}, {"source": "xiaohongshu"})
    assert rows == [{"asset_sha": "a" * 64}]
    stages = _stages(tmp_path / "timings.jsonl")
    assert {"detail_click", "detail_dom_wait", "detail_return"} <= set(stages)
    assert commands[0] == "click" and commands[-1] == "navigate-back"


def test_pinterest_detail_reuses_the_preview_instead_of_downloading_again(tmp_path, monkeypatch):
    browser = collect_verified.Browser(tmp_path)
    raw = _png(size=(500, 700))
    sha = hashlib.sha256(raw).hexdigest()
    previews = tmp_path / "discovery-previews"
    previews.mkdir()
    preview = previews / f"{sha}.png"
    preview.write_bytes(raw)
    browser.preview = {"url": "https://i.pinimg.com/example.png", "sha": sha, "path": str(preview)}
    browser.command = lambda *args, **kwargs: "{}"
    monkeypatch.setattr(collect_verified, "fetch_pinterest_detail_metadata",
                        lambda *args, **kwargs: {"image_url": "https://i.pinimg.com/example.png"})

    def fail(*args, **kwargs):
        raise AssertionError("the same bytes must not be downloaded twice")

    monkeypatch.setattr(collect_verified.httpx, "stream", fail)
    rows = browser.receive({"page": "https://www.pinterest.com/pin/123/"}, {"source": "pinterest"})
    assert rows and rows[0]["preview_bytes_reused"] is True
    assert rows[0]["asset_sha"] == sha
    assert browser.preview_reused == 1


def test_search_target_counts_independent_named_photos_not_downloads(tmp_path):
    from ref_lab.collage import STATUS_LOW_RESOLUTION, STATUS_NO_COLLAGE, STATUS_SPLIT_OK, usable_named_count

    named = {"asset_sha": "a" * 64, "relevance": {"tier": "target_named"}}
    exploration = {"asset_sha": "b" * 64, "relevance": {"tier": "unconfirmed"}}
    collage_row = {"asset_sha": "c" * 64, "relevance": {"tier": "target_named"}}
    lowres_row = {"asset_sha": "d" * 64, "relevance": {"tier": "target_named"}}
    records = {
        named["asset_sha"]: {"status": STATUS_NO_COLLAGE, "children": []},
        exploration["asset_sha"]: {"status": STATUS_NO_COLLAGE, "children": []},
        collage_row["asset_sha"]: {"status": STATUS_SPLIT_OK, "children": [
            {"status": "valid"}, {"status": "valid"}, {"status": "low_resolution"}]},
        lowres_row["asset_sha"]: {"status": STATUS_LOW_RESOLUTION, "children": [
            {"status": "low_resolution"}, {"status": "low_resolution"}]},
    }
    assert usable_named_count([named, exploration, collage_row, lowres_row], records) == 3
    # An original not yet processed is not guessed as one photo.
    assert usable_named_count([{**named, "asset_sha": "e" * 64}], records) == 0
    assert collage.count_summary(STATUS_SPLIT_OK, records[collage_row["asset_sha"]]["children"])["independent"] == 2
