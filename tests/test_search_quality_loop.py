"""Observed acquisition failures; synthetic pixels never prove visual identity."""
import io
import json
import base64
from types import SimpleNamespace

import pytest
from PIL import Image

from conftest import image_bytes
from tools import collect_adapter as adapter


PIN = "https://www.pinterest.com/pin/874965033874150534/"
TITLE = "其中包含以下圖片：Кана Арима Косплей"


def exercise_pin(monkeypatch, *, title=TITLE, login_wall=False):
    # Valid synthetic file above the existing 10 KiB download threshold. The
    # initial compressed fixture was 7057 bytes and tested that other boundary.
    buffer = io.BytesIO()
    with Image.open(io.BytesIO(image_bytes(seed=137))) as image:
        image.save(buffer, "PNG", compress_level=0)
    original = buffer.getvalue()
    detail_calls, downloads, sessions_stopped = [], [], []
    job = {"project_snapshot": {"character": "有马加奈", "costume": ""},
           "preferred_sources": ["pinterest"]}
    cover = "https://i.pinimg.com/474x/test-cover.jpg"
    detail_image = "https://i.pinimg.com/736x/test-detail.jpg"
    pin = {"title": title, "desc": title, "purl": PIN, "image_url": cover,
           "width": 236, "height": 286}

    def run(cmd, **kwargs):
        if cmd[1:3] == ["session", "start"]:
            return SimpleNamespace(stdout=json.dumps({"session_id": "test-owned"}), returncode=0)
        if cmd[1:3] == ["session", "stop"]:
            sessions_stopped.append(cmd[3])
        return SimpleNamespace(stdout="{}", returncode=0)

    def detail(*args):
        detail_calls.append(args[2])
        return {"title": title, "desc": "", "purl": PIN, "author": "",
                "image_url": detail_image, "width": 736, "height": 889}

    def download(url, **kwargs):
        downloads.append(url)
        return SimpleNamespace(status_code=200, content=original)

    monkeypatch.setattr(adapter.subprocess, "run", run)
    monkeypatch.setattr(adapter.time, "sleep", lambda _: None)
    monkeypatch.setattr(adapter, "build_queries", lambda *a, **k: ["query-one", "query-two"])
    monkeypatch.setattr(adapter, "wait_for_cards", lambda *a, **k: ([pin], login_wall))
    # raising=False makes the pre-fix regression fail at the real dropped output.
    monkeypatch.setattr(adapter, "fetch_pinterest_detail_metadata", detail, raising=False)
    monkeypatch.setattr(adapter.httpx, "get", download)
    result = adapter.fetch_bsk_candidates("synthetic-bsk", "synthetic-browser", job, 1, adapter.build_policy(job))
    return result, original, detail_calls, downloads, sessions_stopped, detail_image


@pytest.mark.parametrize("title", [TITLE, "Arima Kana cosplay", "其中包含以下圖片："])
def test_inconclusive_pin_metadata_reaches_image_review_without_fabricated_pass(monkeypatch, title):
    result, raw, opened, downloads, stopped, detail_image = exercise_pin(monkeypatch, title=title)
    candidates, images, log, _ = result
    assert len(candidates) == 1, ("Missing/foreign metadata must reach bounded visual review", log)
    candidate = candidates[0]
    assert opened == [PIN]
    assert downloads == [detail_image], "Use the observed detail image, not the undersized search cover"
    assert images[candidate["file"].removeprefix("images/")] == raw
    assert candidate["source"]["page_url"] == PIN
    assert candidate["source"]["image_url"] == detail_image
    assert candidate["source"]["source_confirmed"] is False
    assert not candidate.get("preflight")
    assert not any(key in candidate for key in ("decision", "review", "card", "acceptance"))
    assert "needs_detail_evidence:" in candidate["discovery_reason"]
    assert stopped == ["test-owned"]


def test_explicit_wrong_type_stays_excluded_before_detail_or_download(monkeypatch):
    result, _, opened, downloads, stopped, _ = exercise_pin(monkeypatch, title="有马加奈 cosplay 游戏截图")
    assert result[0] == []
    assert opened == downloads == []
    assert stopped == ["test-owned"]


def test_pinterest_login_wall_stops_source_before_occluded_images_are_used(monkeypatch):
    result, _, opened, downloads, stopped, _ = exercise_pin(monkeypatch, login_wall=True)
    assert result[0] == []
    assert opened == downloads == []
    assert len(result[2]) == 1
    assert result[2][0]["stop_reason"] == "login_required"
    assert stopped == ["test-owned"]


def test_login_observation_invalidates_earlier_card_sample(monkeypatch):
    samples = iter([
        {"ok": True, "value": {"cards": [{"title": "previously visible"}]}},
        {"ok": True, "value": {"cards": [{"title": "now occluded"}], "is_login_wall": True}},
    ])
    monkeypatch.setattr(adapter.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=json.dumps(next(samples))))
    monkeypatch.setattr(adapter.time, "sleep", lambda _: None)
    assert adapter.wait_for_cards("synthetic", "owned", "fixture", {}, delay=0) == ([], True)


@pytest.mark.parametrize("returned_url,image_url", [
    ("https://www.pinterest.com/pin/999/", "https://i.pinimg.com/736x/other.jpg"),
    (PIN, "https://pinimg.com.attacker.invalid/736x/image.jpg"),
])
def test_detail_cannot_substitute_another_pin_or_unrelated_host(monkeypatch, returned_url, image_url):
    def run(command, **kwargs):
        data = {"ok": True, "value": {"purl": returned_url, "image_url": image_url}}
        return SimpleNamespace(stdout=json.dumps(data), returncode=0)
    monkeypatch.setattr(adapter.subprocess, "run", run)
    assert adapter.fetch_pinterest_detail_metadata("synthetic", "owned", PIN, {}) == {}


def test_current_detail_uses_observed_url_verbatim(monkeypatch):
    observed = "https://i.pinimg.com/736x/as-provided/image.jpg?variant=visible"
    data = {"ok": True, "value": {"purl": PIN, "image_url": observed, "width": 736, "height": 889}}
    monkeypatch.setattr(adapter.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=json.dumps(data), returncode=0))
    assert adapter.fetch_pinterest_detail_metadata("synthetic", "owned", PIN, {})["image_url"] == observed


def test_detail_dom_uses_primary_image_not_larger_related_pin():
    """Real Chromium DOM, local synthetic images; not live platform evidence."""
    from playwright.sync_api import sync_playwright
    first = "data:image/png;base64," + base64.b64encode(image_bytes(seed=11)).decode()
    related = "data:image/png;base64," + base64.b64encode(image_bytes(seed=12)).decode()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(f'<main><h1>Visible title</h1><img elementtiming="StoryPinImageBlock-MainPinImage" src="{first}" width="200" height="300"><img src="{related}" width="500" height="600"></main>')
            result = page.evaluate(adapter.PINTEREST_DETAIL_JS)
            assert result["image_url"] == first
            assert result["title"] == "Visible title"
            assert result["width"] == 800
        finally:
            browser.close()


def test_detail_dom_stops_at_visible_password_login_overlay():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content('<main><h1>Occluded page</h1></main><div role="dialog" style="position:fixed;inset:0"><form><input type="password"></form></div>')
            result = page.evaluate(adapter.PINTEREST_DETAIL_JS)
            assert result["is_login_wall"] is True
            assert not result.get("image_url")
        finally:
            browser.close()
