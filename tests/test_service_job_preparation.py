"""Service regressions for fast Job creation, background preparation and list projection."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ref_lab import api, collection_stages, service
from ref_lab.models import JobInput, ProjectInput


def wait_until(predicate, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.02)
    raise AssertionError("timed out waiting for service state")


@pytest.fixture
def project(library, tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir(parents=True)
    monkeypatch.setattr(service, "__file__", str(root / "ref_lab" / "service.py"))
    monkeypatch.setenv("LAB_DATA_DIR", str(root / "data"))
    monkeypatch.setenv("LAB_COLLECTION_HISTORY_DIR", str(root / "data" / "assets"))
    monkeypatch.setenv("LAB_COLLECTION_HISTORY_ROOTS", "[]")
    return library.create_project(ProjectInput(character="后台准备测试"))


def collection_job(library, project, mode="search"):
    return library.create_job(project["id"], JobInput(
        kind="collection", collection_mode=mode, target_count=2))


def test_create_persists_pending_without_building_history(library, project, monkeypatch):
    monkeypatch.setattr(library, "_create_auto_goal",
                        lambda *args, **kwargs: pytest.fail("create_job built history"))
    started = time.monotonic()
    job = collection_job(library, project)
    elapsed = time.monotonic() - started
    assert elapsed < 1.0, elapsed
    assert job["preparation_state"] == "pending"
    assert job["search_state"] == "idle"
    assert job["goal_id"]
    assert not (Path(service.__file__).parents[1] / ".local" / "goals" / job["goal_id"]).exists()


def test_start_prepares_in_background_once_then_dispatches(library, project, monkeypatch):
    launched = []
    monkeypatch.setattr(collection_stages, "launch_search",
                        lambda current, job_id, **kwargs: (launched.append(job_id) or current.job(job_id)))
    job = collection_job(library, project)
    started = time.monotonic()
    first = collection_stages.start_job(library, job["id"])
    second = collection_stages.start_job(library, job["id"])
    assert time.monotonic() - started < 1.0
    assert first["preparation_state"] == second["preparation_state"] == "running"
    wait_until(lambda: library.job(job["id"])["preparation_state"] in {"ready", "failed"})
    current = library.job(job["id"])
    assert current["preparation_state"] == "ready", current.get("preparation_detail")
    wait_until(lambda: launched)
    assert current["preparation_state"] == "ready"
    assert launched == [job["id"]]
    goal = Path(service.__file__).parents[1] / ".local" / "goals" / job["goal_id"]
    assert json.loads((goal / "goal.json").read_text("utf8"))["goal_id"] == job["goal_id"]


def test_concurrent_start_claims_one_preparation(library, project, monkeypatch):
    job = collection_job(library, project)
    entered = threading.Event()
    release = threading.Event()
    calls = []

    def held(*args):
        calls.append(args)
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(collection_stages, "_prepare_then_launch", held)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: collection_stages.start_job(library, job["id"]), range(2)))
    assert entered.wait(5)
    assert all(result["preparation_state"] == "running" for result in results)
    assert len(calls) == 1
    release.set()
    wait_until(lambda: (job["id"], "prepare") not in collection_stages._RUNNING)


def test_preparation_failure_is_retryable_without_budget_change(library, project, monkeypatch):
    job = collection_job(library, project)
    original_replace = service.os.replace
    monkeypatch.setattr(service.os, "replace",
                        lambda *args: (_ for _ in ()).throw(PermissionError("synthetic publish failure")))
    collection_stages.start_job(library, job["id"])
    failed = wait_until(lambda: (current := library.job(job["id"]))["preparation_state"] == "failed" and current)
    assert failed["goal_id"] == job["goal_id"]
    assert failed.get("search_timeout_seconds") is None
    goals = Path(service.__file__).parents[1] / ".local" / "goals"
    assert not (goals / job["goal_id"]).exists()
    assert not list(goals.glob(".p-*"))

    launched = []
    monkeypatch.setattr(service.os, "replace", original_replace)
    monkeypatch.setattr(collection_stages, "launch_search",
                        lambda current, job_id, **kwargs: (launched.append(job_id) or current.job(job_id)))
    collection_stages.start_job(library, job["id"])
    wait_until(lambda: library.job(job["id"])["preparation_state"] in {"ready", "failed"})
    current = library.job(job["id"])
    assert current["preparation_state"] == "ready", current.get("preparation_detail")
    wait_until(lambda: launched)
    retried = library.job(job["id"])
    assert retried["preparation_state"] == "ready"
    assert retried.get("search_timeout_seconds") == failed.get("search_timeout_seconds")


def test_cancel_during_preparation_prevents_collector_dispatch(library, project, monkeypatch):
    job = collection_job(library, project)
    entered = threading.Event()
    release = threading.Event()
    launched = []
    original_create = library._create_auto_goal

    def slow_create(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original_create(*args, **kwargs)

    monkeypatch.setattr(library, "_create_auto_goal", slow_create)
    monkeypatch.setattr(collection_stages, "launch_search",
                        lambda *args, **kwargs: launched.append(args) or pytest.fail(
                            "cancelled preparation launched search"))
    collection_stages.start_job(library, job["id"])
    assert entered.wait(5)
    cancelled = library.cancel_search_stage(job["id"])
    release.set()
    wait_until(lambda: (job["id"], "prepare") not in collection_stages._RUNNING)
    current = library.job(job["id"])
    assert cancelled["search_state"] == current["search_state"] == "cancelled"
    assert launched == []


def test_summary_page_and_detail_retry_fields_do_not_scan_candidates(app, library, project, monkeypatch):
    job = collection_job(library, project)
    verified = collection_job(library, project, mode="verified")
    list_route = next(route for route in app.routes if route.path == "/api/jobs")
    legacy = list_route.endpoint(summary=False, limit=20, offset=0)
    assert isinstance(legacy, list) and {row["id"] for row in legacy} == {job["id"], verified["id"]}
    from ref_lab.db import encode
    current = library.job(job["id"])
    current.update(preparation_state="ready", search_state="completed", review_state="idle",
                   search_counts={"found": 2})
    with library.db.transaction() as con:
        con.execute("UPDATE jobs SET status=?,data=? WHERE id=?",
                    (current["status"], encode(current), job["id"]))
    monkeypatch.setattr(api, "candidate_snapshot",
                        lambda *args, **kwargs: pytest.fail("summary scanned candidates"))
    page = list_route.endpoint(summary=True, limit=20, offset=0)
    items = {row["id"]: row for row in page["items"]}
    assert page["total"] == 2
    assert set(page) == {"items", "total", "limit", "offset"}
    assert items[job["id"]]["is_split_mode"] is True
    assert items[job["id"]]["can_start_review"] is True
    assert items[job["id"]]["can_retry_search"] is False
    assert items[job["id"]]["search_budget_exhausted"] is False
    assert items[verified["id"]]["is_split_mode"] is False
    assert items[verified["id"]]["can_start_review"] is False

    current = library.job(job["id"])
    current.update(preparation_state="failed", preparation_detail="synthetic start failure",
                   status="blocked")
    with library.db.transaction() as con:
        con.execute("UPDATE jobs SET status=?,data=? WHERE id=?",
                    (current["status"], encode(current), job["id"]))
    detail_route = next(route for route in app.routes if route.path == "/api/jobs/{job_id}")
    detail = detail_route.endpoint(job["id"])
    assert detail["preparation_state"] == "failed"
    assert detail["can_retry_search"] is True
    assert detail["search_budget_exhausted"] is False
    assert detail["can_start_review"] is False


def test_pure_time_retry_requires_an_exhausted_budget(library, project, monkeypatch):
    job = collection_job(library, project)
    with library.db.transaction() as con:
        current = library.job(job["id"])
        current.update(search_state="blocked", search_stop_reason="navigation_failed",
                       search_timeout_seconds=900, status="blocked")
        library._save_job(con, current, "synthetic.navigation_failed", {}, "worker")
    with pytest.raises(service.Problem) as failure:
        library.replenish_search(job["id"], 60)
    assert failure.value.details == {"code": "search_budget_not_exhausted"}

    monkeypatch.setattr(service, "_preflight_search_goal", lambda *args: None)
    with library.db.transaction() as con:
        current = library.job(job["id"])
        current["search_stop_reason"] = "time_budget_exhausted"
        library._save_job(con, current, "synthetic.budget_exhausted", {}, "worker")
    replenished = library.replenish_search(job["id"], 60)
    assert replenished["search_timeout_seconds"] == 960


def test_verified_runner_prepares_baseline_before_attempt(library, project, monkeypatch):
    from ref_lab.agent_collection import run_collection_attempt

    job = collection_job(library, project, mode="verified")
    goal = Path(service.__file__).parents[1] / ".local" / "goals" / job["goal_id"]
    assert job["preparation_state"] == "pending" and not goal.exists()
    monkeypatch.setenv("LAB_COLLECTION_COMMAND", "")
    result = run_collection_attempt(library, job["id"])
    assert result["preparation_state"] == "ready"
    assert result["status"] == "blocked"
    assert (goal / "baseline.json").is_file() and (goal / "goal.json").is_file()


@pytest.mark.parametrize("mode", ["verified", "search"])
def test_direct_attempt_cannot_bypass_baseline_preparation(library, project, mode):
    job = collection_job(library, project, mode=mode)
    running = library.start_collection_attempt(job["id"], job["revision"], "direct-attempt")
    assert running["preparation_state"] == "ready"
    goal = Path(service.__file__).parents[1] / ".local" / "goals" / job["goal_id"]
    assert (goal / "baseline.json").is_file()

    other = collection_job(library, project, mode=mode)
    preparing, _ = library.begin_job_preparation(other["id"], "other-preparation", {})
    with pytest.raises(service.Problem, match="历史基线仍在后台准备"):
        library.start_collection_attempt(other["id"], preparing["revision"], "cannot-start")
    assert not library.job(other["id"]).get("active_attempt_id")


def test_retry_failed_search_advances_collector_generation_without_adding_time(library, project):
    job = collection_job(library, project)
    first = library.start_collection_attempt(job["id"], job["revision"], "first", timeout=900)
    failed = library.update_search_stage(job["id"], "first", "blocked",
        {"stop_reason":"command_timeout", "counts":{"found":0}}, "synthetic window creation timeout")
    elapsed, budget = failed["search_elapsed_seconds"], failed["search_timeout_seconds"]
    retried = library.start_collection_attempt(job["id"], failed["revision"], "retry", timeout=900)
    assert retried["id"] == first["id"]
    assert retried["search_resume_generation"] == failed.get("search_resume_generation", 0) + 1
    assert retried["search_elapsed_seconds"] == elapsed
    assert retried["search_timeout_seconds"] == budget
    assert retried["target_count"] == first["target_count"]
