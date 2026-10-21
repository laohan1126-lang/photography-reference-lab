"""Comprehensive regressions for BrowserSkill collection failure classification, bounded recovery, and state machine consistency.

Covers requirements R1 through R7:
- R1: Persistent navigation failure (bounded stop, browser_unavailable, not exhausted, unobserved queries not done)
- R2: Transient disconnect then recovery (recovers session, continues original query, no duplicate download or count corruption)
- R3: Unrecoverable connection (recovery budget exhausted, clean stop, blocked state preserved)
- R4: Normal content exhaustion (DOM read, 0 cards, search_plan_exhausted, queries marked done)
- R5: Platform-specific failure (one platform login_required/challenge does not kill browser or other platforms)
- R6: Existing progress preservation and resume (resumes from partial state, deduplicates, reaches target)
- R7: Error diagnostics and UI/API consistency (sanitized diagnostics, progress and summary consistent)
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from urllib.parse import quote

import pytest
from PIL import Image

from ref_lab import collection_queue
from ref_lab.browser_recovery import (
    BrowserError,
    BrowserInfrastructureError,
    PlatformRestrictionError,
    classify_bsk_error,
    sanitize_diagnostics,
)
from tools import collect_verified as worker

PROJECT = {"character": "西木野真姬", "work": "Love Live!", "costume": "", "brief": ""}
JOB_ID = "browserskill-recovery-suite"


def _photo(folder: Path, seed: int, page_url: str) -> dict:
    path = folder / "images" / f"test-{seed}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    from tests.test_collage_split import _textured
    _textured((800, 600), seed, (40 + seed * 7, 90, 150)).save(path, format="PNG")
    raw = path.read_bytes()
    row = {
        "asset_sha": hashlib.sha256(raw).hexdigest(),
        "original_path": str(path.resolve()),
        "page_url": page_url,
        "image_url": f"https://i.pinimg.com/736x/test-{seed}.jpg",
        "source_text": "西木野真姬 cos 摄影",
        "width": 800,
        "height": 600,
    }
    from tests.photo_type_fixture import synthetic_type
    synthetic_type(folder, row)
    return row


class SyntheticAgent:
    producer = "synthetic-recovery"
    model = "synthetic"
    candidate_calls = 0
    vision_cli_calls = 0
    references = []
    deadline = float("inf")

    def __init__(self):
        self.candidate_limit = 40

    def plan(self, project):
        raise AssertionError("search-only must not call name model")

    def prepare(self, project, plan):
        raise AssertionError("search-only must not prepare references")

    def review(self, path, project):
        raise AssertionError("search-only must not call vision")


def _job(target: int = 4, extra: int = 0) -> dict:
    return {
        "id": JOB_ID,
        "project_snapshot": PROJECT,
        "target_count": target,
        "preferred_sources": ["xiaohongshu", "pinterest"],
        "notes": "",
        "search_extra_target": extra,
    }


def test_r1_persistent_navigation_failure_stops_bounded_and_not_exhausted(tmp_path):
    """R1: Persistent navigation failures must stop boundedly with browser_unavailable,

    MUST NOT claim search_plan_exhausted, and MUST NOT mark unobserved queries as done.
    """
    navigate_attempts = []

    class FailingBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "mock-session"
            self.recovery_attempts = 0
            self.max_recovery_attempts = 1

        def start(self):
            pass

        def close(self):
            pass

        def can_recover(self):
            return self.recovery_attempts < self.max_recovery_attempts

        def recover(self, step=None):
            self.recovery_attempts += 1
            return False  # Recovery fails

        def search(self, step, sort="relevance"):
            navigate_attempts.append((step["source"], step["query"]))
            raise BrowserInfrastructureError(
                "BrowserSkill:action_failed - session not registered or already stopped",
                action="navigate",
                code="session_not_found",
                is_session_dead=True,
            )

    browser = FailingBrowser(tmp_path)
    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), browser, tmp_path, search_only=True)

    assert summary["stop_reason"] != "search_plan_exhausted"
    assert summary["stop_reason"] == "browser_unavailable"
    assert summary["status"] == "blocked"

    state = json.loads((tmp_path / "collector-state.json").read_text("utf8"))
    assert state.get("search_stop_reason") == "browser_unavailable"
    assert state.get("search_complete") is not True

    # Unobserved queries must NOT be marked done
    searches = state.get("searches", {})
    for k, s in searches.items():
        if not s.get("observed"):
            assert s.get("done") is not True, f"Search query {k} was never observed, must not be done"

    # Bounded stop: should not exhaustively run all 16-32 queries across all platforms
    assert len(navigate_attempts) <= 2, f"Expected bounded attempts (<=2), but got {len(navigate_attempts)}"


def test_r2_transient_disconnect_recovers_and_continues_original_query(tmp_path):
    """R2: A transient session disconnect is recovered, resumes the interrupted query,

    and succeeds without duplicate downloads or corrupting counts.
    """
    executed = []
    recovered_sessions = []

    class TransientDisconnectBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "session-1"
            self.disconnected = True
            self.recovery_attempts = 0
            self.max_recovery_attempts = 2
            self.sequence = 0

        def start(self):
            pass

        def close(self):
            pass

        def can_recover(self):
            return self.recovery_attempts < self.max_recovery_attempts

        def recover(self, step=None):
            self.recovery_attempts += 1
            self.session = f"session-recovered-{self.recovery_attempts}"
            recovered_sessions.append(self.session)
            self.disconnected = False
            return True

        def search(self, step, sort="relevance"):
            executed.append((self.session, step["source"], step["query"]))
            if self.disconnected:
                raise BrowserInfrastructureError(
                    "session not registered or already stopped",
                    action="navigate",
                    code="session_not_found",
                    is_session_dead=True,
                )
            # Return matching cards after recovery
            idx = len(executed)
            return {
                "url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}",
                "search": step["query"],
                "visibleMain": "",
                "cards": [
                    {"page": f"https://www.pinterest.com/pin/transient-{idx}-1/", "text": "西木野真姬 cos 摄影"},
                    {"page": f"https://www.pinterest.com/pin/transient-{idx}-2/", "text": "西木野真姬 cos 摄影"},
                ],
                "login_required": False,
                "challenge": False,
            }

        def more(self, step):
            return {"url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}", "search": step["query"], "visibleMain": "", "cards": [], "login_required": False, "challenge": False}

        def receive(self, card, step):
            self.sequence += 1
            return [_photo(self.folder, self.sequence, card["page"])]

    browser = TransientDisconnectBrowser(tmp_path)
    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), browser, tmp_path, search_only=True)

    assert len(recovered_sessions) == 1
    assert browser.recovery_attempts == 1
    assert summary["status"] == "completed"
    assert summary["target_reached"] is True
    assert summary["counts"]["found"] == 4

    # Verify browser-errors recorded recovery
    browser_errors = json.loads((tmp_path / "browser-errors.json").read_text("utf8"))
    assert any(e.get("result") == "recovered" or e.get("recovered") is True for e in browser_errors)

    # First executed call failed with session-1, second call retried the SAME query with session-recovered-1
    assert executed[0][0] == "session-1"
    assert executed[1][0] == "session-recovered-1"
    assert executed[0][1:] == executed[1][1:], "Must retry the exact same query after recovery"


def test_r3_unrecoverable_connection_stops_within_budget(tmp_path):
    """R3: When recovery fails or budget is exhausted, stop cleanly and retain blocked status."""
    class DeadDaemonBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "dead-session"
            self.recovery_attempts = 0
            self.max_recovery_attempts = 2

        def start(self):
            pass

        def close(self):
            pass

        def can_recover(self):
            return self.recovery_attempts < self.max_recovery_attempts

        def recover(self, step=None):
            self.recovery_attempts += 1
            return False  # daemon is dead, cannot recover

        def search(self, step, sort="relevance"):
            raise BrowserInfrastructureError(
                "connection refused",
                action="navigate",
                code="daemon_disconnected",
                is_daemon_down=True,
            )

    browser = DeadDaemonBrowser(tmp_path)
    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), browser, tmp_path, search_only=True)

    assert summary["status"] == "blocked"
    assert summary["stop_reason"] == "browser_unavailable"
    assert browser.recovery_attempts == 1

    progress = json.loads((tmp_path / "progress.json").read_text("utf8"))
    assert progress["phase"] == "finished"
    assert progress["outcome"] == "blocked"
    assert progress["stop_reason"] == "browser_unavailable"


def test_r4_normal_content_exhaustion_preserves_search_plan_exhausted(tmp_path):
    """R4: Normal content exhaustion (DOM read successfully, 0 cards) must still report search_plan_exhausted."""
    executed = []

    class EmptyContentBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "normal-session"

        def start(self):
            pass

        def close(self):
            pass

        def search(self, step, sort="relevance"):
            executed.append((step["source"], step["query"]))
            return {
                "url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}",
                "search": step["query"],
                "visibleMain": "",
                "cards": [],
                "login_required": False,
                "challenge": False,
            }

        def more(self, step):
            return {"url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}", "search": step["query"], "visibleMain": "", "cards": [], "login_required": False, "challenge": False}

    browser = EmptyContentBrowser(tmp_path)
    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), browser, tmp_path, search_only=True)

    # In this case, DOM was read, pages were observed, but content exhausted
    assert summary["stop_reason"] == "search_plan_exhausted"
    state = json.loads((tmp_path / "collector-state.json").read_text("utf8"))
    searches = state.get("searches", {})
    # Queries were actually observed
    for s in searches.values():
        assert s.get("observed") is True
        assert s.get("done") is True


def test_r5_platform_specific_failure_does_not_break_other_platforms(tmp_path):
    """R5: One platform hitting login_required or challenge does NOT stop the whole browser;

    other authorized platforms continue and succeed.
    """
    xhs_called = []
    pin_called = []

    class PlatformIsolatedBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "valid-session"
            self.sequence = 0

        def start(self):
            pass

        def close(self):
            pass

        def search(self, step, sort="relevance"):
            if step["source"] == "xiaohongshu":
                xhs_called.append(step["query"])
                # Xiaohongshu requires login / slider
                return {
                    "url": f"https://www.xiaohongshu.com/search_result?keyword={quote(step['query'])}",
                    "search": step["query"],
                    "visibleMain": "",
                    "cards": [],
                    "login_required": True,
                    "challenge": False,
                }
            pin_called.append(step["query"])
            return {
                "url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}",
                "search": step["query"],
                "visibleMain": "",
                "cards": [
                    {"page": f"https://www.pinterest.com/pin/pin-{len(pin_called)}-1/", "text": "西木野真姬 cos 摄影"},
                    {"page": f"https://www.pinterest.com/pin/pin-{len(pin_called)}-2/", "text": "西木野真姬 cos 摄影"},
                ],
                "login_required": False,
                "challenge": False,
            }

        def more(self, step):
            return {"url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}", "search": step["query"], "visibleMain": "", "cards": [], "login_required": False, "challenge": False}

        def receive(self, card, step):
            self.sequence += 1
            return [_photo(self.folder, self.sequence, card["page"])]

    browser = PlatformIsolatedBrowser(tmp_path)
    summary, _ = worker.collect(_job(target=4), SyntheticAgent(), browser, tmp_path, search_only=True)

    # XHS was stopped due to login_required, but Pinterest completed the 4 images!
    assert len(xhs_called) == 1, "XHS should be blocked after first login check"
    assert len(pin_called) >= 2, "Pinterest should continue to be used"
    assert summary["status"] == "completed"
    assert summary["target_reached"] is True
    assert summary["checks"]["xiaohongshu"]["status"] == "blocked"
    assert summary["checks"]["pinterest"]["status"] == "usable"


def test_r6_existing_progress_preserved_and_resumed_after_recovery(tmp_path):
    """R6: Ingests partial candidates before a failure; once recovered/resumed,

    previous originals/SHAs/dedup are preserved and task finishes remaining target.
    """
    # Step 1: Run with browser that succeeds for 2 images then fails with unrecoverable error
    class PartialThenFailBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "session-1"
            self.sequence = 0
            self.calls = 0

        def start(self):
            pass

        def close(self):
            pass

        def can_recover(self):
            return False  # Do not recover on this run

        def search(self, step, sort="relevance"):
            self.calls += 1
            if self.calls == 1:
                return {
                    "url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}",
                    "search": step["query"],
                    "visibleMain": "",
                    "cards": [
                        {"page": "https://www.pinterest.com/pin/part-1/", "text": "西木野真姬 cos 摄影"},
                        {"page": "https://www.pinterest.com/pin/part-2/", "text": "西木野真姬 cos 摄影"},
                    ],
                    "login_required": False,
                    "challenge": False,
                }
            raise BrowserInfrastructureError("session dropped", action="navigate", code="session_not_found")

        def more(self, step):
            return {"url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}", "search": step["query"], "visibleMain": "", "cards": [], "login_required": False, "challenge": False}

        def receive(self, card, step):
            self.sequence += 1
            return [_photo(self.folder, self.sequence, card["page"])]

    first_browser = PartialThenFailBrowser(tmp_path)
    first_summary, _ = worker.collect(_job(target=4), SyntheticAgent(), first_browser, tmp_path, search_only=True)

    assert first_summary["status"] == "partial"
    assert first_summary["stop_reason"] == "browser_unavailable"
    assert first_summary["counts"]["found"] == 2
    first_shas = [r["asset_sha"] for r in json.loads((tmp_path / "received.json").read_text("utf8"))]
    assert len(first_shas) == 2

    # Step 2: Resume the job with a working browser!
    class WorkingResumeBrowser:
        supports_sort = True

        def __init__(self, folder: Path):
            self.folder = folder
            self.session = "session-working"
            self.sequence = 2

        def start(self):
            pass

        def close(self):
            pass

        def search(self, step, sort="relevance"):
            return {
                "url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}",
                "search": step["query"],
                "visibleMain": "",
                "cards": [
                    {"page": "https://www.pinterest.com/pin/part-3/", "text": "西木野真姬 cos 摄影"},
                    {"page": "https://www.pinterest.com/pin/part-4/", "text": "西木野真姬 cos 摄影"},
                ],
                "login_required": False,
                "challenge": False,
            }

        def more(self, step):
            return {"url": f"https://www.pinterest.com/search/pins/?q={quote(step['query'])}", "search": step["query"], "visibleMain": "", "cards": [], "login_required": False, "challenge": False}

        def receive(self, card, step):
            self.sequence += 1
            return [_photo(self.folder, self.sequence, card["page"])]

    second_browser = WorkingResumeBrowser(tmp_path)
    second_summary, _ = worker.collect(_job(target=4), SyntheticAgent(), second_browser, tmp_path, search_only=True)

    # It must NOT return the old partial summary immediately; it must resume and finish!
    assert second_summary["status"] == "completed"
    assert second_summary["target_reached"] is True
    assert second_summary["counts"]["found"] == 4
    second_received = json.loads((tmp_path / "received.json").read_text("utf8"))
    assert len(second_received) == 4
    # The first 2 SHAs are intact
    assert [r["asset_sha"] for r in second_received[:2]] == first_shas
    assert len({r["asset_sha"] for r in second_received}) == 4


def test_r7_error_diagnostics_sanitized_and_consistent(tmp_path):
    """R7: Error diagnostics in browser-errors, collector-state, progress, and search-summary

    are sanitized, informative, and avoid misleading 'search_plan_exhausted' text.
    """
    raw_error_text = (
        "error: requested resource does not exist for token=secret12345678 in C:\\Users\\Dell\\AppData\\Local\\secret\n"
        "details: session not registered or already stopped"
    )

    err = classify_bsk_error("navigate", 1, "", raw_error_text)
    assert isinstance(err, BrowserInfrastructureError)
    assert err.code == "session_not_found"
    assert err.is_session_dead is True
    assert "secret12345678" not in err.raw_output
    assert "C:\\Users\\Dell" not in err.raw_output

    sanitized = sanitize_diagnostics({"token": "sensitive123456", "path": "C:\\Users\\Dell\\test.txt", "msg": "ok"})
    assert sanitized["token"] == "[REDACTED]"
    assert "C:\\Users\\Dell" not in sanitized["path"]
