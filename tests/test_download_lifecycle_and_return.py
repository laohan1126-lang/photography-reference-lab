"""Download lifecycle and page-return recovery regressions (2026-10-22).

These protect the user-visible failures from the renewed formal runs:

* a timed-out ``navigate-back`` whose page is actually restored must not leave a
  stale ``return_error`` that stops the Job later;
* recovery budget is measured by real recovery work, not by normal collection
  wall time after the first recovery;
* a page-return fault is repaired in the same session (original query first)
  instead of blindly rebuilding it, and it is handled before heavy dedup;
* unknown bytes wait in a bounded temporary area, known source addresses are not
  transferred again, known exact bytes are deleted immediately after streaming.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote

import pytest
from PIL import Image

from ref_lab.browser_recovery import BrowserInfrastructureError
from tools import collect_verified as worker
from tools import exact_recall
from tests.test_browserskill_recovery import SyntheticAgent, _job


def _png(size=(400, 600), colour=(120, 80, 60)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
    return buffer.getvalue()


def _page_payload(query: str, cards: int = 1, page: str | None = None) -> dict:
    page = page or "https://www.xiaohongshu.com/explore/" + "e" * 24
    return {"url": "https://www.xiaohongshu.com/search_result?keyword=" + quote(query),
            "search": query, "visibleMain": "",
            "cards": [{"page": page, "text": query, "cover_url": "",
                       "cover_width": 400, "cover_height": 600} for _ in range(cards)],
            "login_required": False, "challenge": False}


def _note_payload(page: str, urls: list[str]) -> dict:
    return {"ok": True, "value": {"page_url": page, "text": "西木野真姬 cos 摄影",
                                  "images": [{"url": url, "width": 400, "height": 600} for url in urls],
                                  "author_detail": {"title": "", "description": "", "author": ""}}}


# --- page-return verification -------------------------------------------------

def test_return_timeout_on_an_already_restored_page_leaves_no_stale_error(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "a" * 24
    query = "西木野真姬"
    good = _page_payload(query)

    browser = worker.Browser(tmp_path)
    browser.bsk, browser.session = "bsk", "session-1"

    def command(*args, timeout=35, **kwargs):
        if args[0] == "navigate-back":
            raise BrowserInfrastructureError("BrowserSkill command timed out", action="navigate-back",
                                             code="command_timeout", is_timeout=True)
        if args[0] == "evaluate":
            return json.dumps({"ok": True, "value": good})
        return json.dumps({"session_id": "session-1"})

    browser.command = command
    browser._probe_detail = lambda: {"url": page}
    monkeypatch.setattr(worker, "capture_note", lambda *a, **k: [])
    browser.receive({"page": page}, {"source": "xiaohongshu", "query": query})

    assert browser.return_error is None
    assert browser.return_failed is False
    checks = json.loads((tmp_path / "return-checks.json").read_text("utf8"))
    assert checks[-1]["confirmed"] is True
    assert checks[-1]["navigate_back_error"] == "BrowserInfrastructureError"
    assert checks[-1]["session_id"] == "session-1"


def test_return_timeout_with_the_wrong_page_keeps_the_error(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "c" * 24
    query = "西木野真姬"
    wrong = {"url": "https://www.xiaohongshu.com/search_result", "search": "",
             "visibleMain": "", "cards": [], "login_required": False, "challenge": False}

    browser = worker.Browser(tmp_path)
    browser.bsk, browser.session = "bsk", "session-2"

    def command(*args, timeout=35, **kwargs):
        if args[0] == "navigate-back":
            raise BrowserInfrastructureError("BrowserSkill command timed out", action="navigate-back",
                                             code="command_timeout", is_timeout=True)
        if args[0] == "evaluate":
            return json.dumps({"ok": True, "value": wrong})
        return json.dumps({"session_id": "session-2"})

    browser.command = command
    browser._probe_detail = lambda: {"url": page}
    monkeypatch.setattr(worker, "capture_note", lambda *a, **k: [])
    browser.receive({"page": page}, {"source": "xiaohongshu", "query": query})

    assert browser.return_error is not None
    assert browser.return_failed is True
    assert browser.return_issue_category == "page_return"
    checks = json.loads((tmp_path / "return-checks.json").read_text("utf8"))
    assert checks[-1]["confirmed"] is False


# --- recovery budget ----------------------------------------------------------

def test_recovery_budget_ignores_normal_work_after_the_first_recovery(tmp_path, monkeypatch):
    browser = worker.Browser(tmp_path)
    browser.bsk, browser.browser_id, browser.session = "bsk", "browser", "session"
    clock = [100.0]
    monkeypatch.setattr(worker.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(worker.time, "time", lambda: clock[0])

    def rebuild():
        clock[0] += 3.0
        return True

    monkeypatch.setattr(browser, "_rebuild_session", rebuild)
    assert browser.recover() is True
    assert browser.recovery_seconds_used == pytest.approx(3.0)

    # 100 seconds of ordinary collection work follow; it must not consume the
    # 60 second recovery allowance. A second recoverable fault still recovers.
    clock[0] += 100.0
    assert browser.can_recover() is True
    assert browser.recover() is True
    assert browser.recovery_attempts == 2
    assert browser.recovery_seconds_used == pytest.approx(6.0)


def test_recovery_is_refused_once_real_recovery_time_is_spent(tmp_path):
    browser = worker.Browser(tmp_path)
    browser.recovery_seconds_used = 60.0
    browser.recovery_attempts = 1
    assert browser.can_recover() is False


# --- in-place page-return repair ---------------------------------------------

def test_return_recovery_revisits_the_original_query_before_rebuilding(tmp_path, monkeypatch):
    query = "西木野真姬"
    page = "https://www.xiaohongshu.com/explore/" + "f" * 24
    good = _page_payload(query, page=page)
    bad = {"url": "https://www.xiaohongshu.com/search_result", "search": "",
           "visibleMain": "", "cards": [], "login_required": False, "challenge": False}
    pages = [bad, good]
    commands: list[str] = []

    browser = worker.Browser(tmp_path)
    browser.bsk, browser.browser_id, browser.session = "bsk", "browser", "session-1"

    def command(*args, timeout=35, **kwargs):
        commands.append(args[0])
        if args[0] == "evaluate":
            return json.dumps({"ok": True, "value": pages.pop(0) if pages else good})
        return json.dumps({"ok": True})

    browser.command = command
    browser.return_failed = True
    browser.return_issue_category = "page_return"
    browser.return_error = BrowserInfrastructureError("timed out", action="navigate-back",
                                                      code="command_timeout", is_timeout=True)
    assert browser.recover({"source": "xiaohongshu", "query": query}, reason="return") is True
    assert browser.session == "session-1"          # same session, not rebuilt
    assert browser.return_error is None
    assert "navigate" in commands and "session" not in commands


# --- download lifecycle -------------------------------------------------------

class _Completed:
    returncode = 0

    def __init__(self, payload: dict):
        self.stdout = json.dumps(payload)


def test_known_source_address_is_not_transferred_again(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "b" * 24
    url = "https://sns-img.xhscdn.com/known-rendition.jpg"
    monkeypatch.setattr(exact_recall.subprocess, "run",
                        lambda *a, **k: _Completed(_note_payload(page, [url])))

    def fail(*args, **kwargs):
        raise AssertionError("a known source address must not be downloaded again")

    monkeypatch.setattr(exact_recall, "_stream_into_temp", fail)
    rows = exact_recall.capture_note("bsk", "session", tmp_path, page,
                                     known_sources={exact_recall.normalize_image_url(url): "b" * 64})
    assert rows and rows[0]["duplicate"] is True
    assert rows[0]["reason"] == "known_source_url"
    assert rows[0]["asset_sha"] == "b" * 64
    assert not (tmp_path / "images").exists()


def test_known_bytes_delete_the_temporary_copy_immediately(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "d" * 24
    url = "https://sns-img.xhscdn.com/already-seen.jpg"
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(exact_recall.subprocess, "run",
                        lambda *a, **k: _Completed(_note_payload(page, [url])))

    def stream(url_arg, target, timeout, limit=20 * 1024 * 1024):
        target.write_bytes(raw)
        return sha, len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    rows = exact_recall.capture_note("bsk", "session", tmp_path, page, known_shas={sha})
    assert rows and rows[0]["duplicate"] is True
    assert rows[0]["reason"] == "same_bytes_known"
    assert rows[0]["bytes_received"] == len(raw)
    assert list((tmp_path / "incoming").glob("*")) == []
    assert not (tmp_path / "images").exists()


def test_unknown_bytes_are_promoted_only_after_history_judgement(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "a" * 24
    raw = _png()
    note = {"page": page, "text": "西木野真姬 cos 摄影", "cover_url": "", "cover_width": 400, "cover_height": 600}

    class Browser:
        supports_sort = True

        def __init__(self, folder):
            self.folder = folder
            self.session = "owned"
            self.deadline = float("inf")
            self.return_failed = False
            self.return_error = None
            self.preview_reused = 0
            self.download_errors = []
            self.note_image_limit = 3

        def start(self):
            pass

        def close(self):
            pass

        def search(self, step, sort="relevance"):
            return _page_payload(step["query"], page=page)

        def more(self, step):
            return _page_payload(step["query"], page=page)

        def receive(self, card, step):
            incoming = self.folder / "incoming"
            incoming.mkdir(exist_ok=True)
            path = incoming / f"{hashlib.sha256(raw).hexdigest()}.png.part"
            path.write_bytes(raw)
            return [{"asset_sha": hashlib.sha256(raw).hexdigest(), "original_path": str(path),
                     "page_url": page, "image_url": "https://sns-img.xhscdn.com/new.jpg",
                     "source_text": "西木野真姬 cos 摄影", "width": 400, "height": 600, "ext": "png",
                     "temporary": True}]

    browser = Browser(tmp_path)
    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), browser, tmp_path, search_only=True)
    rows = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert rows and Path(rows[0]["original_path"]).parent == tmp_path / "images"
    assert Path(rows[0]["original_path"]).is_file()
    assert list((tmp_path / "incoming").glob("*")) == []
    assert "temporary" not in rows[0]
    assert summary["incoming_cleaned"]["files"] == 0


def test_page_return_fault_is_handled_before_heavy_history_compare(tmp_path):
    page = "https://www.xiaohongshu.com/explore/" + "a" * 24

    class Browser:
        supports_sort = True

        def __init__(self, folder):
            self.folder = folder
            self.session = "owned"
            self.deadline = float("inf")
            self.return_failed = True
            self.return_issue_category = "page_return"
            self.return_error = BrowserInfrastructureError("timed out", action="navigate-back",
                                                           code="command_timeout", is_timeout=True)
            self.preview_reused = 0
            self.download_errors = []
            self.note_image_limit = 3

        def start(self):
            pass

        def close(self):
            pass

        def can_recover(self):
            return False

        def recover(self, step=None, reason="connection"):
            raise AssertionError("no recovery credit must be invented")

        def search(self, step, sort="relevance"):
            self.return_failed = False
            self.return_error = None
            return _page_payload(step["query"], page=page)

        def more(self, step):
            return self.search(step)

        def receive(self, card, step):
            self.return_failed = True
            self.return_error = BrowserInfrastructureError("timed out", action="navigate-back",
                                                           code="command_timeout", is_timeout=True)
            self.return_issue_category = "page_return"
            return []

    class NoCompareHistory:
        known_shas = set()
        known_count = 0
        ready = True

        def consider(self, path):
            raise AssertionError("history matching must run only after the return fault is handled")

    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), Browser(tmp_path), tmp_path,
                                search_only=True, history=NoCompareHistory())
    state = json.loads((tmp_path / "collector-state.json").read_text("utf8"))
    assert summary["stop_reason"] == "command_timeout"
    assert state.get("return_pending_rows")

# --- concurrency and promotion bookkeeping -------------------------------

def test_concurrent_consider_admits_one_original(tmp_path):
    import threading
    from ref_lab.collection_history import ImageHistory
    from tests.test_collage_split import _textured

    path = tmp_path / "one.png"
    _textured((800, 600), 7, (10, 120, 200)).save(path)
    history = ImageHistory([])
    results = []

    def run():
        results.append(history.consider(path))

    threads = [threading.Thread(target=run) for _ in range(4)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()

    assert sum(1 for result in results if result is None) == 1
    assert sum(1 for result in results if (result or {}).get("reason") == "same_bytes") == 3
    assert len(history.records) == 1


def test_rekey_follows_the_promoted_original(tmp_path):
    from ref_lab.collection_history import ImageHistory
    from tests.test_collage_split import _textured

    temp = tmp_path / "incoming" / "x.part"
    temp.parent.mkdir()
    _textured((800, 600), 9, (200, 120, 10)).save(temp, format="PNG")
    final = tmp_path / "images" / "final.png"
    final.parent.mkdir()
    history = ImageHistory([])
    assert history.consider(temp) is None
    temp.replace(final)
    history.rekey(temp, final)
    assert history.match(final)["reason"] == "same_bytes"


def test_received_original_is_linked_not_duplicated_by_the_asset_store(tmp_path):
    from ref_lab.config import Settings
    from ref_lab.storage import AssetStore

    source = tmp_path / "run" / "images" / "received.png"
    source.parent.mkdir(parents=True)
    raw = _png()
    source.write_bytes(raw)
    store = AssetStore(Settings(tmp_path / "data", "test-token-0123456789abcdef", public_origin="http://testserver"))
    meta = store.ingest(raw, source.name, source_path=source)
    stored = store.path(meta)
    assert stored.read_bytes() == raw
    assert stored.stat().st_ino == source.stat().st_ino
    source.unlink()
    assert stored.read_bytes() == raw and store.verify(meta)


def test_asset_store_falls_back_when_the_source_cannot_be_linked(tmp_path):
    from ref_lab.config import Settings
    from ref_lab.storage import AssetStore

    raw = _png()
    missing = tmp_path / "run" / "images" / "not-there.png"
    store = AssetStore(Settings(tmp_path / "data", "test-token-0123456789abcdef", public_origin="http://testserver"))
    meta = store.ingest(raw, "not-there.png", source_path=missing)
    stored = store.path(meta)
    assert stored.read_bytes() == raw and store.verify(meta)


def test_cleaned_archived_run_is_skipped_without_hiding_live_bytes(tmp_path):
    from ref_lab.collection_history import historical_paths

    root = tmp_path / "root"
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    asset = root / "data" / "assets" / sha[:2] / sha / "original.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(raw)

    run = root / ".local" / "collection-runs" / "old-run"
    run.mkdir(parents=True)
    (run / "received.json").write_text(json.dumps([
        {"asset_sha": sha, "original_path": str(run / "images" / f"{sha}.png")}]), "utf8")

    skipped = []
    paths = historical_paths(root, root / ".local" / "collection-runs" / "current", skipped=skipped)
    assert [str(p) for p in paths] == [str(asset.resolve())]
    assert len(skipped) == 1
    assert skipped[0]["received_rows"] == 1

    # A run that still holds files must fail loudly instead of silently hiding them.
    stale = run / "images" / "not-the-sha.png"
    stale.parent.mkdir()
    stale.write_bytes(raw)
    with pytest.raises(ValueError):
        historical_paths(root, root / ".local" / "collection-runs" / "current", skipped=[])

def test_capture_note_creates_a_missing_temporary_area(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "e" * 24
    url = "https://sns-img.xhscdn.com/needs-temp-dir.jpg"
    raw = _png()
    monkeypatch.setattr(exact_recall.subprocess, "run",
                        lambda *a, **k: _Completed(_note_payload(page, [url])))

    def stream(url_arg, target, timeout, limit=20 * 1024 * 1024):
        target.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest(), len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    missing = tmp_path / "not-created-yet"
    rows = exact_recall.capture_note("bsk", "session", tmp_path, page, incoming=missing)
    assert rows and rows[0]["temporary"] is True
    assert Path(rows[0]["original_path"]).parent == missing
    assert Path(rows[0]["original_path"]).read_bytes() == raw
