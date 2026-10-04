"""Deterministic transport counterexamples; fixtures do not prove visual accuracy."""
import io
import json
import zipfile

import pytest
from PIL import Image

from ref_lab.models import CandidatePackage
from ref_lab.identity import build_identity_context
from ref_lab.preflight import detect_modality, evaluate_identity, evaluate_quality, run_candidate_preflight
from tools import collect_adapter as adapter
from conftest import image_bytes


@pytest.mark.parametrize("notes", ["只找竖图", "不要竖图，要横图", "非cos普通人像", "不限角色，找可迁移动作"])
def test_free_text_is_discovery_context_not_a_hard_specification(notes):
    project = {"character": "王昭君", "costume": "长夜焕生", "work": "王者荣耀"}
    baseline = adapter.build_policy({"project_snapshot": project})
    policy = adapter.build_policy({"project_snapshot": project, "notes": notes})
    fields = ("require_cosplay", "require_character", "require_costume", "portrait_only")
    assert {k: policy[k] for k in fields} == {k: baseline[k] for k in fields}
    assert policy["notes"] == notes
    assert baseline["require_character"] and baseline["require_costume"]
    assert any(notes in query for query in adapter.build_queries({"project_snapshot": project, "notes": notes}, for_browser=True))


@pytest.mark.parametrize("color", [(180, 40, 40), (30, 40, 180)])
def test_color_rectangles_cannot_establish_character_identity(color):
    image = Image.new("RGB", (600, 800), color)
    out = io.BytesIO()
    image.save(out, "PNG")
    result = evaluate_identity(out.getvalue(), {"title": "有马加奈 cos正片"}, build_identity_context("有马加奈"))
    assert result["prediction"] == "uncertain" and result["confidence"] == "low"


def test_metadata_does_not_become_visual_evidence():
    image = Image.open(io.BytesIO(image_bytes()))
    assert detect_modality(image, {"title": "布光图 游戏截图"}) == ("unknown", [])
    pf = run_candidate_preflight(image_bytes(), {"title": "商品展示"}, None, "a" * 64, "test-project")
    assert pf["content_type"] == "unknown" and pf["visual_evidence"] == []
    assert pf["discovery_context"]["photographic_fact"] is False
    assert "商品展示" in pf["discovery_context"]["filter_terms"]
    assert pf["status"] == "uncertain"


def test_pixel_measurements_do_not_invent_people_or_readable_pose():
    result = evaluate_quality(image_bytes())
    assert result["is_single_person"] is None and result["pose_readable"] is None
    assert result["is_equipment_or_scene"] is None
    assert result["width"] == 800 and result["height"] == 1200


def test_uniform_background_is_a_hint_not_a_visual_collage_or_blur():
    image = Image.new("RGB", (600, 800), "white")
    out = io.BytesIO()
    image.save(out, "PNG")
    result = evaluate_quality(out.getvalue())
    assert result["passed"]
    assert result["is_collage"] is None and result["is_blurry_or_lowres"] is None


def run_adapter(monkeypatch, tmp_path, *, sources, candidates, query_log, login_wall, target_count=30, images=None):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    job = {"id": "synthetic-job", "project_snapshot": {"character": "test"}, "target_count": target_count, "preferred_sources": sources}
    (task_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
    result_file = tmp_path / "result.zip"
    monkeypatch.setattr(adapter, "parse_arguments", lambda: (task_dir, result_file, False))
    monkeypatch.setattr(adapter, "select_browserskill", lambda env: ("synthetic-bsk", "browser"))
    monkeypatch.setattr(adapter, "fetch_bsk_candidates", lambda *args: (candidates, images or {}, query_log, login_wall))
    adapter.main()
    with zipfile.ZipFile(result_file) as archive:
        return json.loads(archive.read("manifest.json"))


def test_one_completed_preferred_source_preserves_another_source_block(monkeypatch, tmp_path):
    raw = image_bytes()
    result = run_adapter(
        monkeypatch, tmp_path, sources=["xiaohongshu", "pinterest"],
        candidates=[{"id": "fixture", "file": "images/fixture.png"}],
        images={"fixture.png": raw},
        query_log=[
            {"source": "xiaohongshu", "query": "fixture", "kept": 0, "stop_reason": "login_required"},
            {"source": "pinterest", "query": "fixture", "kept": 1, "stop_reason": "kept=1"},
        ],
        login_wall=True,
    )
    CandidatePackage.model_validate(result)
    with zipfile.ZipFile(tmp_path / "result.zip") as archive:
        assert archive.read("images/fixture.png") == raw
    report = result["execution_report"]
    assert report["status"] == "completed"
    assert {check["source"]: check["status"] for check in report["source_checks"]} == {
        "xiaohongshu": "blocked", "pinterest": "usable",
    }
    assert any("xiaohongshu:" in gap for gap in report["gaps"])
    assert any("1 / 30" in gap for gap in report["gaps"])


def test_attempted_zero_yield_source_is_not_reported_untested(monkeypatch, tmp_path):
    result = run_adapter(monkeypatch, tmp_path, sources=["pinterest"], candidates=[], query_log=[{"source": "pinterest", "query": "fixture", "kept": 0, "stop_reason": "kept=0"}], login_wall=False)
    check = next(x for x in result["execution_report"]["source_checks"] if x["source"] == "pinterest")
    assert check["status"] == "usable"
    assert result["execution_report"]["status"] == "blocked"
    assert result["execution_report"]["gaps"]


def test_unsupported_explicit_source_is_blocked_without_silent_substitution(monkeypatch, tmp_path):
    result = run_adapter(monkeypatch, tmp_path, sources=["instagram"], candidates=[{"id": "fixture"}], query_log=[{"source": "xiaohongshu", "query": "fixture", "kept": 1, "stop_reason": "kept=1"}], login_wall=False)
    assert result["execution_report"]["status"] == "blocked"
    assert any(x["source"] == "instagram" and x["status"] == "unavailable" for x in result["execution_report"]["source_checks"])


def test_explicit_source_order_controls_browser_navigation(monkeypatch):
    visited = []
    def run(command, **kwargs):
        if command[1:3] == ["session", "start"]:
            return type("Result", (), {"stdout": json.dumps({"session_id": "synthetic-session"})})()
        if command[1] == "navigate":
            visited.append(command[2])
        return type("Result", (), {"stdout": "{}"})()
    monkeypatch.setattr(adapter.subprocess, "run", run)
    monkeypatch.setattr(adapter.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(adapter, "wait_for_cards", lambda *args: ([], False))
    job = {"project_snapshot": {"character": "test"}, "preferred_sources": ["pinterest", "xiaohongshu"]}
    _, _, query_log, _ = adapter.fetch_bsk_candidates("synthetic-bsk", "synthetic-browser", job, 1, adapter.build_policy(job))
    assert "pinterest.com" in visited[0]
    assert [entry["source"] for entry in query_log] == ["pinterest"] * 4 + ["xiaohongshu"] * 4
    visited.clear()
    job["preferred_sources"] = ["pinterest"]
    adapter.fetch_bsk_candidates("synthetic-bsk", "synthetic-browser", job, 1, adapter.build_policy(job))
    assert visited and all("pinterest.com" in url for url in visited)


def test_session_start_failure_keeps_transport_contract(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("synthetic session failure")
    monkeypatch.setattr(adapter.subprocess, "run", fail)
    assert adapter.fetch_bsk_candidates("synthetic-bsk", "synthetic-browser", {}, 1, {}) == ([], {}, [], False)


def test_satisfied_request_can_complete_without_visual_claims(monkeypatch, tmp_path):
    manifest = run_adapter(monkeypatch, tmp_path, sources=["pinterest"],
                           candidates=[{"id": "partial"}],
                           query_log=[{"source": "pinterest", "query": "test", "kept": 1}],
                           login_wall=False, target_count=1)
    assert manifest["schema_version"] == 2
    assert manifest["execution_report"]["status"] == "completed"
    assert manifest["execution_report"]["gaps"] == []
    assert "preflight" not in manifest["candidates"][0]


def test_empty_source_selection_does_not_invoke_browser(monkeypatch, tmp_path):
    def unexpected(*args, **kwargs):
        pytest.fail("An empty source selection must not probe or acquire from a browser")
    manifest = run_adapter(monkeypatch, tmp_path, sources=[], candidates=[], query_log=[], login_wall=False)
    assert manifest["candidates"] == []
    assert manifest["execution_report"]["status"] == "blocked"
    monkeypatch.setattr(adapter, "select_browserskill", unexpected)
    adapter.main()


def test_invalid_file_is_filtered_without_inventing_visual_failure():
    quality = evaluate_quality(b"not an image")
    assert quality["passed"] is False
    assert quality["pose_readable"] is None
    assert quality["is_single_person"] is None
    assert quality["is_collage"] is None
    preflight = run_candidate_preflight(b"not an image", {}, None, "b" * 64, "test-project")
    assert preflight["status"] == "filtered"
    assert preflight["content_type"] == "unknown"
    assert preflight["visual_evidence"] == []


def test_soft_quantity_gap_does_not_block_a_completed_source_run(monkeypatch, tmp_path):
    manifest = run_adapter(
        monkeypatch, tmp_path, sources=["pinterest"],
        candidates=[{"id": "one-current-candidate"}],
        query_log=[{"source": "pinterest", "query": "test", "kept": 1}],
        login_wall=False, target_count=60,
    )
    report = manifest["execution_report"]
    assert report["source_checks"][0]["status"] == "usable"
    assert report["status"] == "completed"
    assert any("1 / 60" in gap for gap in report["gaps"])
    assert "preflight" not in manifest["candidates"][0]


def test_unused_preferred_source_reports_execution_budget_not_requested_goal(monkeypatch, tmp_path):
    manifest = run_adapter(
        monkeypatch, tmp_path, sources=["xiaohongshu", "pinterest"],
        candidates=[{"id": str(index)} for index in range(40)],
        query_log=[{"source": "xiaohongshu", "query": "fixture", "kept": 40}],
        login_wall=False, target_count=60,
    )
    report = manifest["execution_report"]
    untested = next(check for check in report["source_checks"] if check["source"] == "pinterest")
    assert report["status"] == "completed"
    assert untested["status"] == "untested"
    assert "执行预算" in untested["detail"]
    assert "数量目标" not in untested["detail"]
    assert any("40 / 60" in gap for gap in report["gaps"])
    assert any("pinterest:" in gap for gap in report["gaps"])


def test_all_preferred_sources_blocked_keep_assets_without_completing(monkeypatch, tmp_path):
    manifest = run_adapter(
        monkeypatch, tmp_path, sources=["xiaohongshu"],
        candidates=[{"id": "earlier-current-candidate"}],
        query_log=[{"source": "xiaohongshu", "query": "fixture", "kept": 1}],
        login_wall=True,
    )
    assert len(manifest["candidates"]) == 1
    assert manifest["execution_report"]["status"] == "blocked"
    assert manifest["execution_report"]["source_checks"][0]["status"] == "blocked"


def test_unavailable_secondary_preference_does_not_block_a_usable_source(monkeypatch, tmp_path):
    manifest = run_adapter(
        monkeypatch, tmp_path, sources=["instagram", "pinterest"],
        candidates=[{"id": "current-candidate"}],
        query_log=[{"source": "pinterest", "query": "fixture", "kept": 1}],
        login_wall=False,
    )
    report = manifest["execution_report"]
    assert report["status"] == "completed"
    assert any(check["source"] == "instagram" and check["status"] == "unavailable" for check in report["source_checks"])
    assert any("instagram:" in gap for gap in report["gaps"])
