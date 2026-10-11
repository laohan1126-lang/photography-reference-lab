#!/usr/bin/env python3
"""Minimal read-only AGY -> BrowserSkill bridge.

Purpose: let an AGY headless agent hold an exact, fixed grant for this one
Python script instead of an arbitrary shell grant or the whole BrowserSkill
feature set.  Browser/domain mechanics stay outside the orchestration Skill;
this file only performs a bounded, read-only navigation and capture against the
one Chrome instance pinned in a private policy file.

Deliberate non-goals (never implemented, not merely "unused"):
  * no publishing, config editing, provider changes or credentials
  * no daemon start/stop, no tab inventory, no click/fill/evaluate/upload/download
  * no arbitrary bsk arguments, no account changes, no other windows touched
  * never kills an unrelated process or session

The public CLI has no policy option: it always reads DEFAULT_POLICY from this
trusted checkout, so a caller who can only run this script cannot substitute a
policy (and therefore a bsk_path) of its own.  The Python functions take an
explicit policy_path for tests only.

The URL that was requested is never taken as proof of where navigation landed:
navigate's own `final_url` -- the address the tab actually reached -- is checked
against the same exact finite allowlist before any observation, HTML or
screenshot is collected, and the session's reported browser binding must match
the pinned instance.  Anything unknown, unexpected or unrecorded is a failure.

Stdlib only.  Every bsk call is an argv list with shell=False.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

BRIDGE = "agy-browser-bridge"
DEFAULT_POLICY = Path(__file__).resolve().parent.parent / ".local" / "agy-browser-policy.json"
MAX_SCROLL_Y = 5000
OBSERVE_MAX_TOKENS = 24000
NAVIGATE_WAIT_UNTIL = "domcontentloaded"
NAVIGATE_TIMEOUT_ARG = "45s"

PROBE_TIMEOUT = 20.0
SESSION_TIMEOUT = 90.0
NAVIGATE_TIMEOUT = 120.0
OBSERVE_TIMEOUT = 120.0
SCREENSHOT_TIMEOUT = 90.0

# This tool only proves command transport and policy enforcement.  It never
# proves that a browser, source or pixel was actually observed.
NOT_VERIFIED = (
    "Transport and policy evidence only: no visual, source, pixel or "
    "photographic success is claimed or implied by this run."
)

STATUS_OK, STATUS_BLOCKED, STATUS_FAILED = "ok", "blocked", "failed"

# The installed bsk 0.3.2 response shape.  `status --json` is a single object
# (pid, daemon_version, protocol_version, browsers, sessions,
# version_skew_browsers) and `browsers --json` is a bare JSON list of browser
# objects.  Any other shape is refused rather than guessed at.
BROWSER_ROW_FIELDS = ("browser_name", "browser_version", "extension_version",
                      "extension_protocol_version", "version_skew",
                      "unresponsive", "session_count")

# The installed bsk 0.3.2 response shapes for the three commands this bridge
# uses.  `session start --json` reports the window it bound and, crucially, the
# `browser_instance_id` the session is actually bound to.  `navigate --json`
# reports `url` (the address that was requested) *and* `final_url` (the address
# the tab actually reached after redirects) -- only the latter is proof of
# where the tab landed.  `observe --json` is the semantic VOM: text, ref_count,
# tab_id, truncated, and no url whatsoever.  Anything else is refused rather
# than guessed at.
SESSION_START_FIELDS = ("agent_window_id", "browser_instance_id", "interaction", "session_id")
NAVIGATE_FIELDS = ("tab_id", "url", "final_url", "reached")
OBSERVE_FIELDS = ("text", "ref_count", "tab_id", "truncated")

# Evidence a successful capture cannot do without.
REQUIRED_ARTIFACTS = ("observation", "html", "screenshot")


class BridgeBlocked(Exception):
    """A precondition failed; no browser action was taken or none may follow."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


# --------------------------------------------------------------------------
# subprocess transport
# --------------------------------------------------------------------------

def _bsk_env() -> dict[str, str]:
    """Always BSK_AUTO_START=0; an existing BSK_HOME is preserved as-is."""
    env = dict(os.environ)
    env["BSK_AUTO_START"] = "0"
    return env


def _execute(bsk_path: str, args: list[str], timeout: float, env: dict[str, str]) -> dict:
    """Run one bsk CLI command.  Never raises; records what actually happened."""
    argv = [bsk_path, *args]
    started = _utc()
    record = {
        "argv": argv,
        "cwd": os.getcwd(),
        "started_utc": started,
        "finished_utc": None,
        "timeout_s": timeout,
        "exit_code": None,
        "timed_out": False,
        "error": None,
        "stdout": "",
        "stderr": "",
    }
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=timeout, shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        record["timed_out"] = True
        record["error"] = f"timeout after {timeout}s"
        record["stdout"] = _as_text(exc.stdout)
        record["stderr"] = _as_text(exc.stderr)
    except (OSError, ValueError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    else:
        record["exit_code"] = completed.returncode
        record["stdout"] = completed.stdout or ""
        record["stderr"] = completed.stderr or ""
    record["finished_utc"] = _utc()
    return record


def _as_text(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)


def _json_result(record: dict) -> tuple[bool, object, str | None]:
    """(ok, parsed, reason).  Exit code 0 alone is never treated as success."""
    if record.get("error"):
        return False, None, record["error"]
    if record.get("timed_out"):
        return False, None, f"timeout after {record['timeout_s']}s"
    if record.get("exit_code") != 0:
        return False, None, f"exit_code={record.get('exit_code')}"
    try:
        data = json.loads(record["stdout"])
    except (ValueError, TypeError):
        return False, None, "stdout_not_json"
    if isinstance(data, dict):
        if data.get("error"):
            return False, data, f"cli_error:{str(data['error'])[:200]}"
        if data.get("success") is False:
            return False, data, "cli_success_false"
    return True, data, None


# --------------------------------------------------------------------------
# policy and argument validation (all before any session/browser action)
# --------------------------------------------------------------------------

def load_policy(path: Path) -> dict:
    if not path.is_file():
        raise BridgeBlocked("policy_missing", f"no policy file at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BridgeBlocked("policy_unreadable", f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(data, dict):
        raise BridgeBlocked("policy_invalid", "policy must be a JSON object")

    for key in ("browser_id", "allowed_urls", "evidence_root", "bsk_path"):
        if not data.get(key):
            raise BridgeBlocked("policy_invalid", f"missing policy key {key!r}")

    urls = data["allowed_urls"]
    if not isinstance(urls, list) or not urls:
        raise BridgeBlocked("policy_invalid", "allowed_urls must be a non-empty finite list")
    for url in urls:
        if not isinstance(url, str) or "*" in url:
            raise BridgeBlocked("policy_invalid", "allowed_urls entries must be literal strings without wildcards")
        _require_https(url, "allowed_urls entry")

    if not isinstance(data["bsk_path"], str) or not Path(data["bsk_path"]).is_absolute():
        raise BridgeBlocked("policy_invalid", "bsk_path must be an absolute path")
    if not Path(data["bsk_path"]).is_file():
        raise BridgeBlocked("bsk_missing", f"pinned bsk binary does not exist: {data['bsk_path']}")

    root = Path(str(data["evidence_root"]))
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise BridgeBlocked("policy_invalid", "evidence_root must be an existing absolute directory")

    data["evidence_root_path"] = root
    return data


def _require_https(url: str, label: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise BridgeBlocked("url_not_https", f"{label} must use https: {url}")
    if not parts.netloc:
        raise BridgeBlocked("url_invalid", f"{label} has no host: {url}")
    if parts.username or parts.password or "@" in parts.netloc:
        raise BridgeBlocked("url_userinfo", f"{label} must not carry userinfo: {url}")


def check_browser_id(policy: dict, browser_id: str) -> str:
    if browser_id != policy["browser_id"]:
        raise BridgeBlocked(
            "wrong_browser_profile",
            f"requested browser {browser_id!r} is not the pinned browser {policy['browser_id']!r}",
        )
    return browser_id


def check_url(policy: dict, url: str) -> str:
    _require_https(url, "url")
    if url not in policy["allowed_urls"]:
        raise BridgeBlocked("url_not_allowlisted", f"url is not an exact allowed_urls entry: {url}")
    return url


def check_scroll(scroll_y: int | None) -> int:
    if scroll_y is None:
        return 0
    if isinstance(scroll_y, bool) or not isinstance(scroll_y, int):
        raise BridgeBlocked("scroll_invalid", "scroll-y must be an integer")
    if scroll_y < 0 or scroll_y > MAX_SCROLL_Y:
        raise BridgeBlocked("scroll_invalid", f"scroll-y must be within 0..{MAX_SCROLL_Y}")
    return scroll_y


def check_out_dir(raw: str, evidence_root: Path) -> Path:
    """Absolute, inside evidence_root, symlink-free and not an existing attempt."""
    path = Path(raw)
    if not path.is_absolute():
        raise BridgeBlocked("out_dir_not_absolute", f"out-dir must be absolute: {raw}")
    if path.exists() or path.is_symlink():
        raise BridgeBlocked("out_dir_exists", f"refusing to overwrite an existing attempt directory: {raw}")
    resolved = path.resolve()
    root = evidence_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise BridgeBlocked("out_dir_outside_evidence_root", f"out-dir escapes evidence_root: {raw}")
    if _has_symlink_component(path, root):
        raise BridgeBlocked("out_dir_symlink", f"out-dir must not traverse a symlink or junction: {raw}")
    return resolved


def _has_symlink_component(path: Path, root: Path) -> bool:
    """True when any component below the pinned evidence root is a link."""
    cursor = Path(path.anchor)
    below_root = False
    for part in path.parts[1:]:
        cursor = cursor / part
        if cursor == root:
            below_root = True
        elif below_root and (cursor.is_symlink() or getattr(cursor, "is_junction", lambda: False)()):
            return True
    return False


def new_preflight_dir(evidence_root: Path) -> Path:
    stamp = _utc().replace(":", "").replace("-", "")
    base = evidence_root / f"preflight-{stamp}-{os.getpid()}"
    for index in range(0, 100):
        candidate = base if index == 0 else Path(f"{base}-{index}")
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
    raise BridgeBlocked("out_dir_exists", "could not allocate a free preflight evidence directory")


# --------------------------------------------------------------------------
# evidence recording
# --------------------------------------------------------------------------

class Attempt:
    """Append-only private evidence for one bridge run."""

    def __init__(self, directory: Path, kind: str, bsk_path: str, facts: dict):
        self.directory = directory
        self.bsk_path = bsk_path
        self.started_utc = _utc()
        self.state = {
            "bridge": BRIDGE,
            "kind": kind,
            "started_utc": self.started_utc,
            "finished_utc": None,
            "status": "in_progress",
            "facts": facts,
            "session_id": None,
            "steps": [],
            "artifacts": {},
            "failures": [],
            "cleanup": None,
        }
        directory.mkdir(parents=True, exist_ok=False)
        self.commands_dir = directory / "commands"
        self.commands_dir.mkdir()
        self._flush()

    def _flush(self) -> None:
        (self.directory / "attempt.json").write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8",
        )

    def note(self, event: str, **fields) -> None:
        line = json.dumps({"utc": _utc(), "event": event, **fields}, ensure_ascii=False)
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def command(self, phase: str, args: list[str], timeout: float, env: dict[str, str]) -> dict:
        record = _execute(self.bsk_path, args, timeout, env)
        base = self.commands_dir / phase
        out_path, err_path = Path(f"{base}.stdout.txt"), Path(f"{base}.stderr.txt")
        out_path.write_text(record["stdout"], encoding="utf-8", errors="replace")
        err_path.write_text(record["stderr"], encoding="utf-8", errors="replace")
        ok, parsed, reason = _json_result(record)
        step = {
            "phase": phase,
            "argv": record["argv"],
            "started_utc": record["started_utc"],
            "finished_utc": record["finished_utc"],
            "timeout_s": timeout,
            "exit_code": record["exit_code"],
            "timed_out": record["timed_out"],
            "error": record["error"],
            "ok": ok,
            "reason": reason,
            "stdout_file": str(out_path),
            "stderr_file": str(err_path),
        }
        self.state["steps"].append(step)
        self.note("command", **step)
        self._flush()
        record["_ok"], record["_data"], record["_reason"] = ok, parsed, reason
        return record

    def require(self, record: dict, code: str) -> object:
        if not record["_ok"]:
            self.note("failure", code=code, reason=record["_reason"])
            raise BridgeBlocked(code, str(record["_reason"]))
        return record["_data"]

    def artifact(self, name: str, path: Path, sha: bool = False) -> Path:
        self.state["artifacts"][name] = str(path)
        if sha:
            self.state["artifacts"][f"{name}_sha256"] = _sha256_file(path)
        self.note("artifact", name=name, path=str(path))
        self._flush()
        return path

    def finish(self, status: str, **fields) -> None:
        self.state.update(fields)
        self.state["status"] = status
        self.state["finished_utc"] = _utc()
        self.state["artifacts"].setdefault("attempt", str(self.directory / "attempt.json"))
        self.state["artifacts"]["events"] = str(self.directory / "events.jsonl")
        self._flush()
        self.note("finished", status=status)


def _result(status: str, started_utc: str, **fields) -> dict:
    return {
        "bridge": BRIDGE,
        "status": status,
        "started_utc": started_utc,
        "finished_utc": _utc(),
        "evidence_only": True,
        "not_verified": NOT_VERIFIED,
        **fields,
    }


# --------------------------------------------------------------------------
# preflight (read-only probes only)
# --------------------------------------------------------------------------

def _refuse(attempt: Attempt, blocked: BridgeBlocked) -> BridgeBlocked:
    attempt.state["failures"].append({"code": blocked.code, "detail": blocked.detail})
    attempt.note("failure", code=blocked.code, detail=blocked.detail)
    return blocked


def select_browser(rows, browser_id: str, policy: dict, status: dict) -> tuple[dict, int]:
    """The one row of `browsers --json` for the pinned instance, or a refusal.

    Only the installed bsk 0.3.2 shape is accepted.  A row that is missing,
    duplicated, unresponsive or reported version-skewed stops the run; nothing
    is inferred about a shape this script has never actually seen.
    """
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise BridgeBlocked(
            "browser_probe_unrecognized",
            f"browsers --json must be a JSON list of objects, got {type(rows).__name__}")
    matches = [row for row in rows if row.get("instance_id") == browser_id]
    if not matches:
        raise BridgeBlocked("connected_browser_absent", f"pinned browser {browser_id} is not connected")
    if len(matches) > 1:
        raise BridgeBlocked("browser_row_ambiguous",
                            f"{len(matches)} rows report instance {browser_id}; refusing to guess")
    row = matches[0]
    missing = [field for field in BROWSER_ROW_FIELDS if field not in row]
    if missing:
        raise BridgeBlocked("browser_row_unrecognized", f"selected row is missing {missing}")

    expected_name = policy.get("browser_name")
    if expected_name and row["browser_name"] != expected_name:
        raise BridgeBlocked(
            "wrong_browser_profile",
            f"pinned browser reports {row['browser_name']!r}, policy expects {expected_name!r}")

    if row["unresponsive"]:
        raise BridgeBlocked("browser_not_responsive", f"pinned browser {browser_id} reports unresponsive")

    skewed = bool(row["version_skew"]) or browser_id in (status.get("version_skew_browsers") or [])
    if skewed:
        raise BridgeBlocked("version_skew", f"pinned browser {browser_id} is reported version-skewed")

    # Chrome's browser_version is its own build number (154.0.0.0); it is never
    # compared against the daemon version.  Only the extension pair agrees.
    daemon_version, protocol_version = status.get("daemon_version"), status.get("protocol_version")
    if not daemon_version or not protocol_version:
        raise BridgeBlocked("daemon_status_unrecognized",
                            "status lacks daemon_version/protocol_version")
    if str(daemon_version) != str(row["extension_version"]):
        raise BridgeBlocked(
            "version_mismatch",
            f"daemon {daemon_version} vs extension {row['extension_version']}")
    if str(protocol_version) != str(row["extension_protocol_version"]):
        raise BridgeBlocked(
            "protocol_mismatch",
            f"daemon protocol {protocol_version} vs extension {row['extension_protocol_version']}")

    # Session ownership is read per browser instance, so another browser's
    # sessions are never this run's business and are never stopped.
    sessions = row["session_count"]
    if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions < 0:
        raise BridgeBlocked("browser_row_unrecognized", "session_count must be a non-negative integer")
    if sessions:
        raise BridgeBlocked(
            "overlapping_session",
            f"{sessions} session(s) already bound to the pinned browser; this bridge will not take over")
    return row, sessions


def run_preflight(attempt: Attempt, policy: dict, browser_id: str) -> dict:
    """Confirm the existing daemon and the pinned browser are usable as-is."""
    env = _bsk_env()

    status = attempt.require(
        attempt.command("status", ["status", "--json"], PROBE_TIMEOUT, env), "daemon_status_failed")
    if not isinstance(status, dict) or not status.get("pid"):
        raise _refuse(attempt, BridgeBlocked(
            "daemon_not_running", "no existing BrowserSkill daemon; the bridge never starts one"))

    browsers = attempt.require(
        attempt.command("browsers", ["browsers", "--json"], PROBE_TIMEOUT, env), "browser_probe_failed")
    try:
        row, sessions = select_browser(browsers, browser_id, policy, status)
    except BridgeBlocked as blocked:
        raise _refuse(attempt, blocked)

    # Only the pinned browser's own identity is reported: no tab or session inventory.
    summary = {
        "daemon_running": True,
        "versions_agree": True,
        "daemon_version": str(status["daemon_version"]),
        "protocol_version": str(status["protocol_version"]),
        "browser_name": row["browser_name"],
        "browser_version": row["browser_version"],
        "extension_version": str(row["extension_version"]),
        "extension_protocol_version": str(row["extension_protocol_version"]),
        "browsers_seen": len(browsers),
        "sessions_on_browser": sessions,
    }
    attempt.note("preflight_pass", browser_id=browser_id, browser_name=row["browser_name"])
    return summary


def do_preflight(policy_path: Path, browser_id: str) -> dict:
    started = _utc()
    try:
        policy = load_policy(policy_path)
        check_browser_id(policy, browser_id)
        directory = new_preflight_dir(policy["evidence_root_path"])
    except BridgeBlocked as blocked:
        return _result(STATUS_BLOCKED, started, reason=blocked.code, detail=blocked.detail,
                       browser_id=browser_id, policy=str(policy_path))

    attempt = Attempt(directory, "preflight", policy["bsk_path"],
                      {"browser_id": browser_id, "policy": str(policy_path)})
    try:
        summary = run_preflight(attempt, policy, browser_id)
    except BridgeBlocked as blocked:
        attempt.finish(STATUS_BLOCKED, reason=blocked.code, detail=blocked.detail)
        return _result(STATUS_BLOCKED, started, reason=blocked.code, detail=blocked.detail,
                       browser_id=browser_id, policy=str(policy_path),
                       attempt_dir=str(directory), artifacts=attempt.state["artifacts"])
    except Exception as exc:  # unexpected: still honest, never a success claim
        attempt.finish(STATUS_FAILED, reason="preflight_exception", detail=f"{type(exc).__name__}: {exc}")
        return _result(STATUS_FAILED, started, reason="preflight_exception",
                       detail=f"{type(exc).__name__}: {exc}", browser_id=browser_id,
                       attempt_dir=str(directory), artifacts=attempt.state["artifacts"])
    attempt.finish(STATUS_OK, checks=summary, browser={"browser_id": browser_id, "browser_name": policy.get("browser_name")})
    return _result(STATUS_OK, started, browser={"browser_id": browser_id}, checks=summary,
                   attempt_dir=str(directory), artifacts=attempt.state["artifacts"])


# --------------------------------------------------------------------------
# capture
# --------------------------------------------------------------------------

def _stop_session(attempt: Attempt, session_id: str, env: dict[str, str]) -> bool:
    """Always attempt cleanup; never kill anything else."""
    try:
        record = attempt.command("session_stop", ["session", "stop", session_id, "--json"],
                                 SESSION_TIMEOUT, env)
        ok = record["_ok"]
        detail = None if ok else record["_reason"]
    except Exception as exc:
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    attempt.state["cleanup"] = {"session_id": session_id, "ok": ok, "detail": detail}
    attempt.note("cleanup", session_id=session_id, ok=ok, detail=detail)
    attempt._flush()
    return ok


def check_session_binding(policy: dict, browser_id: str, started_data: object) -> str:
    """The session must come back bound to the pinned browser instance.

    The requested --browser argument is not proof of anything; only the
    instance the session actually reports may be compared with the policy.
    """
    if not isinstance(started_data, dict):
        raise BridgeBlocked("session_start_unrecognized",
                            f"session start --json must be an object, got {type(started_data).__name__}")
    missing = [field for field in SESSION_START_FIELDS if field not in started_data]
    if missing:
        raise BridgeBlocked("session_start_unrecognized",
                            f"session start response is missing {missing}")
    bound = started_data["browser_instance_id"]
    if not isinstance(bound, str) or not bound:
        raise BridgeBlocked("session_binding_missing",
                            "session start did not report a usable browser_instance_id")
    if bound != policy["browser_id"]:
        raise BridgeBlocked(
            "wrong_browser_binding",
            f"session came back bound to browser instance {bound!r}, "
            f"not the pinned {policy['browser_id']!r}")
    return str(started_data["session_id"])


def check_destination(policy: dict, requested_url: str, navigate_data: object) -> tuple[str, int]:
    """(final_url, tab_id) for the address the tab *actually* reached.

    The requested seed URL is never treated as proof of where navigation
    landed; only navigate's own `final_url` is checked, and against the same
    exact finite allowed_urls list.
    """
    if not isinstance(navigate_data, dict):
        raise BridgeBlocked("navigate_unrecognized",
                            f"navigate --json must be an object, got {type(navigate_data).__name__}")
    if "final_url" not in navigate_data:
        raise BridgeBlocked("destination_unknown",
                            "navigate did not report final_url, the address actually reached")
    missing = [field for field in NAVIGATE_FIELDS if field not in navigate_data]
    if missing:
        raise BridgeBlocked("navigate_unrecognized", f"navigate response is missing {missing}")

    requested_reported, final_url, tab_id = (navigate_data["url"], navigate_data["final_url"],
                                            navigate_data["tab_id"])
    if not isinstance(final_url, str) or not isinstance(requested_reported, str):
        raise BridgeBlocked("navigate_unrecognized", "navigate url and final_url must be strings")
    if isinstance(tab_id, bool) or not isinstance(tab_id, int):
        raise BridgeBlocked("navigate_unrecognized", "navigate tab_id must be an integer")
    if requested_reported != requested_url:
        raise BridgeBlocked("navigate_request_mismatch",
                            f"navigate reports requesting {requested_reported!r}, "
                            f"but {requested_url!r} was asked for")
    try:
        check_url(policy, final_url)
    except BridgeBlocked as blocked:
        raise BridgeBlocked(
            "destination_not_allowlisted",
            f"the tab actually landed on {final_url}, which is not an exact "
            f"allowed_urls entry ({blocked.code}: {blocked.detail})") from blocked
    return final_url, tab_id


def check_observation(observation: object, expected_tab_id: int, final_url: str) -> None:
    """The semantic VOM must belong to this run's task tab and nothing else."""
    if not isinstance(observation, dict):
        raise BridgeBlocked("observe_unrecognized",
                            f"observe --json must be an object, got {type(observation).__name__}")
    missing = [field for field in OBSERVE_FIELDS if field not in observation]
    if missing:
        raise BridgeBlocked("observe_unrecognized", f"observe response is missing {missing}")
    if observation["tab_id"] != expected_tab_id:
        raise BridgeBlocked("observe_tab_mismatch",
                            f"observe reported tab {observation['tab_id']!r}, "
                            f"not this run's task tab {expected_tab_id!r}")
    # The installed observe shape carries no url.  If one is ever reported and
    # contradicts the destination already verified, that contradiction is fatal.
    reported_url = observation.get("url")
    if reported_url is not None and reported_url != final_url:
        raise BridgeBlocked("observe_url_mismatch",
                            f"observe reported url {reported_url!r} but the tab is at {final_url!r}")


def missing_artifacts(attempt: Attempt, scrolled: bool) -> list[str]:
    """Required evidence that is unrecorded or not actually on disk."""
    required = REQUIRED_ARTIFACTS + (("observation_after_scroll",) if scrolled else ())
    missing = [name for name in required
               if not attempt.state["artifacts"].get(name)
               or not Path(attempt.state["artifacts"][name]).is_file()]
    if not attempt.state["artifacts"].get("screenshot_sha256"):
        missing.append("screenshot_sha256")
    return sorted(missing)


def do_capture(policy_path: Path, browser_id: str, url: str, out_dir: str,
               scroll_y: int | None) -> dict:
    started = _utc()
    facts: dict = {"browser_id": browser_id, "url": url, "policy": str(policy_path)}
    try:
        policy = load_policy(policy_path)
        check_browser_id(policy, browser_id)
        check_url(policy, url)
        facts["scroll_y"] = check_scroll(scroll_y)
        directory = check_out_dir(out_dir, policy["evidence_root_path"])
    except BridgeBlocked as blocked:
        return _result(STATUS_BLOCKED, started, reason=blocked.code, detail=blocked.detail,
                       browser_id=browser_id, url=url, policy=str(policy_path))

    facts["evidence_dir"] = str(directory)
    attempt = Attempt(directory, "capture", policy["bsk_path"], facts)
    env = _bsk_env()
    own_session: str | None = None
    final_url: str | None = None
    tab_id: int | None = None
    blocked_exc: BridgeBlocked | None = None
    exception_detail: str | None = None

    try:
        try:
            run_preflight(attempt, policy, browser_id)
        except BridgeBlocked as blocked:
            attempt.finish(STATUS_BLOCKED, reason=blocked.code, detail=blocked.detail)
            return _result(STATUS_BLOCKED, started, reason=blocked.code, detail=blocked.detail,
                           browser_id=browser_id, url=url, scroll_y=facts["scroll_y"],
                           attempt_dir=str(directory), artifacts=attempt.state["artifacts"])

        started_data = attempt.require(
            attempt.command("session_start",
                            ["session", "start", "--browser", browser_id, "--no-focus", "--json"],
                            SESSION_TIMEOUT, env), "session_start_failed")
        own_session = (started_data or {}).get("session_id") if isinstance(started_data, dict) else None
        if not own_session:
            attempt.note("failure", code="session_id_missing")
            raise BridgeBlocked("session_id_missing", "session start returned no session_id")
        # The id is recorded first so that even a rejected binding still gets
        # this run's own session stopped in the finally block below.
        attempt.state["session_id"] = own_session
        attempt._flush()
        own_session = check_session_binding(policy, browser_id, started_data)
        attempt.note("session_started", session_id=own_session,
                     browser_instance_id=started_data["browser_instance_id"],
                     agent_window_id=started_data["agent_window_id"])

        # The requested seed URL is validated up front and again below against
        # what the tab actually reached; the requested address alone is never
        # evidence that navigation landed anywhere in particular.
        navigated = attempt.require(
            attempt.command("navigate",
                            ["navigate", url, "--session", own_session,
                             "--wait-until", NAVIGATE_WAIT_UNTIL,
                             "--timeout", NAVIGATE_TIMEOUT_ARG, "--json"],
                            NAVIGATE_TIMEOUT, env), "navigate_failed")
        final_url, tab_id = check_destination(policy, url, navigated)
        attempt.state["final_url"] = final_url
        attempt.state["tab_id"] = tab_id
        attempt.note("destination_verified", final_url=final_url, tab_id=tab_id)
        attempt._flush()

        observation = attempt.require(
            attempt.command("observe", ["observe", "--session", own_session,
                                        "--max-tokens", str(OBSERVE_MAX_TOKENS), "--json"],
                            OBSERVE_TIMEOUT, env), "observe_failed")
        check_observation(observation, tab_id, final_url)
        observation_path = attempt.directory / "observation.json"
        observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False), encoding="utf-8")
        attempt.artifact("observation", observation_path)

        html = attempt.require(
            attempt.command("get_html", ["get-html", "--session", own_session, "--json"],
                            OBSERVE_TIMEOUT, env), "get_html_failed")
        html_path = attempt.directory / "page.html"
        html_path.write_text(html if isinstance(html, str) else json.dumps(html, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        attempt.artifact("html", html_path)

        if facts["scroll_y"]:
            attempt.require(
                attempt.command("wheel", ["wheel", "--delta-y", str(facts["scroll_y"]),
                                          "--session", own_session, "--json"],
                                SESSION_TIMEOUT, env), "wheel_failed")
            scrolled = attempt.require(
                attempt.command("observe_after_scroll",
                                ["observe", "--session", own_session,
                                 "--max-tokens", str(OBSERVE_MAX_TOKENS), "--json"],
                                OBSERVE_TIMEOUT, env), "observe_after_scroll_failed")
            check_observation(scrolled, tab_id, final_url)
            scrolled_path = attempt.directory / "observation-after-scroll.json"
            scrolled_path.write_text(json.dumps(scrolled, indent=2, ensure_ascii=False), encoding="utf-8")
            attempt.artifact("observation_after_scroll", scrolled_path)

        shot = attempt.command("screenshot",
                               ["screenshot", "--session", own_session,
                                "--out", str(directory / "viewport.png"), "--json"],
                               SCREENSHOT_TIMEOUT, env)
        if not shot["_ok"] or not (directory / "viewport.png").is_file():
            attempt.note("failure", code="screenshot_failed", reason=shot["_reason"])
            raise BridgeBlocked("screenshot_failed", str(shot["_reason"]))
        attempt.artifact("screenshot", directory / "viewport.png", sha=True)
    except BridgeBlocked as blocked:
        attempt.state["failures"].append({"code": blocked.code, "detail": blocked.detail})
        attempt.note("blocked", code=blocked.code, detail=blocked.detail)
        blocked_exc = blocked
    except Exception as exc:
        # An unexpected error (a full disk while writing evidence, a bug) is
        # still a failure.  It is never swallowed into a soft success.
        exception_detail = f"{type(exc).__name__}: {exc}"
        attempt.state["failures"].append({"code": "capture_exception", "detail": exception_detail})
        attempt.note("capture_exception", detail=exception_detail)
    finally:
        # The own session is always stopped, even after a navigation/capture
        # failure.  Nothing else is ever stopped or killed.
        cleanup_ok = True
        if own_session:
            cleanup_ok = _stop_session(attempt, own_session, env)

    # A success additionally requires every required artifact to exist on disk.
    if blocked_exc is None and exception_detail is None:
        absent = missing_artifacts(attempt, bool(facts["scroll_y"]))
        if absent:
            blocked_exc = BridgeBlocked(
                "artifacts_incomplete",
                f"required evidence missing or unreadable: {absent}")
            attempt.state["failures"].append({"code": blocked_exc.code, "detail": blocked_exc.detail})
            attempt.note("blocked", code=blocked_exc.code, detail=blocked_exc.detail)

    artifacts = dict(attempt.state["artifacts"])
    artifacts.setdefault("attempt", str(directory / "attempt.json"))
    artifacts["events"] = str(directory / "events.jsonl")
    common = {
        "browser": {"browser_id": browser_id},
        "session": {"session_id": own_session, "cleanup_ok": cleanup_ok},
        "source_url": url,
        "final_url": final_url,
        "tab_id": tab_id,
        "scroll_y": facts["scroll_y"],
        "attempt_dir": str(directory),
        "artifacts": artifacts,
    }

    # Preflight refusals returned early as "blocked"; anything after a session
    # existed is a failure, never a soft success.
    if blocked_exc is not None or exception_detail is not None or not cleanup_ok:
        status = STATUS_FAILED
    else:
        status = STATUS_OK
    if blocked_exc is not None:
        common["reason"] = blocked_exc.code
        common["detail"] = blocked_exc.detail
    if exception_detail is not None:
        common["reason"] = "capture_exception"
        common["detail"] = exception_detail
    if not cleanup_ok:
        common["reason"] = "cleanup_failed"
        common["detail"] = "session stop did not succeed; this run is not a success"

    attempt.finish(status, reason=common.get("reason"), session_id=own_session)
    return _result(status, started, **common)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """There is deliberately no --policy option on any subcommand.

    A caller who is granted only this script could otherwise author a policy
    naming its own bsk_path and run an arbitrary executable through the fixed
    permission grant.  The policy is therefore fixed at DEFAULT_POLICY.
    """
    parser = argparse.ArgumentParser(
        prog=BRIDGE, description="Minimal read-only AGY/BrowserSkill bridge (policy-pinned, one browser).")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="read-only daemon/browser checks")
    pre.add_argument("--browser-id", required=True)

    cap = sub.add_parser("capture", help="navigate and capture one allowlisted URL, then always stop the session")
    cap.add_argument("--browser-id", required=True)
    cap.add_argument("--url", required=True)
    cap.add_argument("--out-dir", required=True)
    cap.add_argument("--scroll-y", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    policy_path = Path(DEFAULT_POLICY)
    if args.command == "preflight":
        result = do_preflight(policy_path, args.browser_id)
    else:
        result = do_capture(policy_path, args.browser_id, args.url, args.out_dir, args.scroll_y)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return {STATUS_OK: 0, STATUS_BLOCKED: 2, STATUS_FAILED: 3}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
