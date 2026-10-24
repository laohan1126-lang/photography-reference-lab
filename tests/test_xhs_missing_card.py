"""A card that left the live grid must not silently lose its note.

The first formal Job counted eighteen XHS cards as detail attempts whose
cover anchors were no longer in the live DOM: both selectors missed and the
post was dropped without a picture.  The repair opens the URL the search page
itself exposed, exactly once, inside the same already-counted attempt.  It
never guesses a token, never composes a URL, and never walks past a login
wall, a challenge or a 404.

The BrowserSkill double below keeps a real page state, so a navigation that
times out before it moves, times out after it moved, or lands on another page
are all distinguishable from a navigation that worked.
"""
from __future__ import annotations

import json
import subprocess
import time
from urllib.parse import quote

import pytest

from ref_lab.browser_recovery import BrowserInfrastructureError, DetailItemError
from ref_lab.collection_timing import CollectionTiming
from ref_lab.verified_collection import AgentCallFailed
from tools import collect_verified
from tools.collect_verified import SourceBlocked


NOTE = "c" * 24
OTHER_NOTE = "d" * 24
PAGE = f"https://www.xiaohongshu.com/explore/{NOTE}"
OTHER_NOTE_PAGE = f"https://www.xiaohongshu.com/explore/{OTHER_NOTE}"
# What the search page actually exposed, query parameters included.
OBSERVED = PAGE + "?xsec_token=ABC123&xsec_source=pc_search"
QUERY = "西木野真姬 cos 摄影"
OTHER_QUERY = "西木野真姬 cos 场照"
SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword=" + quote(QUERY)
OTHER_SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword=" + quote(OTHER_QUERY)


class FakePage:
    """A BrowserSkill double whose page really changes on navigation."""

    def __init__(self, browser, *, navigate="ok", landing="note", body_ready=True,
                 click_works=False, expire_after=0):
        self.browser = browser
        self.state = "search"          # search | note | other_note | foreign | other_search
        self.navigate = navigate        # ok | timeout_before_leave | timeout_after_leave
        self.landing = landing          # where a navigation ends up
        self.body_ready = body_ready
        self.click_works = click_works
        self.commands: list[tuple] = []
        self.back_calls = 0
        self.probe_reads = 0
        self.expire_after = expire_after

    def _url(self):
        return {
            "search": SEARCH_URL,
            "other_search": OTHER_SEARCH_URL,
            "note": PAGE,
            "other_note": OTHER_NOTE_PAGE,
            "foreign": "https://foreign.example/explore/" + NOTE,
        }[self.state]

    def _snapshot(self):
        if self.state == "search":
            return {"url": SEARCH_URL, "search": QUERY, "visibleMain": "",
                    "cards": [{"page": PAGE}], "login_required": False, "challenge": False,
                    "body_ready": self.body_ready}
        if self.state == "other_search":
            return {"url": OTHER_SEARCH_URL, "search": OTHER_QUERY, "visibleMain": "",
                    "cards": [{"page": OTHER_NOTE_PAGE}], "login_required": False, "challenge": False,
                    "body_ready": self.body_ready}
        return {"url": self._url(), "search": "", "visibleMain": "", "cards": [],
                "login_required": False, "challenge": False, "body_ready": self.body_ready}

    def command(self, *args, **kwargs):
        action = args[0]
        # The real BrowserSkill helper refuses work once the Job deadline is
        # gone, before the command ever runs; the double must do the same.
        if self.browser.deadline - time.monotonic() <= 0:
            raise AgentCallFailed("time_budget_exhausted", fatal=True)
        self.commands.append(args)
        if self.expire_after and len(self.commands) >= self.expire_after:
            self.browser.deadline = time.monotonic() - 1
        if action == "click":
            if not self.click_works:
                raise DetailItemError("selector did not match any element",
                                      code="selector_not_found")
            self.state = "note"
            return json.dumps({"session_id": "owned-session"})
        if action == "navigate":
            if self.navigate == "timeout_before_leave":
                raise BrowserInfrastructureError("BrowserSkill command timed out",
                                                 action="navigate", code="command_timeout",
                                                 is_timeout=True)
            self.state = self.landing
            if self.navigate == "timeout_after_leave":
                raise BrowserInfrastructureError("BrowserSkill command timed out",
                                                 action="navigate", code="command_timeout",
                                                 is_timeout=True)
            return "{}"
        if action == "evaluate":
            script = " ".join(str(item) for item in args)
            if "history.back" in script:
                self.back_calls += 1
                # The SPA returns to the search results page.
                self.state = "search"
                return json.dumps({"ok": True, "value": True})
            if "not_found" in script:
                self.probe_reads += 1
                return json.dumps({"ok": True, "value": {
                    "url": self._url(), "login_required": False, "challenge": False,
                    "not_found": False, "body_ready": self.body_ready}})
            return json.dumps({"ok": True, "value": self._snapshot()})
        return "{}"


def _browser(tmp_path, *, deadline=None, **kwargs):
    browser = collect_verified.Browser(tmp_path)
    browser.bsk, browser.session = "bsk", "owned-session"
    browser.timing = CollectionTiming(tmp_path)
    browser.deadline = deadline if deadline is not None else time.monotonic() + 600
    page = FakePage(browser, **kwargs)
    browser.command = page.command
    return browser, page


def _capture(monkeypatch, rows):
    calls: list[dict] = []

    def capture_note(*args, **kwargs):
        calls.append(kwargs.get("errors") or [])
        return list(rows)

    monkeypatch.setattr(collect_verified, "capture_note", capture_note)
    return calls


def _stages(path):
    return [json.loads(line)["stage"] for line in path.read_text("utf8").splitlines() if line.strip()]


def _navigations(page):
    return [args for args in page.commands if args[0] == "navigate"]


def test_normal_click_path_does_not_navigate(tmp_path, monkeypatch):
    """The ordinary path keeps working and never opens a second page."""
    browser, page = _browser(tmp_path, click_works=True)
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == [{"asset_sha": "a" * 64}]
    assert captured, "the ordinary click path must still capture the note"
    assert not _navigations(page), "the click path must not navigate"
    assert {args[0] for args in page.commands} == {"click", "evaluate"}
    assert {"detail_click", "detail_dom_wait", "detail_return"} <= set(_stages(tmp_path / "timings.jsonl"))


def test_missing_card_falls_back_to_the_observed_url_once(tmp_path, monkeypatch):
    """Both cover selectors missed: open the observed URL exactly once."""
    browser, page = _browser(tmp_path)
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == [{"asset_sha": "a" * 64}]
    assert captured, "the fallback must still capture the note"
    navigations = _navigations(page)
    assert len(navigations) == 1, "the fallback may open the page only once"
    # The opened URL is the observed one, verbatim: no token is added or removed.
    assert navigations[0][1] == OBSERVED
    assert "--session" in navigations[0] and "owned-session" in navigations[0]
    assert len([args for args in page.commands if args[0] == "click"]) == 2
    assert "detail_navigate" in _stages(tmp_path / "timings.jsonl")


@pytest.mark.parametrize("url", [
    "http://www.xiaohongshu.com/explore/" + NOTE,
    "https://evil.example/explore/" + NOTE,
    "https://user:secret@www.xiaohongshu.com/explore/" + NOTE,
    "https://www.xiaohongshu.com/explore/" + NOTE + "/extra",
    "https://www.xiaohongshu.com/profile/other",
])
def test_unauthorised_urls_are_never_opened(tmp_path, monkeypatch, url):
    """Only an observed HTTPS note URL of this note may be opened."""
    browser, page = _browser(tmp_path)
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": url}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == []
    assert not captured, "a refused URL must not capture anything"
    assert not _navigations(page), "a refused URL must not be opened"


def test_a_different_note_is_never_captured(tmp_path, monkeypatch):
    """The fallback landed on another note: it must not be captured."""
    browser, page = _browser(tmp_path, landing="other_note")
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == []
    assert not captured, "a different note must not be captured"
    assert len(_navigations(page)) == 1


def test_a_foreign_page_is_never_captured(tmp_path, monkeypatch):
    """A landing on another host is not a source page and proves nothing."""
    browser, page = _browser(tmp_path, landing="foreign")
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == []
    assert not captured, "a foreign page must not be captured"
    assert page.back_calls == 1, "the browser must return to the search page"


@pytest.mark.parametrize("probe,expected", [
    ({"url": PAGE, "login_required": True, "challenge": False, "not_found": False},
     SourceBlocked),
    ({"url": PAGE, "login_required": False, "challenge": True, "not_found": False},
     SourceBlocked),
])
def test_login_and_challenge_are_not_retried(tmp_path, monkeypatch, probe, expected):
    """A login wall or a challenge stops the card; it is never tried again."""
    browser, page = _browser(tmp_path)
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])
    browser._probe_detail = lambda: dict(probe, body_ready=True)

    with pytest.raises(expected):
        browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert not captured
    assert len(_navigations(page)) == 1


def test_a_missing_note_is_not_retried_and_the_search_page_is_restored(tmp_path, monkeypatch):
    browser, page = _browser(tmp_path)
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])
    browser._probe_detail = lambda: {"url": PAGE + "-404", "login_required": False,
                                     "challenge": False, "not_found": True, "body_ready": True}

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == []
    assert not captured, "a 404 note must not be captured"
    assert len(_navigations(page)) == 1, "no second attempt"
    assert "detail_return" in _stages(tmp_path / "timings.jsonl")
    checks = json.loads((tmp_path / "return-checks.json").read_text("utf8"))
    assert checks[-1]["confirmed"] is True


def test_the_fallback_returns_to_the_same_source_query_and_session(tmp_path, monkeypatch):
    browser, _ = _browser(tmp_path)
    _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    checks = json.loads((tmp_path / "return-checks.json").read_text("utf8"))
    evidence = checks[-1]
    assert evidence["confirmed"] is True
    assert evidence["source"] == "xiaohongshu"
    assert evidence["query"] == QUERY
    assert evidence["session_id"] == "owned-session"
    assert evidence["path"] == "/search_result"
    assert evidence["cards"] >= 1


def test_a_navigation_that_never_moved_does_not_step_back(tmp_path, monkeypatch):
    """A timeout before the page moved: keep the failure, do not go back."""
    browser, page = _browser(tmp_path, navigate="timeout_before_leave")
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == []
    assert not captured, "nothing may be captured from the search page"
    assert page.back_calls == 0, "the browser never left the search page"
    assert page.state == "search"
    assert len(_navigations(page)) == 1


def test_a_navigation_that_timed_out_after_landing_still_captures(tmp_path, monkeypatch):
    """A timeout after the note opened: the live page decides, and it is the note."""
    browser, page = _browser(tmp_path, navigate="timeout_after_leave")
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == [{"asset_sha": "a" * 64}]
    assert captured, "the note really opened, so it may be captured"
    assert page.back_calls == 1


def test_a_navigation_that_landed_on_another_query_returns_correctly(tmp_path, monkeypatch):
    browser, page = _browser(tmp_path, landing="other_search")
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    rows = browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert rows == []
    assert not captured
    assert page.back_calls == 1, "another search page must be stepped back from"


def test_a_page_that_never_built_is_not_captured(tmp_path, monkeypatch):
    """Three unreadable bodies are not a verified page."""
    browser, page = _browser(tmp_path, body_ready=False)
    captured = _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    with pytest.raises(DetailItemError):
        browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert not captured, "an unreadable page must not be captured"
    assert page.probe_reads <= 3, "the probe is bounded"


def test_the_probe_wait_stays_inside_the_deadline(tmp_path, monkeypatch):
    """The bounded re-read never waits longer than the Job has left."""
    browser, page = _browser(tmp_path, body_ready=False)
    sleeps: list[float] = []
    monkeypatch.setattr(collect_verified.time, "sleep", lambda seconds: sleeps.append(seconds))
    browser.deadline = time.monotonic() + 0.2

    with pytest.raises(DetailItemError):
        browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert sleeps, "the probe waits between the bounded reads"
    assert all(seconds <= 0.2 + 1e-6 for seconds in sleeps), sleeps
    assert all(seconds <= 0.6 for seconds in sleeps), sleeps


def test_the_fallback_never_extends_the_deadline(tmp_path, monkeypatch):
    """The existing Job deadline governs the fallback; it is not extended."""
    # The deadline expires right after the two cover selectors were tried.
    browser, page = _browser(tmp_path, expire_after=2)
    _capture(monkeypatch, [{"asset_sha": "a" * 64}])

    with pytest.raises(AgentCallFailed):
        browser.receive({"page": OBSERVED}, {"source": "xiaohongshu", "query": QUERY})

    assert not _navigations(page)
    assert browser.deadline < time.monotonic()


def test_the_fallback_does_not_consume_an_extra_detail_attempt(tmp_path, monkeypatch):
    """One card stays one detail attempt and one per-post attempt."""
    from ref_lab.collection_history import ImageHistory
    from test_verified_collection import FakeAgent, FakeBrowser, job, row

    browser, page = _browser(tmp_path)
    _capture(monkeypatch, [row(tmp_path)])

    class Browser(FakeBrowser):
        searches = 0

        def search(self, step):
            browser.active_query = step["query"]
            Browser.searches += 1
            snapshot = super().search(step)
            # One card in the whole run: one card, one detail attempt.
            snapshot["cards"] = [{"page": OBSERVED}] if Browser.searches == 1 else []
            return snapshot

        def receive(self, card, step):
            return browser.receive(card, step)

    manifest, _ = collect_verified.collect({**job(), "target_count": 1,
                                            "preferred_sources": ["xiaohongshu"]},
                                           FakeAgent(), Browser([]), tmp_path,
                                           history=ImageHistory([]))

    counts = json.loads((tmp_path / "counts.json").read_text("utf8"))
    assert counts["detail_pages"] == 1, "the fallback must not spend another detail attempt"
    schedule = json.loads((tmp_path / "collector-state.json").read_text("utf8"))["detail_schedule"]
    assert len(schedule) == 1 and schedule[0]["attempt"] == 1
    assert len(_navigations(page)) == 1
    assert manifest is not None


@pytest.mark.parametrize('navigate', ['ok', 'timeout_before_leave'])
def test_failed_probe_restores_only_a_page_that_left_search(tmp_path, monkeypatch, navigate):
    browser, page = _browser(tmp_path, navigate=navigate)
    captured = _capture(monkeypatch, [])
    def failed():
        raise DetailItemError('Detail page read failed', code='detail_read_failed')
    monkeypatch.setattr(browser, '_probe_detail', failed)
    with pytest.raises(DetailItemError):
        browser.receive({'page': OBSERVED}, {'source': 'xiaohongshu', 'query': QUERY})
    assert not captured
    assert page.state == 'search' and not browser.return_failed
    assert page.back_calls == (1 if navigate == 'ok' else 0)


def test_return_wait_cannot_spend_more_than_remaining_job_time(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(collect_verified.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(collect_verified.time, 'sleep', lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    browser, page = _browser(tmp_path, deadline=1100.0)
    _capture(monkeypatch, [])
    command = page.command
    def near_deadline(*args, **kwargs):
        value = command(*args, **kwargs)
        if args[0] == 'evaluate' and 'history.back' in str(args[-1]):
            clock[0] = browser.deadline - 0.1
            page.state = 'other_search'
        return value
    browser.command = near_deadline
    with pytest.raises(AgentCallFailed):
        browser.receive({'page': OBSERVED}, {'source': 'xiaohongshu', 'query': QUERY})
    assert clock[0] <= browser.deadline


def test_observed_link_must_keep_note_identity_in_path():
    setup = r'''
const p=JSON.parse(require('fs').readFileSync(0,'utf8'));
const link=href=>({href,getAttribute:()=>href});
const card={innerText:'original card',querySelector:s=>s==='img'?{}:link(p.primary),
            querySelectorAll:()=>p.links.map(link)};
global.document={body:{innerText:'search'},querySelectorAll:s=>s==='section'?[card]:[],
                 querySelector:()=>({value:'query'})};
global.location={hostname:'www.xiaohongshu.com',href:'https://www.xiaohongshu.com/search_result'};
process.stdout.write(JSON.stringify(eval(p.script)));
'''
    payload = {'script': collect_verified.SEARCH_JS, 'primary': PAGE,
               'links': [OTHER_NOTE_PAGE + '?related=' + NOTE,
                         'https://foreign.example/explore/' + NOTE + '?from=search', OBSERVED]}
    result = subprocess.run(['node', '-e', setup], input=json.dumps(payload),
                            text=True, encoding='utf8', capture_output=True, timeout=15, check=True)
    assert json.loads(result.stdout)['cards'][0]['page'] == OBSERVED
