from __future__ import annotations

import json
from pathlib import Path
import threading
from urllib.parse import quote

import pytest

from ref_lab.name_resolution import NameDiscovery
from ref_lab.verified_collection import AgentCallFailed
from tools import collect_verified as worker


PROJECT = {"id": "name-enrichment-project", "character": "慢查角色", "work": "测试作品",
           "costume": "", "brief": ""}


def job() -> dict:
    return {"id": "name-enrichment-job", "project_id": PROJECT["id"],
            "project_snapshot": PROJECT, "target_count": 1,
            "preferred_sources": ["pinterest"], "notes": ""}


def discovery(*, status="resolved"):
    names = [] if status != "resolved" else [{
        "name": "Slow Alias", "language": "en", "kind": "character",
        "source_urls": ["https://example.org/slow-alias"],
        "evidence": "搜索结果标题使用该英文名",
    }]
    return {"status": status, "names": names,
            "source_urls": ["https://example.org/name-result"],
            "reason": "synthetic name-search result"}


class NameAgent:
    producer = "synthetic-name-agent"

    def __init__(self, *, result=None, block=False, cancel_wait=False):
        self.result = result or discovery()
        self.block = block
        self.cancel_wait = cancel_wait
        self.started = threading.Event()
        self.finished = threading.Event()
        self.release = threading.Event()
        self.cancelled = threading.Event()
        self.calls = []
        self.last_tool_calls = []

    def run(self, prompt, result_type, image_path=None, *, search_query=None):
        self.calls.append(search_query)
        self.last_tool_calls = [
            {"tool": "search_web", "state": "ACTIVE", "query": search_query},
            {"tool": "search_web", "state": "DONE", "query": search_query},
            {"tool": "finish", "state": "DONE", "query": ""},
        ]
        self.started.set()
        try:
            if self.cancel_wait:
                assert self.cancelled.wait(3)
                raise AgentCallFailed("cancelled", fatal=True)
            if self.block:
                assert self.release.wait(3)
            return result_type.model_validate(self.result)
        finally:
            self.finished.set()


class Agent:
    producer = "synthetic-collector-agent"
    model = "synthetic"
    candidate_calls = 0
    vision_cli_calls = 0
    references = []
    deadline = float("inf")

    def __init__(self, name_agent=None):
        self.candidate_limit = 40
        self.name_agent = name_agent
        self.name_calls = 0

    def name_agent_factory(self):
        self.name_calls += 1
        if self.name_agent is None:
            raise AssertionError("name resolution must not run again on resume")
        return self.name_agent

    def plan(self, project):
        raise AssertionError("search-only must not call the vision name planner")

    def prepare(self, project, plan):
        raise AssertionError("search-only must not prepare references")

    def review(self, path, project):
        raise AssertionError("search-only must not review images")


class Browser:
    def __init__(self, *, release=None, interrupt_on=None):
        self.executed = []
        self.release = release
        self.interrupt_on = interrupt_on

    def start(self):
        pass

    def close(self):
        pass

    def search(self, step):
        self.executed.append((step["source"], step["query"], step.get("used_name")))
        if len(self.executed) == self.interrupt_on:
            raise KeyboardInterrupt
        if self.release is not None and len(self.executed) == 1:
            self.release.set()
        return {"url": "https://www.pinterest.com/search/pins/?q=" + quote(step["query"]),
                "search": step["query"], "visibleMain": "", "cards": [],
                "login_required": False, "challenge": False, "body_ready": True}


def state(folder: Path) -> dict:
    return json.loads((folder / "collector-state.json").read_text("utf8"))


def test_slow_name_lookup_does_not_block_first_search_and_runs_after_completion(tmp_path):
    name_agent = NameAgent(block=True)
    browser = Browser(release=name_agent.release)
    summary, _ = worker.collect(job(), Agent(name_agent), browser, tmp_path, search_only=True)

    assert browser.executed[0][2] == PROJECT["character"]
    assert any(row[2] == "Slow Alias" for row in browser.executed[1:]), browser.executed
    assert name_agent.started.is_set() and name_agent.finished.is_set()
    saved = state(tmp_path)
    assert saved["name_enrichment"]["state"] == "resolved"
    assert saved["name_enrichment"]["applied"] is True
    assert saved["name_enrichment"]["resolution"]["source_kind"] == "web_search_results"
    assert saved["name_enrichment"]["resolution"]["page_reads"] is False
    assert json.loads((tmp_path / "name-enrichment.json").read_text("utf8"))["state"] == "resolved"
    assert any(record.get("source") == "web_search_name_alias" for record in saved["plan"]["name_records"])
    assert set(saved["execution_schedule"]) == set(range(len(saved["steps"])))
    assert summary["status"] in {"partial", "blocked", "completed"}


def test_name_failure_keeps_original_queries_without_aliases(tmp_path):
    name_agent = NameAgent(result=discovery(status="source_missing"))
    browser = Browser()
    worker.collect(job(), Agent(name_agent), browser, tmp_path, search_only=True)
    assert browser.executed and browser.executed[0][2] == PROJECT["character"]
    assert all(row[2] != "Slow Alias" for row in browser.executed)
    saved = state(tmp_path)
    assert saved["name_enrichment"]["state"] == "source_missing"
    assert all(record.get("source") != "web_search_name_alias" for record in saved["plan"]["name_records"])


def test_cancel_stops_only_the_owned_name_worker(tmp_path):
    name_agent = NameAgent(cancel_wait=True)
    browser = Browser(interrupt_on=2)
    with pytest.raises(KeyboardInterrupt):
        worker.collect(job(), Agent(name_agent), browser, tmp_path, search_only=True)
    assert name_agent.cancelled.is_set()
    assert name_agent.finished.wait(1)
    saved = state(tmp_path)
    assert saved["outcome"] == "cancelled"
    assert saved["name_enrichment"]["state"] == "cancelled"
    assert json.loads((tmp_path / "name-enrichment.json").read_text("utf8"))["state"] == "cancelled"
    assert saved["name_enrichment"]["applied"] is False


def test_resume_reuses_persisted_names_and_does_not_rerun_name_agent(tmp_path):
    first_name_agent = NameAgent()
    worker.collect(job(), Agent(first_name_agent), Browser(release=None), tmp_path, search_only=True)
    assert len(first_name_agent.calls) == 1
    first_state = state(tmp_path)
    assert first_state["name_enrichment"]["applied"] is True
    assert any(first_state["steps"][index].get("used_name") == "Slow Alias"
               for index in first_state["execution_schedule"])

    resumed_agent = Agent()
    resumed_browser = Browser()
    worker.collect(job(), resumed_agent, resumed_browser, tmp_path, search_only=True)
    assert resumed_agent.name_calls == 0
    resumed_state = state(tmp_path)
    assert resumed_state["execution_schedule"] == first_state["execution_schedule"]
    assert resumed_state["name_enrichment"]["state"] == "resolved"
    assert resumed_state["name_enrichment"]["applied"] is True
    assert any(record.get("name") == "Slow Alias" and record.get("source") == "web_search_name_alias"
               for record in resumed_state["plan"]["name_records"])


def test_name_cache_is_shared_across_jobs_without_repeating_the_lookup(tmp_path):
    first_lookup, second_lookup = NameAgent(), NameAgent()
    for index, lookup in enumerate([first_lookup, second_lookup]):
        folder = tmp_path / str(index)
        folder.mkdir()
        agent = Agent(lookup)
        agent.name_cache_dir = tmp_path / "shared-names"
        request = {**job(), "id": f"cache-job-{index}"}
        worker.collect(request, agent, Browser(), folder, search_only=True)
        assert state(folder)["name_enrichment"]["state"] == "resolved"
    assert len(first_lookup.calls) == 1
    assert second_lookup.calls == []
    assert state(tmp_path / "1")["name_enrichment"]["resolution"]["cached"] is True


def test_candidate_snapshot_exposes_name_lookup_without_model_calls(tmp_path, monkeypatch):
    from ref_lab import collection_queue
    monkeypatch.setattr(collection_queue, "run_directory", lambda _: tmp_path)
    evidence = {"state":"ambiguous", "resolution":{"names":[], "reason":"synthetic conflict"}}
    (tmp_path / "name-enrichment.json").write_text(json.dumps(evidence), encoding="utf8")
    assert collection_queue.snapshot("name-test")["name_lookup"] == evidence
