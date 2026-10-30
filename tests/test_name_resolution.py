from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import threading

import pytest

from ref_lab.name_resolution import NameDiscovery, apply_name_resolution, name_query, resolve_names
from ref_lab.verified_collection import (AgentCallFailed, deterministic_plan, parse_agent_stream,
                                         query_steps)


PROJECT = {"character": "妮可", "work": "普通作品甲"}


class FakeAgent:
    producer = "synthetic-name-agent"

    def __init__(self, discovery=None, *, error=None, started=None, release=None, expected_query=None):
        self.discovery = discovery
        self.error = error
        self.started = started
        self.release = release
        self.expected_query = expected_query or name_query(PROJECT)
        self.last_tool_calls = []
        self.calls = []

    def run(self, prompt, result_type, image_path=None, *, search_query=None):
        assert result_type is NameDiscovery
        assert image_path is None
        assert search_query == self.expected_query
        self.calls.append({"prompt": prompt, "search_query": search_query})
        self.last_tool_calls = [
            {"tool": "search_web", "state": "ACTIVE", "query": search_query},
            {"tool": "search_web", "state": "DONE", "query": search_query},
            {"tool": "finish", "state": "DONE", "query": ""},
        ]
        if self.started:
            self.started.set()
        if self.release:
            assert self.release.wait(2)
        if self.error:
            raise self.error
        return result_type.model_validate(self.discovery)


def resolved_discovery():
    return {
        "status": "resolved",
        "names": [
            {"name": "妮可", "language": "zh", "kind": "character",
             "source_urls": ["https://example.org/nicole"], "evidence": "搜索结果标题使用该中文名"},
            {"name": "ニコ", "language": "ja", "kind": "character",
             "source_urls": ["https://example.net/nicole-ja"], "evidence": "日文结果标题使用该写法"},
            {"name": "Nicole Example", "language": "en", "kind": "character",
             "source_urls": ["https://example.com/nicole-en"], "evidence": "英文结果标题使用该全名"},
            {"name": "Example Work", "language": "en", "kind": "work",
             "source_urls": ["https://example.com/work"], "evidence": "结果标题给出作品英文名"},
        ],
        "source_urls": ["https://example.org/search-result"],
        "reason": "搜索结果中的三种语言名称明确关联同一角色与作品。",
    }


def test_resolved_names_use_producer_schema_are_cached_and_feed_query_steps(tmp_path):
    agent = FakeAgent(resolved_discovery())
    result = resolve_names(PROJECT, agent, tmp_path / "names")
    assert result.status == "resolved" and not result.cached
    assert {candidate.language for candidate in result.names} == {"zh", "ja", "en"}
    assert result.source_kind == "web_search_results" and result.page_reads is False
    assert result.tool_calls == [
        {"tool": row["tool"], "state": row["state"], **({"query": row["query"]} if row["query"] else {})}
        for row in agent.last_tool_calls
    ]
    assert not (tmp_path / "names" / "page.html").exists()
    assert NameDiscovery.model_json_schema()["additionalProperties"] is False

    plan = deterministic_plan(PROJECT)
    merged = apply_name_resolution(plan, result)
    steps = query_steps(PROJECT, merged, ["xiaohongshu", "pinterest"])
    assert any(step["used_name"] == "ニコ" for step in steps)
    assert any(step["used_name"] == "Nicole Example" for step in steps)
    assert next(step for step in steps if step["used_name"] == "ニコ")["alias_origin"] == "web_search_name_alias"
    assert plan.name_records == deterministic_plan(PROJECT).name_records

    second = FakeAgent(error=AssertionError("cache should avoid a second run"))
    cached = resolve_names(PROJECT, second, tmp_path / "names")
    assert cached.cached and cached.status == "resolved" and second.calls == []


def test_cache_is_isolated_by_character_and_work(tmp_path):
    first = FakeAgent(resolved_discovery())
    resolve_names(PROJECT, first, tmp_path)
    other = {**PROJECT, "work": "普通作品乙"}
    second = FakeAgent(resolved_discovery(), expected_query=name_query(other))
    resolve_names(other, second, tmp_path)
    other_character = {**PROJECT, "character": "另一角色"}
    third = FakeAgent(resolved_discovery(), expected_query=name_query(other_character))
    resolve_names(other_character, third, tmp_path)
    assert len(first.calls) == len(second.calls) == len(third.calls) == 1
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_search_call_evidence_is_required_for_self_reported_sources(tmp_path):
    class NoToolEvidence(FakeAgent):
        def run(self, prompt, result_type, image_path=None, *, search_query=None):
            self.calls.append({"prompt": prompt, "search_query": search_query})
            self.last_tool_calls = []
            return result_type.model_validate(self.discovery)

    result = resolve_names(PROJECT, NoToolEvidence(resolved_discovery()), tmp_path)
    assert result.status == "invalid_evidence"
    assert result.names == [] and not list(tmp_path.glob("*.json"))

    unbacked = resolved_discovery()
    unbacked["names"][0]["source_urls"] = []
    result = resolve_names(PROJECT, FakeAgent(unbacked), tmp_path / "unbacked")
    assert result.status == "invalid_evidence" and result.names == []


def test_ambiguous_or_missing_results_reject_aliases_and_preserve_original_plan(tmp_path):
    plan = deterministic_plan(PROJECT)
    before = plan.model_dump()
    for status in ("source_missing", "ambiguous"):
        discovery = {"status": status, "names": [], "source_urls": [], "reason": "同名来源存在多个角色"}
        if status == "ambiguous":
            discovery["source_urls"] = ["https://example.org/a", "https://example.net/b"]
        result = resolve_names(PROJECT, FakeAgent(discovery), tmp_path / status)
        assert result.status == status
        assert apply_name_resolution(plan, result).model_dump() == before


@pytest.mark.parametrize("status", ["source_missing", "ambiguous"])
def test_unresolved_names_are_retried_on_the_next_call(tmp_path, status):
    discovery = {"status": status, "names": [], "source_urls": [], "reason": "本轮没有可复用名称"}
    if status == "ambiguous":
        discovery["source_urls"] = ["https://example.org/a", "https://example.net/b"]
    first = FakeAgent(discovery)
    result = resolve_names(PROJECT, first, tmp_path)
    assert result.status == status and not list(tmp_path.glob("*.json"))

    second = FakeAgent(resolved_discovery())
    result = resolve_names(PROJECT, second, tmp_path)
    assert result.status == "resolved" and not result.cached
    assert len(first.calls) == len(second.calls) == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_timeout_and_agent_error_are_explicit_and_not_cached(tmp_path):
    for category, expected in (("timeout", "timeout"), ("authentication", "error")):
        folder = tmp_path / category
        result = resolve_names(PROJECT, FakeAgent(error=AgentCallFailed(category, fatal=True)), folder)
        assert result.status == expected
        assert result.names == [] and not list(folder.glob("*.json"))


def test_async_resolution_does_not_block_an_original_name_query(tmp_path):
    started, release = threading.Event(), threading.Event()
    project = {**PROJECT, "work": "普通作品异步"}
    plan = deterministic_plan(project)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(resolve_names, project, FakeAgent(
            resolved_discovery(), started=started, release=release,
            expected_query=name_query(project)), tmp_path)
        assert started.wait(2)
        initial = query_steps(project, plan, ["xiaohongshu"])
        assert initial and all(step["used_name"] == project["character"] for step in initial[:1])
        release.set()
        result = future.result(timeout=2)
    assert result.status == "resolved"


def test_parse_agent_stream_accepts_the_name_discovery_schema():
    value = NameDiscovery.model_validate(resolved_discovery())
    final = {"event": "result", "result": {"status": "SUCCESS", "structured_output": value.model_dump()}}
    assert parse_agent_stream(json.dumps(final, ensure_ascii=False), NameDiscovery) == value
