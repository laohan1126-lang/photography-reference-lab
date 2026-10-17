"""Explicit task-scoped query plans must survive multilingual discovery."""
import pytest

from tools.collect_adapter import build_policy, build_queries


def test_declared_multilingual_plan_preserves_scope_and_query_order():
    scope = {"character": "托尔", "costume": "婚纱", "work": "小林家的龙女仆"}
    job = {"project_snapshot": scope, "query_plan": {"scope": scope, "queries": [
        "Tohru wedding cosplay", "トール 花嫁 コスプレ", "托尔 婚纱 cos"
    ]}}
    assert build_queries(job, for_browser=True) == job["query_plan"]["queries"]
    assert build_policy(job)["require_costume"] is True
    assert build_policy(job)["costume"] == "婚纱"


def test_generic_plan_not_character_specific_and_rejects_stale_scope():
    scope = {"character": "Example", "costume": "Ceremony", "work": "Test"}
    job = {"project_snapshot": scope, "query_plan": {"scope": scope, "queries": ["Example 礼服 写真"]}}
    assert build_queries(job, True) == ["Example 礼服 写真"]
    job["project_snapshot"] = {**scope, "costume": "School"}
    with pytest.raises(ValueError, match="scope"):
        build_queries(job, True)


@pytest.mark.parametrize("queries", [[], "text", [""], ["x"] * 9, [123]])
def test_explicit_plan_has_bounded_valid_queries(queries):
    scope = {"character": "A", "costume": "", "work": "B"}
    with pytest.raises(ValueError, match="query"):
        build_queries({"project_snapshot": scope, "query_plan": {"scope": scope, "queries": queries}}, True)


def test_ordinary_jobs_keep_existing_queries():
    job = {"project_snapshot": {"character": "A", "costume": "C", "work": "B"}}
    assert build_queries(job, True) == ["B A C cosplay 正片", "B A C coser 摄影", "B A C cos 返图", "B A C cos 场照"]
