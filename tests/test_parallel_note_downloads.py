"""Concurrent note downloads with incremental, ownership-transferring delivery."""
from __future__ import annotations

import hashlib
import io
import json
import threading
import time
from pathlib import Path

import httpx
import pytest
from PIL import Image

from tools import exact_recall


def _png(size=(400, 600), colour=(120, 80, 60)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
    return buffer.getvalue()


def _payload(page: str, count: int) -> dict:
    return {
        "ok": True,
        "value": {
            "page_url": page,
            "text": "标题正文",
            "images": [
                {"url": f"https://sns-img.xhscdn.com/image-{index}.png",
                 "width": 400, "height": 600}
                for index in range(count)
            ],
            "author_detail": {"title": "", "description": "", "author": ""},
        },
    }


class _Completed:
    returncode = 0

    def __init__(self, payload: dict):
        self.stdout = json.dumps(payload)


class _Client:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True


def _bind_note(monkeypatch, page: str, count: int) -> None:
    payload = _payload(page, count)
    monkeypatch.setattr(exact_recall, "run_bsk", lambda *args, **kwargs: _Completed(payload))


def _bind_urls(monkeypatch, page: str, urls: list[str]) -> None:
    payload = _payload(page, len(urls))
    payload["value"]["images"] = [
        {"url": url, "width": 400, "height": 600} for url in urls
    ]
    monkeypatch.setattr(exact_recall, "run_bsk", lambda *args, **kwargs: _Completed(payload))


@pytest.mark.parametrize("url", [
    "https://user@sns-img.xhscdn.com/image.png",
    "https://:secret@sns-img.xhscdn.com/image.png",
    "https://sns-img.xhscdn.com:8443/image.png",
])
def test_capture_note_rejects_untrusted_url_authority(tmp_path, monkeypatch, url):
    page = "https://www.xiaohongshu.com/explore/" + "2" * 23 + "a"
    errors = []

    _bind_urls(monkeypatch, page, [url])
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def must_not_download(*args, **kwargs):
        raise AssertionError("untrusted URL reached download")

    monkeypatch.setattr(exact_recall, "_stream_into_temp", must_not_download)

    rows = exact_recall.capture_note(
        "bsk", "session", tmp_path, page, errors=errors,
    )

    assert rows == []
    assert len(errors) == 1 and "Untrusted image host" in errors[0]["error"]


def test_capture_note_preserves_query_and_allows_explicit_https_port(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "3" * 23 + "a"
    url = "https://sns-img.xhscdn.com:443/path/image.png?imageView2=2&xsec_token=synthetic"
    raw = _png()
    requested = []

    _bind_urls(monkeypatch, page, [url])
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def stream(observed, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        requested.append(observed)
        target.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest(), len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    rows = exact_recall.capture_note("bsk", "session", tmp_path, page)

    assert requested == [url]
    assert len(rows) == 1 and rows[0]["image_url"] == url


def test_four_downloads_share_client_and_emit_each_row_on_the_consumer_thread(
        tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "a" * 24
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    caller = threading.get_ident()
    barrier = threading.Barrier(4)
    clients: list[_Client] = []
    streams: list[_Client] = []

    class Client(_Client):
        def __init__(self):
            super().__init__()
            clients.append(self)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        assert client is not None
        streams.append(client)
        barrier.wait(timeout=5)
        target.write_bytes(raw)
        return sha, len(raw)

    _bind_note(monkeypatch, page, 4)
    monkeypatch.setattr(exact_recall.httpx, "Client", Client)
    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)

    formal = tmp_path / "formal"
    formal.mkdir()
    callbacks = []

    def on_record(row):
        callbacks.append((threading.get_ident(), row))
        target = formal / f"{row['image_index']}.png"
        Path(row["original_path"]).replace(target)
        row["original_path"] = str(target)
        row["temporary"] = False
        row["delivered"] = True

    rows = exact_recall.capture_note(
        "bsk", "session", tmp_path, page, limit=4, on_record=on_record,
    )

    assert len(rows) == len(callbacks) == 4
    assert len(clients) == 1 and clients[0].closed
    assert {id(client) for client in streams} == {id(clients[0])}
    assert all(thread == caller for thread, _ in callbacks)
    assert all(any(row is callback_row for _, callback_row in callbacks) for row in rows)
    assert all(row["temporary"] is False and row["delivered"] is True for row in rows)
    assert sorted(path.name for path in formal.iterdir()) == ["1.png", "2.png", "3.png", "4.png"]
    assert list((tmp_path / "incoming").glob("*")) == []


def test_partial_download_failure_keeps_and_delivers_the_other_rows(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "b" * 24
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    errors = []

    _bind_note(monkeypatch, page, 4)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        assert client is not None
        if url.endswith("image-2.png"):
            target.write_bytes(b"partial")
            raise ValueError("synthetic download failure")
        target.write_bytes(raw)
        return sha, len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    formal = tmp_path / "formal"
    formal.mkdir()
    delivered = []

    def on_record(row):
        delivered.append(row["image_index"])
        target = formal / f"{row['image_index']}.png"
        Path(row["original_path"]).replace(target)
        row["original_path"] = str(target)
        row["temporary"] = False

    rows = exact_recall.capture_note(
        "bsk", "session", tmp_path, page, limit=4, errors=errors,
        on_record=on_record,
    )

    assert sorted(row["image_index"] for row in rows) == [1, 2, 4]
    assert sorted(delivered) == [1, 2, 4]
    assert len(errors) == 1 and errors[0]["image_index"] == 3
    assert "synthetic download failure" in errors[0]["error"]
    assert sorted(path.name for path in formal.iterdir()) == ["1.png", "2.png", "4.png"]
    assert list((tmp_path / "incoming").glob("*")) == []


def test_successful_callback_owns_the_file_and_returned_rows_are_the_same_objects(
        tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "c" * 24
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    unlinks = []
    original_unlink = Path.unlink

    def tracked_unlink(path, *args, **kwargs):
        unlinks.append(Path(path))
        return original_unlink(path, *args, **kwargs)

    _bind_note(monkeypatch, page, 1)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)
    monkeypatch.setattr(Path, "unlink", tracked_unlink)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        assert client is not None
        target.write_bytes(raw)
        return sha, len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    formal = tmp_path / "formal" / "owned.png"
    formal.parent.mkdir()
    callback_rows = []

    def on_record(row):
        callback_rows.append(row)
        Path(row["original_path"]).replace(formal)
        row["original_path"] = str(formal)
        row["temporary"] = False
        row["delivered"] = True

    rows = exact_recall.capture_note(
        "bsk", "session", tmp_path, page, limit=1, on_record=on_record,
    )

    assert len(rows) == len(callback_rows) == 1 and rows[0] is callback_rows[0]
    assert formal.read_bytes() == raw
    assert rows[0]["original_path"] == str(formal) and rows[0]["delivered"] is True
    assert unlinks == []
    assert list((tmp_path / "incoming").glob("*")) == []


def test_callback_failure_is_not_recorded_as_a_download_failure(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "d" * 24
    raw = _png()
    errors = []

    _bind_note(monkeypatch, page, 1)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        target.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest(), len(raw)

    def reject(row):
        raise RuntimeError("delivery store unavailable")

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    with pytest.raises(RuntimeError, match="delivery store unavailable"):
        exact_recall.capture_note(
            "bsk", "session", tmp_path, page, errors=errors, on_record=reject,
        )

    assert errors == []
    # Ownership transfers before the callback; a failed delivery leaves bytes recoverable.
    assert len(list((tmp_path / "incoming").glob("*.part"))) == 1


@pytest.mark.parametrize("status", [401, 403, 429])
def test_http_source_restriction_stops_new_work_but_drains_in_flight(
        tmp_path, monkeypatch, status):
    page = "https://www.xiaohongshu.com/explore/" + "e" * 24
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    errors = []
    calls = []

    _bind_note(monkeypatch, page, 6)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        calls.append(url)
        if url.endswith("image-0.png"):
            time.sleep(0.01)
            response = httpx.Response(status, request=httpx.Request("GET", url))
            response.raise_for_status()
        time.sleep(0.1)
        target.write_bytes(raw)
        return sha, len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    rows = exact_recall.capture_note(
        "bsk", "session", tmp_path, page, limit=6, errors=errors,
    )

    assert len(calls) == 4 and len(rows) == 3
    assert len(errors) == 1
    assert errors[0]["source_restricted"] == status
    assert 0 <= errors[0]["remaining_futures"] <= 3
    assert errors[0]["queued_skipped"] == 2


def test_decode_failure_keeps_other_rows_in_the_window(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "1" * 23 + "a"
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    errors = []

    _bind_note(monkeypatch, page, 4)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        content = b"not an image" if url.endswith("image-2.png") else raw
        target.write_bytes(content)
        return hashlib.sha256(content).hexdigest(), len(content)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    rows = exact_recall.capture_note(
        "bsk", "session", tmp_path, page, limit=4, errors=errors,
    )

    assert [row["image_index"] for row in rows] == [1, 2, 4]
    assert len(errors) == 1 and errors[0]["image_index"] == 3
    assert len(list((tmp_path / "incoming").glob("*.part"))) == 3


def test_executor_refills_only_after_the_four_active_downloads_finish(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "0" * 23 + "a"
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    real_pool = exact_recall.ThreadPoolExecutor
    submitted = []
    first_started = threading.Event()
    release = threading.Event()
    result = {}

    class TrackingPool(real_pool):
        def submit(self, fn, /, *args, **kwargs):
            submitted.append(fn)
            return super().submit(fn, *args, **kwargs)

    _bind_note(monkeypatch, page, 6)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)
    monkeypatch.setattr(exact_recall, "ThreadPoolExecutor", TrackingPool)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        first_started.set()
        release.wait(timeout=5)
        target.write_bytes(raw)
        return sha, len(raw)

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)

    def run():
        result["rows"] = exact_recall.capture_note(
            "bsk", "session", tmp_path, page, limit=6, errors=[],
        )

    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert first_started.wait(timeout=5)
        time.sleep(0.05)
        assert len(submitted) == 4
    finally:
        release.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert len(submitted) == 6
    assert len(result["rows"]) == 6


def test_successful_transfer_survives_a_callback_exception(tmp_path, monkeypatch):
    page = "https://www.xiaohongshu.com/explore/" + "f" * 24
    raw = _png()
    formal = tmp_path / "formal" / "transferred.png"
    formal.parent.mkdir()

    _bind_note(monkeypatch, page, 1)
    monkeypatch.setattr(exact_recall.httpx, "Client", _Client)

    def stream(url, target, timeout, limit=20 * 1024 * 1024, *, client=None):
        target.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest(), len(raw)

    def transfer_then_fail(row):
        Path(row["original_path"]).replace(formal)
        row["original_path"] = str(formal)
        row["temporary"] = False
        raise RuntimeError("database refused the transferred row")

    monkeypatch.setattr(exact_recall, "_stream_into_temp", stream)
    with pytest.raises(RuntimeError, match="database refused"):
        exact_recall.capture_note(
            "bsk", "session", tmp_path, page, on_record=transfer_then_fail,
        )

    assert formal.read_bytes() == raw
