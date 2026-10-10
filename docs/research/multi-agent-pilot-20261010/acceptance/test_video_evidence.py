"""独立 HTTP/Chromium 验收；不读取用户数据库，使用 test_learning_ui 的临时数据夹具。

Run from a target checkout with VERIFIER_TARGET_ROOT set, using that checkout's Python:
  python -m pytest -q <this-file>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
import uvicorn

ROOT = Path(os.environ.get("VERIFIER_TARGET_ROOT", Path(__file__).resolve().parents[2])).resolve()
sys.path.insert(0, str(ROOT))
from ref_lab.api import create_app  # noqa: E402
from ref_lab.config import Settings  # noqa: E402

COURSE_ID = "sword-perspective-chapter"
ROLE_PATTERNS = {
    "A": re.compile(r"A\s*[·:：]|画面(实际)?观察|可见(画面|事实|细节|证据)|这一帧|视频画面", re.I),
    "B": re.compile(r"B\s*[·:：]|摄影师(本人)?[^。；\n]{0,12}(原话|原声|说)|本人原话|现场原话|未(听到|找到|核对|提供)[^。；\n]{0,12}(原话|逐字)|没有[^。；\n]{0,12}原话", re.I),
    "C": re.compile(r"C\s*[·:：]|专业(解释|原理|依据)|独立依据|解释依据|分析依据", re.I),
    "D": re.compile(r"D\s*[·:：]|项目(应用|建议)|待验证(推断|假设)?|现场(应用|调整)|下一步(建议|试拍)", re.I),
}
VIDEO_HOSTS = ("bilibili.com", "youtube.com", "youtu.be", "vimeo.com")
LEGACY_FIELDS = {
    "id", "title", "author", "url", "display", "images", "caption", "alt",
    "rights", "review", "playback", "source_summary",
}
INJECTION = '<img src=x onerror="window.__verifierXss=1"><svg onload="window.__verifierXss=2"></svg>'
TOKEN = "verifier-only-temporary-token-20261010"


@pytest.fixture
def learning_site(tmp_path):
    """Start candidate code against a fresh, disposable data directory."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    web = tmp_path / "web"
    shutil.copytree(ROOT / "web", web)
    app = create_app(Settings(tmp_path / "data", TOKEN, public_origin=origin, web_dir=web))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started, "isolated candidate server did not start"
    try:
        yield origin
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def _course(bundle):
    return next(item for item in bundle["gateways"] if item.get("id") == COURSE_ID)


def _video_cases(course):
    found = []
    for case in course.get("cases", []):
        host = (urlsplit(case.get("url", "")).hostname or "").lower()
        if case.get("playback") and any(host == h or host.endswith("." + h) for h in VIDEO_HOSTS):
            found.append(case)
    return found


def _case(page, case_id):
    return page.locator(".gateway-case").filter(has=page.locator(f'[data-case="{case_id}"]')).first


def _open_course(page, origin):
    session = page.request.post(origin + "/api/session", data={"token": TOKEN})
    assert session.status == 200, session.text()
    page.set_extra_http_headers({"X-Lab-CSRF": session.json()["csrf"]})
    page.goto(f"{origin}/learning?course={COURSE_ID}")
    expect(page.locator("#gateway-dialog")).to_be_visible()
    return page.request.get(f"{origin}/static/learning-atlas.json").json()


def _intercept_bundle(page, transform):
    def handler(route):
        response = route.fetch()
        bundle = response.json()
        transform(bundle)
        route.fulfill(response=response, body=json.dumps(bundle, ensure_ascii=False))

    page.route("**/static/learning-atlas.json", handler)


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_video_examples_visibly_separate_A_B_C_D_and_fit_viewport(learning_site, width, height):
    origin = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        bundle = _open_course(page, origin)
        cases = _video_cases(_course(bundle))
        assert cases, "课程目录中没有可识别的带时间码视频案例"
        # Content is tested through public rendered UI. No candidate JSON key names are assumed.
        for case in cases:
            locator = page.locator(f'.gateway-case[data-case="{case["id"]}"]').first
            expect(locator).to_be_visible()
            text = locator.inner_text()
            missing = [role for role, pattern in ROLE_PATTERNS.items() if not pattern.search(text)]
            assert not missing, f'{case["id"]}: rendered video case lacks explicit evidence roles {missing}'
        assert not page.locator("#gateway-dialog").evaluate("el => el.scrollWidth > el.clientWidth")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        browser.close()


def test_video_links_keep_source_and_timecode_aligned_and_legacy_cases_survive(learning_site):
    origin = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})

        def strip_optional_fields(bundle):
            for case in _video_cases(_course(bundle)):
                for key in list(case):
                    if key not in LEGACY_FIELDS:
                        del case[key]

        _intercept_bundle(page, strip_optional_fields)
        bundle = _open_course(page, origin)
        for case in _video_cases(_course(bundle)):
            locator = page.locator(f'.gateway-case[data-case="{case["id"]}"]').first
            expect(locator).to_be_visible()
            expect(locator).to_contain_text(case["caption"])
            playback = locator.locator("a.case-playback")
            expect(playback).to_have_count(1)
            href = playback.get_attribute("href")
            parsed, expected = urlsplit(href), urlsplit(case["url"])
            assert (parsed.scheme, parsed.hostname, parsed.path) == (expected.scheme, expected.hostname, expected.path)
            assert parse_qs(parsed.query).get("t") == [str(case["playback"]["start"])]
            start, end = case["playback"]["start"], case["playback"]["end"]
            fmt = lambda n: f"{n // 60:02d}:{n % 60:02d}"
            expect(playback).to_contain_text(f"{fmt(start)}–{fmt(end)}")
        browser.close()


def _poison_video_cases(bundle):
    for case in _video_cases(_course(bundle)):
        original_url = case["url"]
        case["title"] = INJECTION
        case["caption"] = INJECTION
        if isinstance(case.get("source_summary"), dict):
            case["source_summary"]["text"] = INJECTION
            case["source_summary"]["locator"] = INJECTION
        for image in case.get("images", []):
            if isinstance(image, dict) and "src" in image:
                image["src"] = "javascript:window.__verifierXss=4"

        def poison_text(value):
            if isinstance(value, dict):
                for key, child in list(value.items()):
                    if key.lower() in {"url", "src", "href"}:
                        value[key] = "javascript:window.__verifierXss=5"
                    elif key not in {"id", "source_id", "media_id", "start", "end", "width", "height"}:
                        value[key] = poison_text(child)
            elif isinstance(value, list):
                return [poison_text(child) for child in value]
            elif isinstance(value, str):
                return INJECTION
            return value

        poison_text(case)
        # Restore stable identity and the adversarial URL after recursive content poisoning.
        case["id"] = case.get("id") or "injection-case"
        case["url"] = original_url


def test_untrusted_case_text_is_inert_and_unsafe_links_never_escape(learning_site):
    origin = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        _intercept_bundle(page, _poison_video_cases)
        bundle = _open_course(page, origin)
        for case in _video_cases(_course(bundle)):
            locator = page.locator(f'.gateway-case[data-case="{case["id"]}"]').first
            expect(locator).to_be_visible()
            assert INJECTION in locator.inner_text()
            assert locator.locator("img[src^='javascript:'], a[href^='javascript:'], img[onerror], svg[onload]").count() == 0
        assert page.evaluate("window.__verifierXss || 0") == 0
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        browser.close()


def test_reading_and_opening_reveals_do_not_change_private_learning_state(learning_site):
    origin = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        bundle = _open_course(page, origin)
        before = page.request.get(origin + "/api/learning-state").json()
        writes = []
        page.on("request", lambda request: writes.append(request.url)
                if request.method in {"PUT", "POST", "DELETE"} else None)
        page.locator('[data-gw-section="principle"]').click()
        page.locator('[data-gw-section="contrast"]').click()
        page.locator('[data-gw-section="sources"]').click()
        for case in _video_cases(_course(bundle)):
            locator = page.locator(f'.gateway-case[data-case="{case["id"]}"]').first
            for details in locator.locator("details").all():
                details.locator("summary").click()
        page.keyboard.press("Escape")
        assert writes == []
        after = page.request.get(origin + "/api/learning-state").json()
        assert after == before
        browser.close()
