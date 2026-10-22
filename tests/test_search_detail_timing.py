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

    def stream(url, target, timeout, limit=20 * 1024 * 1024):
        raw = _png()
        target.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest(), len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    timing = CollectionTiming(tmp_path)
    rows = exact_recall.capture_note("bsk", "session", tmp_path, page, limit=3, timing=timing)
    assert len(rows) == 1 and rows[0]["width"] == 400
    assert rows[0]["temporary"] is True
    # New bytes wait in the bounded temporary area, not in long-term storage.
    assert Path(rows[0]["original_path"]).parent == tmp_path / "incoming"
    assert not (tmp_path / "images").exists()
    stages = _stages(tmp_path / "timings.jsonl")
    for expected in ("detail_locate", "detail_download", "detail_store"):
        assert expected in stages


def test_note_download_stops_at_browser_deadline_and_keeps_first_original(tmp_path,monkeypatch):
    import time
    clock=[0.0];calls=[];raw=_png();page='https://www.xiaohongshu.com/explore/'+'d'*24
    payload={'page_url':page,'text':'synthetic visible DOM','images':[
        {'url':f'https://sns-img.xhscdn.com/{i}.png','width':400,'height':600} for i in range(2)]}
    browser=collect_verified.Browser(tmp_path);browser.bsk='fixture';browser.session='owned';browser.deadline=1.0
    browser.command=lambda *a,**kw:json.dumps({'ok':True,'value':payload})
    browser._probe_detail=lambda:{'url':page}
    browser.snapshot=lambda:{'url':'https://www.xiaohongshu.com/search_result','cards':[{}]}
    def stream(url,target,timeout,limit=20*1024*1024):
        calls.append(timeout);target.write_bytes(raw)
        clock[0]=2.0
        return hashlib.sha256(raw).hexdigest(),len(raw)
    monkeypatch.setattr(time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(exact_recall,'_stream_into_temp',stream)
    rows=browser.receive({'page':page},{'source':'xiaohongshu','query':'西木野真姬'})
    assert len(rows)==len(calls)==1 and calls[0]<=1.0
    assert Path(rows[0]['original_path']).read_bytes()==raw


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
    browser.snapshot = lambda: {'url':'https://www.xiaohongshu.com/search_result',
                               'cards':[{'page':page}]}
    monkeypatch.setattr(collect_verified, "capture_note",
                        lambda *args, **kwargs: [{"asset_sha": "a" * 64}])
    timing = CollectionTiming(tmp_path)
    browser.timing = timing
    rows = browser.receive({"page": page}, {"source": "xiaohongshu", "query": "西木野真姬"})
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
    rows = browser.receive({"page": "https://www.pinterest.com/pin/123/"},
                           {"source": "pinterest", "query": "西木野真姬"})
    assert rows and rows[0]["preview_bytes_reused"] is True
    assert rows[0]["asset_sha"] == sha
    assert rows[0]["temporary"] is True
    assert browser.preview_reused == 1


def test_search_target_counts_independent_named_photos_not_downloads(tmp_path):
    """The unified count: singles + valid tiles, no parent/tile double count."""
    from ref_lab.collage import STATUS_SPLIT_OK, process_original
    from ref_lab.collection_counts import compute
    from tests.test_collage_split import _collage, _textured, _write_original

    folder = tmp_path / "run"
    named = _write_original(folder, _textured((800, 1200), 1, (90, 130, 170)), name="named.png")
    named["relevance"] = {"tier": "target_named"}
    exploration = _write_original(folder, _textured((900, 1200), 2, (140, 90, 70)), name="explore.png")
    exploration["relevance"] = {"tier": "unconfirmed"}
    split_row = _write_original(folder, _collage(2, 1, tile=(800, 600)), name="split.png")
    split_row["relevance"] = {"tier": "target_named"}
    lowres_row = _write_original(folder, _collage(3, 1, tile=(360, 480)), name="lowres.png")
    lowres_row["relevance"] = {"tier": "target_named"}
    rows = [named, exploration, split_row, lowres_row]
    records = {row["asset_sha"]: process_original(folder, row) for row in rows}
    assert records[split_row["asset_sha"]]["status"] == STATUS_SPLIT_OK
    counts = compute(folder, rows, records)
    assert counts["found"] == 4
    assert counts["target_confirmed"] == 3            # originals only
    assert counts["original_singles"] == 2            # named + exploration singles
    assert counts["derived_valid"] == 2               # the 2-panel collage
    assert counts["independent_candidates"] == 4          # 2 singles + 2 tiles
    assert counts["named_candidates"] == 3                # named single + 2 tiles
    assert counts["awaiting_manual"] == 2             # exploration relevance + low-res collage
    # An original not yet processed is not guessed as one photo.
    pending = _write_original(folder, _textured((700, 1000), 3, (60, 90, 60)), name="pending.png")
    pending["relevance"] = {"tier": "target_named"}
    assert compute(folder, [*rows, pending], records)["named_candidates"] == 3
    assert compute(folder, [*rows, pending], records)["unprocessed"] == 1
    assert collage.count_summary(STATUS_SPLIT_OK, records[split_row["asset_sha"]]["children"])["independent"] == 2
