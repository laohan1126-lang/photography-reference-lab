"""Regression coverage for first-search timeout recovery and cleanup state."""
import json
import time

import pytest

from ref_lab import browser_recovery as errors
from tools import collect_verified as worker


QUERY = "矢泽妮可 lovelive cos 摄影"
STEP = {"source": "xiaohongshu", "query": QUERY}


def _browser(tmp_path):
    browser = worker.Browser(tmp_path)
    browser.bsk = "bsk"
    browser.browser_id = "original"
    browser.session = "old"
    browser.deadline = time.monotonic() + 120
    return browser


def _search_page(query=QUERY, *, challenge=False, cards=1):
    return {
        "url": "https://www.xiaohongshu.com/search_result?keyword=" + query,
        "search": query,
        "visibleMain": "",
        "body_ready": True,
        "cards": [{"page": "https://www.xiaohongshu.com/explore/" + "a" * 24}]
        if cards else [],
        "login_required": False,
        "challenge": challenge,
    }


def _value(value):
    return json.dumps({"ok": True, "value": value})


@pytest.mark.parametrize(
    "action,message,code",
    [
        ("evaluate", "Browser read Page.getFrameTree timed out after 10000ms: renderer is not answering",
         "renderer_not_answering"),
        ("session", "Background execution cleanup timed out", "cleanup_timeout"),
    ],
)
def test_browser_control_timeouts_keep_their_actual_cause(action, message, code):
    error = errors.classify_bsk_error(
        action, 1, json.dumps({"code": "timeout", "message": message}), ""
    )
    assert error.code == code
    assert error.is_timeout is True


def test_readable_page_after_navigation_timeout_is_recovered_without_retry(tmp_path, monkeypatch):
    browser = _browser(tmp_path)
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        if args[0] == "navigate":
            raise errors.BrowserInfrastructureError(
                "BrowserSkill command timed out", action="navigate",
                code="command_timeout", is_timeout=True,
            )
        if args[0] == "evaluate":
            return _value(_search_page())
        raise AssertionError(args)

    monkeypatch.setattr(browser, "command", command)
    monkeypatch.setattr(browser, "_apply_sort", lambda _: {"sort_state": "default"})

    snapshot = browser.search(STEP)

    assert snapshot["cards"]
    assert sum(args[0] == "navigate" for args in calls) == 1
    assert not any(args[:2] == ("session", "stop") for args in calls)
    assert browser.session == "old"
    assert browser.recovery_attempts == 0
    receipt = json.loads((tmp_path / "browser-errors.json").read_text("utf8"))
    assert receipt[-1]["action"] == "browser_recovery"
    assert receipt[-1]["result"] == "recovered"


def test_challenge_after_navigation_timeout_is_not_retried_or_bypassed(tmp_path, monkeypatch):
    browser = _browser(tmp_path)
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        if args[0] == "navigate":
            raise errors.BrowserInfrastructureError(
                "BrowserSkill command timed out", action="navigate",
                code="command_timeout", is_timeout=True,
            )
        if args[0] == "evaluate":
            return _value(_search_page(challenge=True, cards=0))
        raise AssertionError(args)

    monkeypatch.setattr(browser, "command", command)

    snapshot = browser.search(STEP)

    assert snapshot["challenge"] is True
    assert sum(args[0] == "navigate" for args in calls) == 1
    assert browser.session == "old"
    assert not (tmp_path / "browser-errors.json").exists()


def test_renderer_timeout_never_rebuilds_the_session(tmp_path, monkeypatch):
    browser = _browser(tmp_path)

    def command(*args, **kwargs):
        raise errors.BrowserInfrastructureError(
            "Browser read Page.getFrameTree timed out: renderer is not answering",
            action="evaluate", code="renderer_not_answering", is_timeout=True,
        )

    monkeypatch.setattr(browser, "command", command)
    monkeypatch.setattr(
        browser, "_rebuild_session",
        lambda: pytest.fail("a renderer timeout must not create another session"),
    )

    assert browser.recover(STEP) is False
    assert browser.session == "old"


def test_wrong_page_gets_one_same_session_recheck_and_is_not_reported_recovered(tmp_path, monkeypatch):
    browser = _browser(tmp_path)
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        if args[0] == "evaluate":
            return _value(_search_page("wrong query"))
        if args[0] == "navigate":
            return "{}"
        raise AssertionError(args)

    monkeypatch.setattr(browser, "command", command)
    monkeypatch.setattr(
        browser, "_rebuild_session",
        lambda: pytest.fail("a readable wrong page does not justify a new session"),
    )

    assert browser.recover(STEP) is False
    assert sum(args[0] == "navigate" for args in calls) == 1
    assert browser.session == "old"
    assert browser.return_failed is not False


def test_stop_timeout_with_live_session_blocks_rebuild_and_keeps_identity(tmp_path, monkeypatch):
    browser = _browser(tmp_path)
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("browsers", "--json"):
            return json.dumps([{"instance_id": "original"}])
        if args[:2] == ("session", "stop"):
            raise errors.BrowserInfrastructureError(
                "Background execution cleanup timed out", action="session",
                code="cleanup_timeout", is_timeout=True,
            )
        if args[:2] == ("session", "list"):
            return json.dumps([{"session_id": "old"}])
        raise AssertionError(args)

    monkeypatch.setattr(browser, "command", command)
    monkeypatch.setattr(browser, "_start_session", lambda **kwargs: pytest.fail("must not start"))

    assert browser._rebuild_session() is False
    assert browser.session == "old"
    assert not any(args[:2] == ("session", "start") for args in calls)
    receipt = json.loads((tmp_path / "browser-session.json").read_text("utf8"))
    assert receipt["state"] == "cleanup_pending"
    assert receipt["session_id"] == "old"


def test_stop_timeout_allows_rebuild_only_after_session_list_proves_it_is_gone(tmp_path, monkeypatch):
    browser = _browser(tmp_path)
    calls = []

    def command(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("browsers", "--json"):
            return json.dumps([{"instance_id": "original"}])
        if args[:2] == ("session", "stop"):
            raise errors.BrowserInfrastructureError(
                "Background execution cleanup timed out", action="session",
                code="cleanup_timeout", is_timeout=True,
            )
        if args[:2] == ("session", "list"):
            return "[]"
        if args[:2] == ("session", "start"):
            return json.dumps({"session_id": "new"})
        if args[0] == "evaluate":
            return _value({"url": "about:blank", "cards": []})
        if args[:2] == ("session", "request"):
            return "{}"
        raise AssertionError(args)

    monkeypatch.setattr(browser, "command", command)

    assert browser._rebuild_session() is True
    assert browser.session == "new"
    assert any(args[:2] == ("session", "list") for args in calls)


def test_unavailable_session_list_never_proves_cleanup_or_starts_another_session(tmp_path, monkeypatch):
    browser = _browser(tmp_path)

    def command(*args, **kwargs):
        if args[:2] == ("browsers", "--json"):
            return json.dumps([{"instance_id": "original"}])
        if args[:2] == ("session", "stop"):
            raise errors.BrowserInfrastructureError(
                "Background execution cleanup timed out", action="session",
                code="cleanup_timeout", is_timeout=True,
            )
        if args[:2] == ("session", "list"):
            raise worker.AgentCallFailed("time_budget_exhausted", fatal=True)
        raise AssertionError(args)

    monkeypatch.setattr(browser, "command", command)
    monkeypatch.setattr(browser, "_start_session", lambda **kwargs: pytest.fail("must not start"))

    assert browser._rebuild_session() is False
    assert browser.session == "old"
    receipt = json.loads((tmp_path / "browser-session.json").read_text("utf8"))
    assert receipt["state"] == "cleanup_pending"
    assert receipt["session_id"] == "old"


def test_final_cleanup_timeout_keeps_owned_session_pending(tmp_path, monkeypatch):
    browser = _browser(tmp_path)

    def command(*args, **kwargs):
        raise errors.BrowserInfrastructureError(
            "Background execution cleanup timed out", action="session",
            code="cleanup_timeout", is_timeout=True,
        )

    monkeypatch.setattr(browser, "command", command)

    with pytest.raises(errors.BrowserInfrastructureError):
        browser.close()
    receipt = json.loads((tmp_path / "browser-session.json").read_text("utf8"))
    assert receipt["state"] == "cleanup_pending"
    assert receipt["session_id"] == "old"
