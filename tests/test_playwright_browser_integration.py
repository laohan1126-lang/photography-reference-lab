from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json
import time
from types import SimpleNamespace

import pytest

from ref_lab.browser_recovery import BrowserInfrastructureError, DetailItemError
from tools import collect_verified as worker


class FakeError(Exception):
    pass


class FakeTimeout(FakeError):
    pass


class FakeTargetClosed(FakeError):
    pass


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector
        self.first = self

    async def click(self, timeout):
        self.page.calls.append(("click", self.selector, timeout))
        if self.page.locator_result:
            raise self.page.locator_result

    async def hover(self, timeout):
        self.page.calls.append(("hover", self.selector, timeout))
        if self.page.locator_result:
            raise self.page.locator_result

    async def count(self):
        return self.page.locator_count


class FakeMouse:
    def __init__(self, page):
        self.page = page

    async def wheel(self, x, y):
        self.page.calls.append(("wheel", x, y))


class FakePage:
    url = "https://example.test/search"

    def __init__(self):
        self.calls = []
        self.closed = False
        self.locator_result = None
        self.locator_count = 1
        self.mouse = FakeMouse(self)

    async def evaluate(self, script):
        self.calls.append(("evaluate", script))
        return {"cards": ["fixture"]}

    async def goto(self, url, wait_until, timeout):
        self.calls.append(("goto", url, wait_until, timeout))
        return SimpleNamespace(status=200)

    async def go_back(self, wait_until, timeout):
        self.calls.append(("go_back", wait_until, timeout))

    async def close(self, run_before_unload):
        self.closed = True
        self.calls.append(("close", run_before_unload))

    def locator(self, selector):
        self.calls.append(("locator", selector))
        return FakeLocator(self, selector)


def fake_api():
    return FakeError, FakeTimeout, FakeTargetClosed, lambda: None


def browser_for_commands(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "resolve_profile", lambda profile, **kwargs: worker.Path(profile).resolve())
    folder = tmp_path / "run"
    folder.mkdir()
    browser = worker.PlaywrightBrowser(folder, tmp_path / "profile")
    browser._runner = asyncio.Runner()
    browser._page = FakePage()
    browser.session = "pw-session"
    browser.deadline = worker.time.monotonic() + 60
    monkeypatch.setattr(worker.PlaywrightBrowser, "_load_api", staticmethod(fake_api))
    return browser


class SourceContext:
    def __init__(self):
        self.pages = []
        self.closed = False

    async def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page

    async def close(self):
        self.closed = True


def test_factory_keeps_bsk_default_and_requires_explicit_profile(tmp_path, monkeypatch):
    assert type(worker.make_browser(tmp_path)) is worker.Browser
    with pytest.raises(ValueError, match="playwright-profile"):
        worker.make_browser(tmp_path, "playwright")
    with pytest.raises(ValueError, match="browser-backend playwright"):
        worker.make_browser(tmp_path, "bsk", tmp_path / "profile")

    class FakePlaywrightBrowser:
        def __init__(self, folder, profile):
            self.folder, self.profile = folder, profile

    monkeypatch.setattr(worker, "PlaywrightBrowser", FakePlaywrightBrowser)
    selected = worker.make_browser(tmp_path, "playwright", tmp_path / "profile")
    assert selected.folder == tmp_path
    assert selected.profile == tmp_path / "profile"


def test_command_shapes_match_existing_browser_calls(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    page = browser._page

    evaluated = json.loads(
        browser.command("evaluate", "--session", "pw-session", "--json", "()=>({cards:[]})")
    )
    assert evaluated == {"ok": True, "value": {"cards": ["fixture"]}}

    browser.command("navigate", "https://example.test/search", "--session", "pw-session",
                    "--wait-until", "commit", "--timeout", "50s", timeout=60)
    browser.command("click", "--selector", "a.cover[href*=abc]", "--session", "pw-session")
    browser.command("hover", "--selector", "body>div:nth-child(1)", "--session", "pw-session")
    browser.command("wheel", "--delta-y", "1800", "--session", "pw-session",
                    "--timeout", "10s", timeout=15)

    assert ("evaluate", "()=>({cards:[]})") in page.calls
    assert ("goto", "https://example.test/search", "commit", 50_000) in page.calls
    assert ("click", "a.cover[href*=abc]", 35_000) in page.calls
    assert ("hover", "body>div:nth-child(1)", 35_000) in page.calls
    assert ("wheel", 0, 1800.0) in page.calls
    browser.close()


def test_command_parser_covers_every_collector_shape():
    parsed = worker.PlaywrightBrowser._parse_command(
        ("evaluate", "--session", "s", "--json", "()=>1")
    )
    assert parsed == ("evaluate", {"session": "s", "json": True}, ["()=>1"])
    assert worker.PlaywrightBrowser._parse_command(
        ("navigate", "https://example.test/", "--session", "s", "--wait-until", "commit",
         "--timeout", "50s")
    ) == ("navigate", {"session": "s", "wait-until": "commit", "timeout": "50s"},
          ["https://example.test/"])
    assert worker.PlaywrightBrowser._parse_command(
        ("click", "--selector", "a[href*=x]", "--session", "s")
    ) == ("click", {"selector": "a[href*=x]", "session": "s"}, [])
    assert worker.PlaywrightBrowser._parse_command(
        ("hover", "--selector", "body>div", "--session", "s")
    ) == ("hover", {"selector": "body>div", "session": "s"}, [])
    assert worker.PlaywrightBrowser._parse_command(
        ("wheel", "--delta-y", "1800", "--session", "s", "--timeout", "10s")
    ) == ("wheel", {"delta-y": "1800", "session": "s", "timeout": "10s"}, [])


def test_persistent_playwright_loop_advances_while_caller_is_idle():
    from ref_lab.playwright_runtime import PlaywrightLoop

    runtime = PlaywrightLoop("persistent-loop-test")
    count = [0]

    async def ticker():
        while True:
            count[0] += 1
            await asyncio.sleep(.01)

    async def read():
        return count[0]

    runtime.start()
    future = runtime.submit(ticker())
    first = runtime.run(read(), 1_000)
    time.sleep(.05)
    second = runtime.run(read(), 1_000)
    runtime.stop()
    assert second > first
    assert future.done()
    assert not runtime.thread


def test_source_navigation_reuses_exactly_two_owned_pages(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    context = SourceContext()
    browser._context = context
    browser._pages = {}

    browser.command("navigate", "https://www.xiaohongshu.com/search_result?keyword=a",
                    "--session", "pw-session")
    xhs = browser._page
    browser.command("navigate", "https://www.pinterest.com/search/pins/?q=b",
                    "--session", "pw-session")
    pinterest = browser._page
    browser.command("navigate", "https://www.xiaohongshu.com/search_result?keyword=c",
                    "--session", "pw-session")

    assert len(context.pages) == 2 and len(browser._pages) == 2
    assert browser._page is xhs and xhs is not pinterest
    assert [call[1] for call in xhs.calls if call[0] == "goto"] == [
        "https://www.xiaohongshu.com/search_result?keyword=a",
        "https://www.xiaohongshu.com/search_result?keyword=c"]
    assert [call[1] for call in pinterest.calls if call[0] == "goto"] == [
        "https://www.pinterest.com/search/pins/?q=b"]
    browser.close()


def test_back_uses_the_selected_sources_own_history_page(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    context = SourceContext(); browser._context = context; browser._pages = {}
    xhs = browser._select_source("xiaohongshu")
    browser._select_source("pinterest")
    assert browser._select_source("xiaohongshu") is xhs
    browser._go_back()
    assert ("go_back", "commit", 10_000) in xhs.calls
    assert not any(call[0] == "go_back" for call in context.pages[1].calls)
    browser.close()


def test_close_includes_every_owned_source_page(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    context = SourceContext(); browser._context = context; browser._pages = {}
    xhs = browser._select_source("xiaohongshu")
    pinterest = browser._select_source("pinterest")
    browser.close()
    assert xhs.closed and pinterest.closed and context.closed


def test_selector_and_network_errors_keep_existing_boundaries(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    browser._page.locator_result = FakeTimeout("selector did not match")
    browser._page.locator_count = 0
    with pytest.raises(DetailItemError):
        browser.command("click", "--selector", "a.cover[href*=missing]", "--session", "pw-session")

    async def fail_goto(*args, **kwargs):
        raise FakeError("net::ERR_CONNECTION_RESET")

    browser._page.goto = fail_goto
    with pytest.raises(BrowserInfrastructureError) as failure:
        browser.command("navigate", "https://example.test/fail", "--session", "pw-session")
    assert failure.value.code == "action_failed"
    assert not browser.can_recover()

    browser._page.locator_count = 1
    with pytest.raises(BrowserInfrastructureError) as timeout:
        browser.command("hover", "--selector", "body>div:nth-child(1)", "--session", "pw-session")
    assert timeout.value.is_timeout
    assert timeout.value.effect_state == "unknown"
    browser.close()


def test_stuck_evaluate_is_bounded_unknown_and_releases_profile(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    released = []

    @contextmanager
    def tracked_lock(profile):
        try:
            yield
        finally:
            released.append(profile)

    monkeypatch.setattr(worker, "profile_lock", tracked_lock)
    browser._lock_guard = tracked_lock(browser.profile)
    browser._lock_guard.__enter__()

    async def stuck(script):
        await asyncio.sleep(60)

    browser._page.evaluate = stuck
    with pytest.raises(BrowserInfrastructureError) as error:
        browser.command("evaluate", "--session", "pw-session", "--json", "stuck()", timeout=0.05)
    assert error.value.code == "command_timeout"
    assert error.value.is_timeout and error.value.effect_state == "unknown"
    browser.close()
    assert released == [browser.profile]
    assert browser._runner is None
    assert browser.session is None


def test_profile_enter_failure_is_mapped_and_runner_close_cannot_skip_lock_release(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "resolve_profile", lambda value, **kwargs: worker.Path(value).resolve())
    folder = tmp_path / "run"
    folder.mkdir()

    class LockFailure:
        def __enter__(self):
            raise worker.TrialError("synthetic profile busy")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(worker.PlaywrightBrowser, "_load_api", staticmethod(fake_api))
    monkeypatch.setattr(worker, "profile_lock", lambda value: LockFailure())
    browser = worker.PlaywrightBrowser(folder, tmp_path / "profile")
    with pytest.raises(BrowserInfrastructureError) as error:
        browser.start()
    assert error.value.code == "profile_unavailable"

    released = []

    @contextmanager
    def tracked_lock(value):
        try:
            yield
        finally:
            released.append(value)

    class BadRunner:
        def close(self):
            raise FakeError("synthetic runner close failure")

    lock = tracked_lock(browser.profile)
    lock.__enter__()
    browser._runner = BadRunner()
    browser._lock_guard = lock
    failures = browser._release_resources(FakeError, FakeTimeout, FakeTargetClosed)
    assert failures and failures[0].code == "action_failed"
    assert released == [browser.profile]
    assert browser._runner is None


def test_navigation_rejects_embedded_credentials(monkeypatch, tmp_path):
    browser = browser_for_commands(monkeypatch, tmp_path)
    with pytest.raises(BrowserInfrastructureError) as error:
        browser.command("navigate", "https://user:secret@example.test/", "--session", "pw-session")
    assert error.value.code == "invalid_url"
    assert not any(call[0] == "goto" for call in browser._page.calls)
    browser.close()


@pytest.mark.parametrize('already_closed', [False, True])
def test_start_and_close_use_explicit_profile_without_real_browser(monkeypatch, tmp_path, already_closed):
    profile = tmp_path / "dedicated-profile"
    folder = tmp_path / "run"
    folder.mkdir()
    events = []

    initial = FakePage()
    popup = FakePage()

    class FakeContext:
        pages = [initial]

        async def close(self):
            events.append("context-close")
            if already_closed:
                raise FakeTargetClosed('last owned page already closed the browser')

    context = FakeContext()

    async def launch(**kwargs):
        events.append(("launch", kwargs))
        return context

    class FakeManager:
        async def __aenter__(self):
            events.append("playwright-enter")
            return SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))

        async def __aexit__(self, *args):
            events.append("playwright-exit")

    @contextmanager
    def tracked_lock(value):
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    monkeypatch.setattr(worker, "resolve_profile", lambda value, **kwargs: worker.Path(value).resolve())
    monkeypatch.setattr(worker.PlaywrightBrowser, "_load_api",
                        staticmethod(lambda: (FakeError, FakeTimeout, FakeTargetClosed, FakeManager)))
    monkeypatch.setattr(worker, "profile_lock", tracked_lock)
    browser = worker.PlaywrightBrowser(folder, profile)
    browser.start()
    context.pages.append(popup)
    receipt = json.loads((folder / "browser-session.json").read_text("utf8"))
    assert receipt["browser_backend"] == "playwright"
    assert receipt["profile"] == str(profile.resolve())
    browser.close()
    assert events[-3:] == ["context-close", "playwright-exit", "lock-exit"]
    assert initial.closed and popup.closed
    assert (folder / "browser-session.json").exists()


def test_verified_browser_high_level_methods_remain_inherited():
    for name in ("snapshot", "check_duplicate", "_pinterest_bytes"):
        assert name not in worker.PlaywrightBrowser.__dict__
    for name in ("search", "more", "receive"):
        assert name in worker.PlaywrightBrowser.__dict__


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("_session_listed", ("owned",)),
        ("_stop_owned_session", ()),
        ("_rebuild_session", ()),
        ("_start_session", ()),
        ("_cleanup_failed_start", ()),
    ],
)
def test_browser_skill_session_paths_are_explicitly_disabled(monkeypatch, tmp_path, name, args):
    browser = browser_for_commands(monkeypatch, tmp_path)
    with pytest.raises(BrowserInfrastructureError) as error:
        getattr(browser, name)(*args)
    assert error.value.code == "unsupported_bsk_session_path"
    browser.close()
