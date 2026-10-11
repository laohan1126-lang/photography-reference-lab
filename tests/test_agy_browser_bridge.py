"""Synthetic transport tests for tools/agy_browser_bridge.py.

Every bsk call is replaced by a scripted fake that answers in the installed
bsk 0.3.2 schema.  These tests prove argv shapes, policy enforcement, cleanup
discipline and result/evidence structure only.  They are NOT evidence that any
real browser, source, page or pixel was observed, and they never touch the
owner's browser, profile, daemon or data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools import agy_browser_bridge as bridge

BROWSER_ID = "1f5bd99b"
ALLOWED_URL = "https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques"
TAB_ID = 1775091505

# The installed bsk 0.3.2 daemon status and browser row, exactly as reported.
DAEMON_VERSION = "0.3.2"
PROTOCOL_VERSION = "1.3"
BROWSER_ROW = {
    "instance_id": BROWSER_ID,
    "browser_name": "chrome",
    "browser_version": "154.0.0.0",
    "extension_version": DAEMON_VERSION,
    "connected_at_ms": 1791689046975,
    "version_skew": False,
    "extension_protocol_version": PROTOCOL_VERSION,
    "unresponsive": False,
    "session_count": 0,
}
DAEMON_STATUS = {
    "daemon_version": DAEMON_VERSION,
    "protocol_version": PROTOCOL_VERSION,
    "pid": 20332,
    "browsers": [BROWSER_ROW],
    "sessions": [],
    "version_skew_browsers": [],
}

# The installed bsk 0.3.2 shapes for the three capture commands, exactly as the
# live transport smoke reported them: session start binds a window and names the
# browser instance; navigate reports the requested url AND the final_url the tab
# actually reached; observe is the semantic VOM and carries no url at all.
SESSION_START = {
    "agent_window_id": 1775091504,
    "browser_instance_id": BROWSER_ID,
    "interaction": {"borrow_confirmation": "always", "request_help": "enabled"},
    "session_id": "own-session",
}
NAVIGATE_RESULT = {
    "tab_id": TAB_ID,
    "url": ALLOWED_URL,
    "final_url": ALLOWED_URL,
    "reached": "domcontentloaded",
}
OBSERVATION = {
    "text": "synthetic semantic VOM",
    "ref_count": 4,
    "tab_id": TAB_ID,
    "truncated": False,
}


def row(**overrides) -> dict:
    return {**BROWSER_ROW, **overrides}


def _record(bsk_path, args, *, stdout="", exit_code=0, error=None, timed_out=False, stderr=""):
    return {
        "argv": [bsk_path, *args],
        "cwd": "synthetic",
        "started_utc": "2026-10-11T00:00:00.000Z",
        "finished_utc": "2026-10-11T00:00:01.000Z",
        "timeout_s": 30.0,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
    }


def _phase(args: list[str]) -> str:
    """`session list|start|stop` is a two-word command; everything else is one."""
    return " ".join(args[:2]) if args[0] == "session" else args[0]


class FakeBsk:
    """Scripted stand-in for the real BrowserSkill CLI."""

    def __init__(self, **overrides):
        self.calls: list[list[str]] = []
        self.envs: list[dict] = []
        self.overrides = overrides

    def __call__(self, bsk_path, args, timeout, env):
        self.calls.append(list(args))
        self.envs.append(dict(env))
        key = _phase(args)
        table = {
            "status": DAEMON_STATUS,
            "browsers": [BROWSER_ROW],
            "session list": [],
            "session start": SESSION_START,
            "session stop": {"stopped": True},
            "navigate": NAVIGATE_RESULT,
            "observe": OBSERVATION,
            "get-html": "<html>synthetic</html>",
            "wheel": {"delta_y": 800},
            "screenshot": {"saved": True},
        }
        payload = self.overrides.get(key, table.get(key, {}))
        if key == "screenshot" and "screenshot" not in self.overrides:
            out = args[args.index("--out") + 1]
            Path(out).write_bytes(b"synthetic-not-a-real-screenshot")
        if isinstance(payload, dict) and "__raw__" in payload:
            return _record(bsk_path, args, stdout=payload["__raw__"], **payload.get("fields", {}))
        return _record(bsk_path, args, stdout=json.dumps(payload), **self.overrides.get(f"fields:{key}", {}))

    def phases(self) -> list[str]:
        return [_phase(call) for call in self.calls]

    def args_of(self, key):
        return [call for call in self.calls if _phase(call) == key]


@pytest.fixture
def env(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    bsk = tmp_path / "bsk.exe"
    bsk.write_text("synthetic", encoding="utf-8")
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({
        "browser_id": BROWSER_ID,
        "browser_name": "chrome",
        "allowed_urls": [ALLOWED_URL],
        "evidence_root": str(evidence),
        "bsk_path": str(bsk),
    }), encoding="utf-8")
    return {"policy": policy, "evidence": evidence, "bsk": bsk}


def run_preflight(env, monkeypatch, **overrides):
    fake = FakeBsk(**overrides)
    monkeypatch.setattr(bridge, "_execute", fake)
    result = bridge.do_preflight(env["policy"], BROWSER_ID)
    return result, fake


def run_capture(env, monkeypatch, *, out_dir=None, url=ALLOWED_URL, scroll=None, browser=BROWSER_ID, **overrides):
    fake = FakeBsk(**overrides)
    monkeypatch.setattr(bridge, "_execute", fake)
    out = out_dir if out_dir is not None else str(env["evidence"] / "attempt-1")
    result = bridge.do_capture(env["policy"], browser, url, out, scroll)
    return result, fake


# ---------------------------------------------------------------- preflight

def test_preflight_passes_when_daemon_and_pinned_browser_are_usable(env, monkeypatch):
    result, fake = run_preflight(env, monkeypatch)
    assert result["status"] == "ok"
    assert result["checks"] == {
        "daemon_running": True, "versions_agree": True,
        "daemon_version": "0.3.2", "protocol_version": "1.3",
        "browser_name": "chrome", "browser_version": "154.0.0.0",
        "extension_version": "0.3.2", "extension_protocol_version": "1.3",
        "browsers_seen": 1, "sessions_on_browser": 0,
    }
    assert fake.phases() == ["status", "browsers"]
    assert Path(result["artifacts"]["attempt"]).is_file()
    assert Path(result["artifacts"]["events"]).is_file()


def test_preflight_rejects_a_browser_other_than_the_pinned_profile(env, monkeypatch):
    fake = FakeBsk()
    monkeypatch.setattr(bridge, "_execute", fake)
    assert bridge.do_preflight(env["policy"], BROWSER_ID)["status"] == "ok"  # sanity
    fake.calls.clear()

    result = bridge.do_preflight(env["policy"], "0badbeef")
    assert (result["status"], result["reason"]) == ("blocked", "wrong_browser_profile")
    assert fake.calls == []


def test_preflight_rejects_a_profile_whose_name_does_not_match_policy(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [row(browser_name="edge")]})
    assert (result["status"], result["reason"]) == ("blocked", "wrong_browser_profile")


def test_preflight_blocks_when_the_pinned_browser_is_absent(env, monkeypatch):
    result, fake = run_preflight(env, monkeypatch, **{"browsers": [row(instance_id="ffffffff")]})
    assert (result["status"], result["reason"]) == ("blocked", "connected_browser_absent")
    assert fake.phases() == ["status", "browsers"]  # stops there; touches no session


def test_preflight_blocks_when_the_browser_is_not_responsive(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [row(unresponsive=True)]})
    assert (result["status"], result["reason"]) == ("blocked", "browser_not_responsive")


def test_preflight_blocks_on_a_duplicate_row_for_the_pinned_instance(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [row(), row()]})
    assert (result["status"], result["reason"]) == ("blocked", "browser_row_ambiguous")


def test_preflight_blocks_on_an_unrecognized_browsers_payload(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{"browsers": {"browsers": [BROWSER_ROW]}})
    assert (result["status"], result["reason"]) == ("blocked", "browser_probe_unrecognized")


def test_preflight_blocks_on_a_row_missing_an_installed_schema_field(env, monkeypatch):
    partial = {k: v for k, v in BROWSER_ROW.items() if k != "unresponsive"}
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [partial]})
    assert (result["status"], result["reason"]) == ("blocked", "browser_row_unrecognized")
    assert "unresponsive" in result["detail"]


def test_preflight_blocks_when_no_daemon_is_running(env, monkeypatch):
    result, fake = run_preflight(env, monkeypatch, **{"status": {**DAEMON_STATUS, "pid": None}})
    assert (result["status"], result["reason"]) == ("blocked", "daemon_not_running")
    assert fake.phases() == ["status"]  # never probes or starts anything else


def test_preflight_never_starts_a_daemon_or_reports_exit_zero_error_as_success(env, monkeypatch):
    result, fake = run_preflight(
        env, monkeypatch, **{"fields:status": {"exit_code": 0}, "status": {"error": "permission denied"}})
    assert (result["status"], result["reason"]) == ("blocked", "daemon_status_failed")
    assert all("daemon" not in call for call in fake.calls)


def test_preflight_blocks_when_another_session_already_owns_the_browser(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{
        "browsers": [row(session_count=1, session_id="user-window")]})
    assert (result["status"], result["reason"]) == ("blocked", "overlapping_session")
    assert "user-window" not in json.dumps(result)  # reports a count, never a session id


def test_preflight_ignores_sessions_bound_to_other_browsers(env, monkeypatch):
    other = row(instance_id="some-other-instance", session_count=3, session_id="user-window")
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [BROWSER_ROW, other]})
    assert result["status"] == "ok"
    assert result["checks"]["sessions_on_browser"] == 0
    assert result["checks"]["browsers_seen"] == 2


def test_preflight_summary_hides_tabs_and_other_sessions(env, monkeypatch):
    other = row(instance_id="some-other-instance", session_count=2,
                tabs=["https://mail.example/private"], title="Inbox")
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [BROWSER_ROW, other]})
    assert result["status"] == "ok"
    printed = json.dumps(result)
    assert "Inbox" not in printed and "mail.example" not in printed
    assert "user-window" not in printed


def test_preflight_blocks_when_the_extension_version_disagrees_with_the_daemon(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{
        "status": {**DAEMON_STATUS, "daemon_version": "0.3.1"}})
    assert (result["status"], result["reason"]) == ("blocked", "version_mismatch")


def test_preflight_blocks_when_the_extension_protocol_disagrees(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{
        "browsers": [row(extension_protocol_version="1.2")]})
    assert (result["status"], result["reason"]) == ("blocked", "protocol_mismatch")


def test_preflight_blocks_a_status_without_daemon_and_protocol_versions(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{
        "status": {"pid": 20332, "browsers": [BROWSER_ROW], "sessions": [],
                   "version_skew_browsers": []}})
    assert (result["status"], result["reason"]) == ("blocked", "daemon_status_unrecognized")


@pytest.mark.parametrize("browsers,status", [
    ([row(version_skew=True)], DAEMON_STATUS),
    ([BROWSER_ROW], {**DAEMON_STATUS, "version_skew_browsers": [BROWSER_ID]}),
])
def test_preflight_blocks_a_version_skewed_browser_row(env, monkeypatch, browsers, status):
    result, _ = run_preflight(env, monkeypatch, **{"browsers": browsers, "status": status})
    assert (result["status"], result["reason"]) == ("blocked", "version_skew")


def test_preflight_never_compares_chromes_build_to_the_daemon_version(env, monkeypatch):
    result, _ = run_preflight(env, monkeypatch, **{"browsers": [row(browser_version="999.0.0.1")]})
    assert result["status"] == "ok"  # a Chrome build number is not a daemon version
    assert result["checks"]["browser_version"] == "999.0.0.1"


def test_preflight_blocks_when_the_policy_file_is_missing(env, monkeypatch):
    fake = FakeBsk()
    monkeypatch.setattr(bridge, "_execute", fake)
    result = bridge.do_preflight(env["policy"].parent / "absent.json", BROWSER_ID)
    assert (result["status"], result["reason"]) == ("blocked", "policy_missing")
    assert fake.calls == []


# ------------------------------------------------------------------ capture

def test_capture_success_shape(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, scroll=800)
    assert result["status"] == "ok"
    assert result["source_url"] == ALLOWED_URL
    assert result["final_url"] == ALLOWED_URL  # the address actually reached, not the seed
    assert result["tab_id"] == TAB_ID
    assert result["browser"] == {"browser_id": BROWSER_ID}
    assert result["session"]["session_id"] == "own-session"
    assert result["session"]["cleanup_ok"] is True
    assert result["evidence_only"] is True and "not_verified" in result
    for key in ("observation", "html", "screenshot", "attempt", "events",
                "observation_after_scroll"):
        assert key in result["artifacts"], key
        assert Path(result["artifacts"][key]).is_file(), key
    # The screenshot digest is a hash of the recorded bytes, not a path.
    screenshot_bytes = Path(result["artifacts"]["screenshot"]).read_bytes()
    assert result["artifacts"]["screenshot_sha256"] == hashlib.sha256(screenshot_bytes).hexdigest()

    phases = fake.phases()
    assert phases == ["status", "browsers", "session start", "navigate",
                      "observe", "get-html", "wheel", "observe", "screenshot", "session stop"]
    navigate = fake.args_of("navigate")[0]
    assert navigate[1] == ALLOWED_URL
    assert navigate[2:] == ["--session", "own-session", "--wait-until", "domcontentloaded",
                            "--timeout", "45s", "--json"]
    assert fake.args_of("observe")[0] == ["observe", "--session", "own-session",
                                          "--max-tokens", "24000", "--json"]
    assert fake.args_of("wheel")[0][:2] == ["wheel", "--delta-y"] and fake.args_of("wheel")[0][2] == "800"
    assert fake.args_of("session start")[0] == ["session", "start", "--browser", BROWSER_ID,
                                                "--no-focus", "--json"]
    assert fake.args_of("session stop")[0] == ["session", "stop", "own-session", "--json"]


def test_capture_result_omits_raw_html_and_says_it_proves_nothing(env, monkeypatch):
    result, _ = run_capture(env, monkeypatch, **{"get-html": "<html>" + "x" * 5000 + "</html>"})
    assert result["status"] == "ok"
    assert "x" * 100 not in json.dumps(result)
    assert Path(result["artifacts"]["html"]).read_text(encoding="utf-8").startswith("<html>")
    assert "no visual" in result["not_verified"]


def test_capture_without_scroll_never_wheels(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, scroll=None)
    assert result["status"] == "ok" and result["scroll_y"] == 0
    assert not fake.args_of("wheel")


def test_capture_always_sets_auto_start_zero_and_preserves_bsk_home(env, monkeypatch):
    monkeypatch.setenv("BSK_HOME", "/existing/home")
    result, fake = run_capture(env, monkeypatch)
    assert result["status"] == "ok"
    assert fake.envs and all(e["BSK_AUTO_START"] == "0" for e in fake.envs)
    assert all(e["BSK_HOME"] == "/existing/home" for e in fake.envs)


def test_capture_stops_its_own_session_after_a_failed_navigation(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"navigate": {"error": "net::ERR_ABORTED"}})
    assert result["status"] == "failed"
    assert result["reason"] == "navigate_failed"
    assert fake.args_of("session stop") == [["session", "stop", "own-session", "--json"]]
    assert not fake.args_of("observe") and not fake.args_of("screenshot")
    state = json.loads(Path(result["artifacts"]["attempt"]).read_text(encoding="utf-8"))
    assert state["cleanup"]["ok"] is True and state["status"] == "failed"


def test_capture_stops_its_own_session_after_a_failed_observe(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"observe": {"error": "target closed"}})
    assert (result["status"], result["reason"]) == ("failed", "observe_failed")
    assert fake.args_of("session stop")
    assert not fake.args_of("screenshot")


def test_capture_is_failed_when_cleanup_fails_even_if_capture_succeeded(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"session stop": {"error": "still busy"}})
    assert result["status"] == "failed"
    assert result["reason"] == "cleanup_failed"
    assert result["session"]["cleanup_ok"] is False


def test_capture_fails_when_the_screenshot_file_is_missing_despite_exit_zero(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"screenshot": {"saved": True}})
    assert result["status"] == "failed"
    assert result["reason"] == "screenshot_failed"
    assert fake.args_of("session stop")


def test_capture_blocks_before_any_browser_action_when_preflight_fails(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"browsers": []})
    assert (result["status"], result["reason"]) == ("blocked", "connected_browser_absent")
    assert not fake.args_of("session start")
    assert Path(result["artifacts"]["events"]).is_file()  # partial evidence preserved


def test_capture_never_touches_another_session(env, monkeypatch):
    other = row(instance_id="another-instance", session_count=2, session_id="user-window")
    result, fake = run_capture(env, monkeypatch, **{"browsers": [BROWSER_ROW, other]})
    assert result["status"] == "ok"
    stopped = [call[2] for call in fake.args_of("session stop")]
    assert stopped == ["own-session"]


# ------------------------------------------------------- policy enforcement

def test_capture_rejects_a_url_outside_the_exact_allowlist(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, url="https://www.nikonusa.com/other-page")
    assert (result["status"], result["reason"]) == ("blocked", "url_not_allowlisted")
    assert fake.calls == []


def test_capture_rejects_non_https_and_userinfo_urls(env, monkeypatch):
    fake = FakeBsk()
    monkeypatch.setattr(bridge, "_execute", fake)
    assert bridge.do_capture(env["policy"], BROWSER_ID, "http://www.nikonusa.com/x",
                             str(env["evidence"] / "a"), None)["reason"] == "url_not_https"
    assert bridge.do_capture(env["policy"], BROWSER_ID, "https://user:pw@www.nikonusa.com/x",
                             str(env["evidence"] / "b"), None)["reason"] == "url_userinfo"
    assert fake.calls == []


def test_policy_rejects_wildcard_allowed_urls(env):
    policy = json.loads(env["policy"].read_text(encoding="utf-8"))
    policy["allowed_urls"] = ["https://*.nikonusa.com/*"]
    env["policy"].write_text(json.dumps(policy), encoding="utf-8")
    result = bridge.do_capture(env["policy"], BROWSER_ID, ALLOWED_URL, str(env["evidence"] / "x"), None)
    assert (result["status"], result["reason"]) == ("blocked", "policy_invalid")


def test_capture_rejects_a_relative_out_dir(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, out_dir="attempt-1")
    assert (result["status"], result["reason"]) == ("blocked", "out_dir_not_absolute")
    assert fake.calls == []


def test_capture_rejects_traversal_outside_the_evidence_root(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch,
                               out_dir=str(env["evidence"] / ".." / "escape-1"))
    assert (result["status"], result["reason"]) == ("blocked", "out_dir_outside_evidence_root")
    assert fake.calls == []


def test_capture_rejects_a_symlinked_out_dir_escaping_the_evidence_root(tmp_path, env, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = env["evidence"] / "link-out"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available in this environment")
    result, fake = run_capture(env, monkeypatch, out_dir=str(link))
    assert result["status"] == "blocked"
    assert result["reason"] in {"out_dir_symlink", "out_dir_outside_evidence_root"}
    assert fake.calls == []


def test_capture_rejects_a_symlinked_out_dir_even_when_it_stays_inside_the_root(env, monkeypatch):
    real = env["evidence"] / "real-1"
    real.mkdir()
    link = env["evidence"] / "link-in"
    try:
        link.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available in this environment")
    result, fake = run_capture(env, monkeypatch, out_dir=str(link))
    assert (result["status"], result["reason"]) == ("blocked", "out_dir_symlink")
    assert fake.calls == []


def test_capture_refuses_to_overwrite_an_existing_attempt_directory(env, monkeypatch):
    existing = env["evidence"] / "attempt-1"
    existing.mkdir()
    (existing / "attempt.json").write_text("{}", encoding="utf-8")
    result, fake = run_capture(env, monkeypatch)
    assert (result["status"], result["reason"]) == ("blocked", "out_dir_exists")
    assert json.loads((existing / "attempt.json").read_text(encoding="utf-8")) == {}
    assert fake.calls == []


@pytest.mark.parametrize("scroll", [-1, 5001, 999999])
def test_capture_rejects_out_of_range_scroll(env, monkeypatch, scroll):
    result, fake = run_capture(env, monkeypatch, scroll=scroll)
    assert (result["status"], result["reason"]) == ("blocked", "scroll_invalid")
    assert fake.calls == []


def test_capture_rejects_a_non_integer_scroll_from_the_cli(env, monkeypatch):
    monkeypatch.setattr(bridge, "DEFAULT_POLICY", env["policy"])
    with pytest.raises(SystemExit):
        bridge.main(["capture", "--browser-id", BROWSER_ID, "--url", ALLOWED_URL,
                     "--out-dir", str(env["evidence"] / "x"), "--scroll-y", "800.5"])


def test_capture_rejects_a_browser_id_the_policy_does_not_pin(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, browser="0badbeef")
    assert (result["status"], result["reason"]) == ("blocked", "wrong_browser_profile")
    assert fake.calls == []


def test_capture_does_not_edit_the_policy_file(env, monkeypatch):
    before = env["policy"].read_bytes()
    result, _ = run_capture(env, monkeypatch)
    assert result["status"] == "ok"
    assert env["policy"].read_bytes() == before


def test_capture_writes_private_structured_evidence_files(env, monkeypatch):
    result, _ = run_capture(env, monkeypatch, scroll=800)
    directory = Path(result["attempt_dir"])
    state = json.loads((directory / "attempt.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert state["facts"]["url"] == ALLOWED_URL
    assert state["session_id"] == "own-session"
    assert all(step["argv"][0] == str(env["bsk"]) for step in state["steps"])
    assert {"command", "session_started", "cleanup", "finished"} <= {e["event"] for e in events}
    assert (directory / "commands" / "navigate.stdout.txt").is_file()
    assert (directory / "commands" / "session_stop.stderr.txt").is_file()


def test_a_timeout_is_reported_as_a_timeout_and_keeps_partial_output(env, monkeypatch):
    result, _ = run_capture(env, monkeypatch, **{
        "navigate": {"__raw__": "partial navigation output",
                     "fields": {"timed_out": True, "error": "timeout after 120.0s", "exit_code": None}}})
    assert result["status"] == "failed"
    assert result["detail"] == "timeout after 120.0s"
    attempt = Path(result["attempt_dir"]) / "commands" / "navigate.stdout.txt"
    assert attempt.read_text(encoding="utf-8") == "partial navigation output"


def test_cli_exit_codes_distinguish_ok_blocked_and_failed(env, monkeypatch, capsys):
    monkeypatch.setattr(bridge, "DEFAULT_POLICY", env["policy"])
    monkeypatch.setattr(bridge, "_execute", FakeBsk())
    assert bridge.main(["preflight", "--browser-id", BROWSER_ID]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"

    monkeypatch.setattr(bridge, "_execute", FakeBsk(**{"browsers": [row(instance_id="ffffffff")]}))
    assert bridge.main(["preflight", "--browser-id", BROWSER_ID]) == 2
    capsys.readouterr()

    monkeypatch.setattr(bridge, "_execute", FakeBsk(**{"observe": {"error": "boom"}}))
    assert bridge.main(["capture", "--browser-id", BROWSER_ID, "--url", ALLOWED_URL,
                        "--out-dir", str(env["evidence"] / "cli-attempt")]) == 3


# --------------------------------------------------------- fixed policy grant

def test_production_cli_rejects_an_arbitrary_policy_and_never_runs_an_injected_bsk(
        env, monkeypatch, tmp_path, capsys):
    """A grant to run this script must not become a grant to run any binary.

    An agent could author a policy naming its own bsk_path, but the public CLI
    has no --policy option, so the argument is refused before anything runs.
    """
    fake_bsk = tmp_path / "injected.exe"
    fake_bsk.write_text("synthetic", encoding="utf-8")
    injected = tmp_path / "agent-authored-policy.json"
    injected.write_text(json.dumps({
        "browser_id": BROWSER_ID,
        "browser_name": "chrome",
        "allowed_urls": [ALLOWED_URL],
        "evidence_root": str(tmp_path / "elsewhere"),
        "bsk_path": str(fake_bsk),
    }), encoding="utf-8")

    fake = FakeBsk()
    monkeypatch.setattr(bridge, "_execute", fake)
    monkeypatch.setattr(bridge, "DEFAULT_POLICY", env["policy"])  # the trusted checkout's policy

    for argv in (["preflight", "--browser-id", BROWSER_ID, "--policy", str(injected)],
                 ["--policy", str(injected), "preflight", "--browser-id", BROWSER_ID],
                 ["capture", "--browser-id", BROWSER_ID, "--url", ALLOWED_URL,
                  "--out-dir", str(tmp_path / "out"), "--policy", str(injected)]):
        # The wording differs by placement (an unrecognised leading option is
        # rejected as an invalid command); what matters is that argparse exits
        # with the usage error and the fixed-policy run never starts.
        with pytest.raises(SystemExit) as exit_info:
            bridge.main(argv)
        assert exit_info.value.code == 2
        assert capsys.readouterr().err.strip()

    assert fake.calls == []  # _execute is the only spawn point; it never ran


def test_cli_uses_only_the_default_policy(env, monkeypatch):
    monkeypatch.setattr(bridge, "DEFAULT_POLICY", env["policy"])
    seen = {}

    def spy(policy_path, browser_id):
        seen.update(policy=Path(policy_path), browser_id=browser_id)
        return {"status": "ok"}

    monkeypatch.setattr(bridge, "do_preflight", spy)
    assert bridge.main(["preflight", "--browser-id", BROWSER_ID]) == 0
    assert seen == {"policy": env["policy"], "browser_id": BROWSER_ID}


def test_default_policy_path_is_the_project_private_file():
    default = Path(bridge.DEFAULT_POLICY)
    assert default.name == "agy-browser-policy.json"
    assert default.parent.name == ".local"
    assert default.parent.parent == Path(bridge.__file__).resolve().parent.parent


# --------------------------------------- regression: unexpected errors fail
# (independent verifier reproductions, integrated here)

def test_unexpected_evidence_write_error_is_failed_not_ok(env, monkeypatch):
    """An OSError while recording evidence must never become a soft success."""
    fake = FakeBsk()
    monkeypatch.setattr(bridge, "_execute", fake)
    original = bridge.Attempt.artifact

    def fail_observation(self, name, path, sha=False):
        if name == "observation":
            raise OSError("simulated disk full while recording observation")
        return original(self, name, path, sha)

    monkeypatch.setattr(bridge.Attempt, "artifact", fail_observation)
    result = bridge.do_capture(env["policy"], BROWSER_ID, ALLOWED_URL,
                               str(env["evidence"] / "write-error"), None)
    assert result["status"] == "failed", result
    assert result["reason"] == "capture_exception"
    assert "simulated disk full" in result["detail"]
    assert fake.args_of("session stop") == [["session", "stop", "own-session", "--json"]]
    state = json.loads(Path(result["artifacts"]["attempt"]).read_text(encoding="utf-8"))
    assert state["status"] == "failed"
    assert state["failures"][0] == {"code": "capture_exception",
                                    "detail": result["detail"]}


def test_cli_exit_code_is_failure_when_capture_raises_unexpectedly(env, monkeypatch, capsys):
    """The same unexpected error must not exit zero at the command line."""
    monkeypatch.setattr(bridge, "DEFAULT_POLICY", env["policy"])
    monkeypatch.setattr(bridge, "_execute", FakeBsk())

    def fail_html(self, name, path, sha=False):
        if name == "html":
            raise OSError("simulated write failure")
        return original(self, name, path, sha)

    original = bridge.Attempt.artifact
    monkeypatch.setattr(bridge.Attempt, "artifact", fail_html)
    assert bridge.main(["capture", "--browser-id", BROWSER_ID, "--url", ALLOWED_URL,
                        "--out-dir", str(env["evidence"] / "cli-raise")]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_capture_fails_when_a_required_artifact_is_never_recorded(env, monkeypatch):
    """Success requires the evidence to actually be on disk, not merely claimed."""
    original = bridge.Attempt.artifact

    def drop_screenshot(self, name, path, sha=False):
        if name == "screenshot":
            self.note("artifact", name=name, path=str(path))  # file exists, unrecorded
            return path
        return original(self, name, path, sha)

    monkeypatch.setattr(bridge.Attempt, "artifact", drop_screenshot)
    result, _ = run_capture(env, monkeypatch)
    assert result["status"] == "failed"
    assert result["reason"] == "artifacts_incomplete"
    assert "screenshot" in result["detail"] and "screenshot_sha256" in result["detail"]


# ------------------------------------- regression: real destination enforcement
# (independent verifier reproductions, integrated here)

def test_capture_stops_when_navigation_lands_outside_the_policy(env, monkeypatch):
    """The requested seed URL is never proof of where the tab actually landed."""
    redirected = "https://unapproved.example/private"
    result, fake = run_capture(env, monkeypatch, **{
        "navigate": {**NAVIGATE_RESULT, "final_url": redirected},
        "observe": {**OBSERVATION, "url": redirected, "text": "out-of-scope page"},
    })
    assert result["status"] == "failed", result
    assert result["reason"] == "destination_not_allowlisted"
    assert redirected in result["detail"]
    assert not fake.args_of("observe"), fake.calls
    assert not fake.args_of("get-html"), fake.calls
    assert not fake.args_of("screenshot"), fake.calls
    assert fake.args_of("session stop") == [["session", "stop", "own-session", "--json"]]
    assert "unapproved.example" not in json.dumps(result["artifacts"])


def test_capture_fails_when_navigate_does_not_report_the_address_reached(env, monkeypatch):
    """Unknown destination: no final_url means no proof, so nothing is collected."""
    partial = {k: v for k, v in NAVIGATE_RESULT.items() if k != "final_url"}
    result, fake = run_capture(env, monkeypatch, **{"navigate": partial})
    assert (result["status"], result["reason"]) == ("failed", "destination_unknown")
    assert not fake.args_of("observe") and not fake.args_of("screenshot")
    assert fake.args_of("session stop")


@pytest.mark.parametrize("mutation", [
    {"final_url": None},
    {"tab_id": str(TAB_ID)},
    {"url": None},
])
def test_capture_fails_on_an_unrecognized_navigate_shape(env, monkeypatch, mutation):
    result, fake = run_capture(env, monkeypatch, **{"navigate": {**NAVIGATE_RESULT, **mutation}})
    assert result["status"] == "failed"
    assert result["reason"] in {"navigate_unrecognized", "destination_not_allowlisted"}
    assert not fake.args_of("observe")
    assert fake.args_of("session stop")


def test_capture_fails_when_navigate_reports_another_requested_url(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"navigate": {**NAVIGATE_RESULT,
                                                                 "url": "https://elsewhere.example/x"}})
    assert (result["status"], result["reason"]) == ("failed", "navigate_request_mismatch")
    assert not fake.args_of("observe")
    assert fake.args_of("session stop")


def test_capture_fails_when_the_session_comes_back_bound_to_another_browser(env, monkeypatch):
    """The requested --browser argument proves nothing; the binding must match."""
    result, fake = run_capture(env, monkeypatch, **{
        "session start": {**SESSION_START, "browser_instance_id": "0badbeef"}})
    assert (result["status"], result["reason"]) == ("failed", "wrong_browser_binding")
    assert "0badbeef" in result["detail"]
    # Only this run's own returned session is stopped, and nothing is navigated.
    assert fake.args_of("session stop") == [["session", "stop", "own-session", "--json"]]
    assert not fake.args_of("navigate") and not fake.args_of("screenshot")


def test_capture_fails_when_session_start_omits_the_browser_binding(env, monkeypatch):
    unbound = {k: v for k, v in SESSION_START.items() if k != "browser_instance_id"}
    result, fake = run_capture(env, monkeypatch, **{"session start": unbound})
    assert (result["status"], result["reason"]) == ("failed", "session_start_unrecognized")
    assert fake.args_of("session stop")
    assert not fake.args_of("navigate")


def test_capture_fails_when_session_start_reports_no_session_id(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{"session start": {
        **SESSION_START, "session_id": None}})
    assert (result["status"], result["reason"]) == ("failed", "session_id_missing")
    assert fake.args_of("session stop") == []  # nothing returned to clean up
    assert not fake.args_of("navigate")


def test_capture_fails_when_observe_reports_another_tab(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{
        "observe": {**OBSERVATION, "tab_id": TAB_ID + 7}})
    assert (result["status"], result["reason"]) == ("failed", "observe_tab_mismatch")
    assert not fake.args_of("screenshot")
    assert fake.args_of("session stop")


def test_capture_fails_when_an_observation_contradicts_the_verified_destination(env, monkeypatch):
    result, fake = run_capture(env, monkeypatch, **{
        "observe": {**OBSERVATION, "url": "https://unapproved.example/private"}})
    assert (result["status"], result["reason"]) == ("failed", "observe_url_mismatch")
    assert not fake.args_of("get-html") and not fake.args_of("screenshot")
    assert fake.args_of("session stop")


def test_capture_preserves_the_task_tab_and_binding_in_the_evidence(env, monkeypatch):
    result, _ = run_capture(env, monkeypatch)
    assert result["status"] == "ok"
    state = json.loads(Path(result["artifacts"]["attempt"]).read_text(encoding="utf-8"))
    assert state["tab_id"] == TAB_ID
    assert state["final_url"] == ALLOWED_URL
    events = [json.loads(line) for line
              in Path(result["artifacts"]["events"]).read_text(encoding="utf-8").splitlines()]
    started = [e for e in events if e["event"] == "session_started"][0]
    assert started["browser_instance_id"] == BROWSER_ID
    assert started["agent_window_id"] == SESSION_START["agent_window_id"]
    assert [e for e in events if e["event"] == "destination_verified"][0]["final_url"] == ALLOWED_URL
