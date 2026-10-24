"""Regressions for continuing an already-finished quick search.

The failure shape is the real checkpoint left by a completed quick search: every
planned query is marked done and ``search_complete`` is true. The user then asks
for more images on the *same* job. No live browser here; the Browser stand-in
only models stable page identities and a platform that can return new cards.

These tests fail on the pre-fix code because:

* ``collect`` rebinds ``state['searches']`` while the loop keeps using the old
  local dict, so the checkpoint written next restores every ``done=True``; and
* the ``--search-only`` CLI exits immediately when an old terminal
  ``search-summary.json`` exists, so a continued job never reaches the collector.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from ref_lab import collection_queue
from ref_lab.collection_checkpoint import rule_contract
from tools import collect_verified as worker

PROJECT = {"character": "西木野真姬", "work": "Love Live!", "costume": "", "brief": ""}
PROJECT_ID = "continue-regression-project"
JOB_ID = "continue-regression"


def _photo(folder: Path, seed: int, page_url: str) -> dict:
    path = folder / "images" / f"continue-{seed}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    from tests.test_collage_split import _textured
    _textured((800,600),seed,(40+seed*7,90,150)).save(path,format="PNG")
    raw = path.read_bytes()
    row = {"asset_sha": hashlib.sha256(raw).hexdigest(), "original_path": str(path.resolve()),
            "page_url": page_url, "image_url": f"https://i.pinimg.com/736x/continue-{seed}.jpg",
            "source_text": "西木野真姬 cosplay 摄影", "width": 800, "height": 600}
    from tests.photo_type_fixture import synthetic_type
    synthetic_type(folder,row)  # Explicit mocked type evidence, not visual accuracy.
    return row


class Browser:
    """Returns one name-hit card per executed query; page identity is per call."""

    def __init__(self, folder: Path, start: int = 0):
        self.folder = folder
        self.executed: list[tuple[str, str]] = []
        self.sequence = start
        self.page_base = start

    def start(self):
        pass

    def close(self):
        pass

    def search(self, step):
        self.executed.append((step["source"], step["query"]))
        index = self.page_base + len(self.executed)
        return {"url": "https://www.pinterest.com/search/pins/?q=" + quote(step["query"]),
                "search": step["query"], "visibleMain": "", "login_required": False,
                "challenge": False,
                "cards": [{"page": f"https://www.pinterest.com/pin/continue-{index}/",
                           "text": "西木野真姬 cosplay 摄影"}]}

    def more(self, step):
        # A bounded second window with no additional pins; the query is still
        # observed and the pass is closed normally.
        return {"url": "https://www.pinterest.com/search/pins/?q=" + quote(step["query"]),
                "search": step["query"], "visibleMain": "", "login_required": False,
                "challenge": False, "cards": []}

    def receive(self, card, step):
        self.sequence += 1
        return [_photo(self.folder, self.sequence, card["page"])]


class Agent:
    producer = "synthetic-continue-recovery"
    model = "synthetic"
    candidate_calls = 0
    vision_cli_calls = 0
    references = []
    deadline = float("inf")

    def __init__(self):
        self.candidate_limit = 40

    def plan(self, project):
        raise AssertionError("search-only must not call the name model")

    def prepare(self, project, plan):
        raise AssertionError("search-only must not prepare references")

    def review(self, path, project):
        raise AssertionError("search-only must not call vision")


def _job(extra: int = 0, target: int = 4) -> dict:
    # Collection jobs carry a verifiable project identity; the duplicate
    # history scope refuses whole-library fallbacks without one.
    return {"id": JOB_ID, "project_id": PROJECT_ID,
            "project_snapshot": {**PROJECT, "id": PROJECT_ID}, "target_count": target,
            "preferred_sources": ["pinterest"], "notes": "", "search_extra_target": extra}


def _outcome(folder: Path):
    return json.loads((folder / "collector-state.json").read_text("utf8"))


def _received(folder: Path) -> list[dict]:
    return json.loads((folder / "received.json").read_text("utf8"))


def test_continue_after_every_query_finished_executes_new_queries_and_keeps_old_originals(tmp_path):
    first_browser = Browser(tmp_path)
    first, _ = worker.collect(_job(extra=0, target=4), Agent(), first_browser, tmp_path, search_only=True)
    assert first["status"] == "completed" and first["target_reached"] is True
    assert first["counts"]["found"] == 4
    before = _outcome(tmp_path)
    steps = before["steps"]
    assert before["search_complete"] is True
    assert set(before["searches"]) == {str(index) for index in range(len(steps))}
    assert any(search.get("done") for search in before["searches"].values())
    old_rows = _received(tmp_path)
    assert len(old_rows) == 4
    original_bytes = {row["asset_sha"]: Path(row["original_path"]).read_bytes() for row in old_rows}
    human = {"version": 1, "items": {old_rows[0]["asset_sha"]: {
        "decision": "keep", "asset_sha": old_rows[0]["asset_sha"], "actor": "human"}}}
    collection_queue.write_json(collection_queue.decide_path(tmp_path), human)
    first_details = before["details"]
    first_windows = before["windows"]

    # A fresh process (new Agent/Browser) resumes the same job after the user
    # asked for four more images. This is the restart shape, not a new job.
    second_browser = Browser(tmp_path, start=4)
    second, _ = worker.collect(_job(extra=4, target=4), Agent(), second_browser, tmp_path, search_only=True)

    assert len(second_browser.executed) > 0, "continue search must actually query the browser"
    executed = set(second_browser.executed)
    assert executed == {(step["source"], step["query"]) for step in steps}
    assert second["status"] == "completed" and second["target_reached"] is True
    assert second["counts"]["found"] == 8
    assert second["counts"]["target_confirmed"] == 8

    after = _outcome(tmp_path)
    rows = _received(tmp_path)
    assert len(rows) == 8
    assert len({row["asset_sha"] for row in rows}) == 8
    assert {row["asset_sha"] for row in rows[:4]} == set(original_bytes)
    for row in rows[:4]:
        assert Path(row["original_path"]).read_bytes() == original_bytes[row["asset_sha"]]
    assert json.loads(collection_queue.decide_path(tmp_path).read_text("utf8")) == human

    # Cumulative counters are kept, never silently zeroed by the new attempt.
    assert after["details"] == first_details + 4
    assert after["windows"] >= first_windows + 4
    assert len(after["queries"]) >= len(steps)
    assert after["elapsed_seconds_total"] >= before["elapsed_seconds_total"]
    assert second["cumulative_elapsed_seconds"] >= second["elapsed_seconds"] > 0
    assert second["continue"]["extra_target"] == 4
    assert second["continue"]["confirmed_at_start"] == 4


def test_continue_reports_exhausted_detail_budget_instead_of_claiming_success(tmp_path):
    first_browser = Browser(tmp_path)
    first, _ = worker.collect(_job(extra=0, target=1), Agent(), first_browser, tmp_path, search_only=True)
    assert first["status"] == "completed" and len(_received(tmp_path)) == 1
    state = _outcome(tmp_path)
    state["details"] = worker.MAX_DETAIL_PAGES
    (tmp_path / "collector-state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf8")
    old_raw = Path(_received(tmp_path)[0]["original_path"]).read_bytes()

    second_browser = Browser(tmp_path)
    second, _ = worker.collect(_job(extra=1, target=1), Agent(), second_browser, tmp_path, search_only=True)

    assert second_browser.executed == [], "an exhausted budget must not pretend to search"
    assert second["status"] == "partial" and second["target_reached"] is False
    assert second["stop_reason"] == "detail_budget_exhausted"
    assert second["counts"]["found"] == 1
    assert second["continue"]["blocked_by"] == "detail_budget_exhausted"
    assert Path(_received(tmp_path)[0]["original_path"]).read_bytes() == old_raw


def _seed_cli_run(root: Path) -> Path:
    run = root / ".local" / "collection-runs" / JOB_ID / "current"
    run.mkdir(parents=True)
    browser = Browser(run)
    first, _ = worker.collect(_job(extra=0, target=1), Agent(), browser, run, search_only=True)
    assert first["status"] == "completed" and len(_received(run)) == 1
    task_dir = root / "task"
    task_dir.mkdir()
    (task_dir / "AGENT_TASK.md").write_text("synthetic continue task", encoding="utf8")
    job = _job(extra=1, target=1)
    (task_dir / "job.json").write_text(json.dumps({"schema_version": 2, "job": job}), encoding="utf8")
    return run


def test_search_only_cli_continues_instead_of_exiting_on_the_old_summary(tmp_path, monkeypatch):
    root = tmp_path / "cli-root"
    run = _seed_cli_run(root)
    browser = Browser(run, start=1)

    class CliAgent(Agent):
        def __init__(self, *args, **kwargs):
            assert kwargs.get("runtime_budget") is False

    class History:
        records: dict = {}
        initial_count = 0
        known_count = 0
        ready = True
        errors: list = []

        def consider(self, path, **kwargs):
            return None

        def close(self, **kwargs):
            pass

    monkeypatch.setattr(worker, "ROOT", root)
    monkeypatch.setattr(worker, "AntigravityCollectionAgent", CliAgent)
    monkeypatch.setattr(worker, "Browser", lambda folder: browser)
    monkeypatch.setattr(worker, "_history_for_search", lambda folder, project_id: History())
    monkeypatch.setattr(worker, "_write_run_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker.sys, "argv", ["collect_verified.py", str(root / "task" / "AGENT_TASK.md"),
                                             str(run / "result.zip"), "--search-only"])
    worker.main()

    summary = json.loads((run / "search-summary.json").read_text("utf8"))
    assert summary["status"] == "completed" and summary["target_reached"] is True
    assert summary["counts"]["found"] == 2, "the CLI must not exit on the previous terminal summary"
    assert browser.executed, "continued CLI run must execute real searches"
    archived = list(run.glob("search-summary-previous-*.json"))
    assert len(archived) == 1
    assert json.loads(archived[0].read_text("utf8"))["counts"]["found"] == 1


def test_task_package_is_refreshed_with_the_pending_extra_target(tmp_path, monkeypatch, library, client, project):
    from ref_lab import collection_stages
    from ref_lab.models import JobInput

    monkeypatch.setattr(collection_queue, "run_directory", lambda job_id: tmp_path / "q")
    job = library.create_job(project["id"], JobInput(kind="collection", collection_mode="search",
                                                     target_count=4, notes="synthetic continue package"))
    folder, task_dir, task_file = collection_stages._artifacts(library, job["id"])
    assert folder == tmp_path / "q"
    first = json.loads((task_dir / "job.json").read_text("utf8"))["job"]
    assert first.get("search_extra_target") in (None, 0)
    library.extend_search(job["id"], 6)
    collection_stages._artifacts(library, job["id"])
    refreshed = json.loads((task_dir / "job.json").read_text("utf8"))["job"]
    assert refreshed["search_extra_target"] == 6
    assert refreshed["target_count"] == 4
    assert refreshed["project_snapshot"]["character"] == project["character"]
    assert rule_contract()  # binding inputs remain computable from the same branch
