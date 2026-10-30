import json
import subprocess
from types import SimpleNamespace

import pytest

from ref_lab.bsk_command import run_bsk


def reply(value, code=0):
    return SimpleNamespace(returncode=code, stdout=json.dumps(value), stderr="")


def test_each_action_consumes_a_fresh_context_and_keeps_tab(monkeypatch):
    calls = []
    def run(argv, **kw):
        calls.append((argv, kw))
        if argv[1:3] == ["cooperate", "sync"]:
            return reply({"context_id": f"context-{len(calls)}", "ready": True})
        return reply({"ok": True, "value": 2})
    monkeypatch.setattr(subprocess, "run", run)
    for _ in range(2):
        run_bsk(["bsk", "evaluate", "--session", "owned", "--tab-id", "42", "--json", "1+1"], timeout=10)
    assert [c[0][1] for c in calls] == ["cooperate", "evaluate", "cooperate", "evaluate"]
    assert calls[1][0][-2:] == ["--context", "context-1"]
    assert calls[3][0][-2:] == ["--context", "context-3"]
    assert calls[0][0][-2:] == ["--tab-id", "42"]


@pytest.mark.parametrize("sync", [
    {"ready": False, "context_id": "held", "state": {"mode": "human"}},
    {"ready": True},
    {"code": "user_aborted", "message": "Stopped by user"},
])
def test_no_action_without_live_authority(monkeypatch, sync):
    calls = []
    def run(argv, **kw):
        calls.append(argv)
        return reply(sync, 1 if "code" in sync else 0)
    monkeypatch.setattr(subprocess, "run", run)
    result = run_bsk(["bsk", "click", "--session", "owned", "@e1"], timeout=10)
    assert result.returncode != 0
    assert len(calls) == 1


def test_sync_and_action_share_one_deadline(monkeypatch):
    from ref_lab import bsk_command
    clock = [0.0]
    calls = []
    monkeypatch.setattr(bsk_command.time, "monotonic", lambda: clock[0])
    def run(argv, **kw):
        calls.append(kw["timeout"])
        clock[0] += 7
        return reply({"context_id": "fresh", "ready": True})
    monkeypatch.setattr(subprocess, "run", run)
    run_bsk(["bsk", "evaluate", "--session", "owned", "1+1"], timeout=10)
    assert calls == [10, 3]


def test_unknown_action_outcome_is_never_replayed(monkeypatch):
    calls = []
    def run(argv, **kw):
        calls.append(argv)
        if argv[1] == "cooperate":
            return reply({"context_id": "fresh", "ready": True})
        raise subprocess.TimeoutExpired(argv, kw["timeout"])
    monkeypatch.setattr(subprocess, "run", run)
    result = run_bsk(["bsk", "click", "--session", "owned", "@e1"], timeout=10)
    assert json.loads(result.stdout)["code"] == "operation_outcome_unknown"
    assert len(calls) == 2


def test_initial_navigation_and_cleanup_do_not_require_context(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: calls.append(argv) or reply({}))
    run_bsk(["bsk", "navigate", "https://example.test", "--session", "owned"], timeout=10, initial_navigation=True)
    run_bsk(["bsk", "session", "stop", "owned"], timeout=10)
    assert [c[1] for c in calls] == ["navigate", "session"]


def test_collector_stops_after_first_infrastructure_read_failure(tmp_path, monkeypatch):
    from ref_lab.browser_recovery import BrowserInfrastructureError
    from tools.collect_verified import Browser
    browser = Browser(tmp_path)
    calls = []
    def command(*args, **kwargs):
        calls.append(args[0])
        if args[0] == "evaluate":
            raise BrowserInfrastructureError("read stalled", code="renderer_not_answering", is_timeout=True)
        return "{}"
    monkeypatch.setattr(browser, "command", command)
    with pytest.raises(BrowserInfrastructureError):
        browser.search({"source": "xiaohongshu", "query": "test"})
    assert calls == ["navigate", "evaluate"]


def test_cleanup_never_stops_another_agents_session(tmp_path, monkeypatch):
    from ref_lab.browser_recovery import BrowserInfrastructureError
    from tools.collect_verified import Browser
    browser = Browser(tmp_path)
    browser.session = "owned"
    calls = []
    def command(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("session", "stop"):
            raise BrowserInfrastructureError("cleanup stalled", code="cleanup_timeout", is_timeout=True)
        return '[{"session_id":"owned"},{"session_id":"other"}]'
    monkeypatch.setattr(browser, "command", command)
    assert browser._stop_owned_session() is False
    assert calls == [("session", "stop", "owned"), ("session", "list", "--json")]


def test_browser_selection_rejects_mismatch_and_ambiguity():
    from tools.collect_adapter import _pick_browser
    assert _pick_browser([{"instance_id": "old", "browser_name": "edge", "version_skew": True}]) is None
    assert _pick_browser([{"instance_id": "a", "browser_name": "edge"}, {"instance_id": "b", "browser_name": "edge"}]) is None


def test_user_abort_cancels_collection_without_recovery(tmp_path):
    from ref_lab.browser_recovery import classify_bsk_error
    from tools import collect_verified as worker
    from tests.test_browserskill_recovery import SyntheticAgent, _job
    class AbortedBrowser:
        supports_sort = True
        def start(self): pass
        def close(self): pass
        def can_recover(self): pytest.fail("User stop must not enter recovery")
        def search(self, *args, **kwargs):
            raise classify_bsk_error("evaluate", 1, json.dumps({
                "code": "permission_denied", "message": "User stopped this task",
                "data": {"reason": "user_aborted", "effect_state": "unknown"},
            }), "")
    summary, _ = worker.collect(_job(), SyntheticAgent(), AbortedBrowser(), tmp_path, search_only=True)
    assert summary["status"] == "cancelled"
    assert summary["stop_reason"] == "cancelled"
