"""The shared course contract: one format boundary, two shapes, one validator.

Every fixture below is synthetic test data written for this file. None of it is teaching
evidence, none of it describes a real photograph, and a passing check here says nothing
about whether a course reads well or whether anyone has accepted its content.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from tools.render_field_course import export, main as render_main
from tools.validate_learning_gateways import validate_gateways

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research/photography-atlas"
PAGE = "https://field-guide-fixture.example/source-page"

# --- synthetic fixture ---------------------------------------------------------

def tree() -> dict:
    return json.loads((RESEARCH / "SKILL_TREE.json").read_text(encoding="utf-8"))


def skill_ids() -> list[str]:
    skills = tree()["skills"]
    return [s["id"] for s in skills if s["id"].startswith("perspective-")][:2] or [s["id"] for s in skills][:2]


def fixture_content() -> dict:
    """A media registry entry so the fixture case may reuse the existing local-media path."""
    return {"schema_version": 1, "notes": [], "trainings": [],
            "sources": [{"id": "fg-fixture-media-source", "url": PAGE, "title": "合成测试夹具图片来源",
                         "author": "SYNTHETIC FIXTURE AUTHOR", "reading_depth": "仅核对简介",
                         "checked_at": "2026-10-11"}],
            "media": [{"id": "fg-fixture-frame", "source_id": "fg-fixture-media-source",
                       "alt": "合成测试夹具图像描述", "position": "合成夹具位置"}]}


def fixture_case(case_id: str, title: str) -> dict:
    return {"id": case_id, "title": title, "author": "SYNTHETIC FIXTURE AUTHOR",
            "caption": "合成测试夹具图片说明，不代表任何真实案例判断。", "alt": "合成测试夹具图像描述",
            "url": PAGE, "display": "note_media", "images": [{"media_id": "fg-fixture-frame"}],
            "source_summary": {"text": "合成测试夹具转述。", "locator": "合成定位",
                               "source_id": "fg-fixture-source", "checked_at": "2026-10-11"},
            "rights": {"allowed": False, "url": PAGE, "statement": "合成测试夹具：无再分发许可。"},
            "review": {"level": "pixel_reviewed", "checked_at": "2026-10-11",
                       "detail": "合成测试夹具：不代表真实像素复核记录。"}}


def fixture_recipe(block_id: str, **overrides) -> dict:
    block = {"type": "field_recipe", "id": block_id,
             "problem": "合成夹具：低机位让靠近镜头的一侧显得更大。",
             "setup": "合成夹具：同一人物，同一背景，只改机位高度。",
             "instruction": "把相机降到人物膝盖高度再拍一张。",
             "target": {"text": "合成夹具：拍到地面占画面下缘约三分之一时停。",
                        "basis": "visible_marker"},
             "comparison": {"case_ids": ["fg-a", "fg-b"], "relation": "same_session",
                            "conditions": ["合成夹具：同一光线与背景"],
                            "look_for": "合成夹具：比较靠近镜头一侧与另一侧的相对大小。"},
             "check": {"success": "合成夹具：两次的相对大小差异可见。",
                       "if_failed": "合成夹具：把机位再降半步重拍。"},
             "cost": "合成夹具：要多跪一次，且画面下半部留白更多。",
             "why": "合成夹具：因为透视由机位高度决定，所以这是最小的一次变量改动。",
             "source_ids": ["fg-fixture-source"]}
    block.update(overrides)
    return block


def fixture_video(block_id: str = "fg-video", **overrides) -> dict:
    block = {"type": "video_sequence", "id": block_id, "source_id": "fg-video-source",
             "start_seconds": 12.0, "end_seconds": 96.0,
             "inspection": {"method": "continuous_segment", "detail": "合成夹具：连续片段核对记录",
                            "checked_at": "2026-10-11"},
             "steps": [{"start_seconds": 12.0, "end_seconds": 48.0, "stage": "合成夹具步骤一",
                        "summary": "合成夹具：先摆位再压机位。"},
                       {"start_seconds": 48.0, "end_seconds": 96.0, "stage": "合成夹具步骤二",
                        "summary": "合成夹具：保持其他变量不动再拍一次。"}]}
    block.update(overrides)
    return block


def field_course(**overrides) -> dict:
    course = {
        "id": "fg-fixture-course", "kind": "course", "course_format": "field-guide-v1",
        "label": "合成测试夹具课程",
        "title": "合成测试夹具课程", "question": "合成夹具问题？", "outcome": "合成夹具结果说明。",
        "method": "合成夹具方法。", "author": "SYNTHETIC FIXTURE", "reading_depth": "合成测试夹具",
        "prior_knowledge": "合成测试夹具先修说明。",
        "skill_ids": skill_ids(), "source_ids": ["fg-fixture-source", "fg-video-source"],
        "cases": [fixture_case("fg-a", "夹具案例 A"), fixture_case("fg-b", "夹具案例 B")],
        "sections": [
            {"id": "before-you-go", "title": "夹具准备", "blocks": [
                {"type": "paragraph", "text": "合成测试夹具段落。", "source_ids": ["fg-fixture-source"]}]},
            {"id": "operation", "title": "夹具现场操作", "blocks": [fixture_recipe("fg-recipe")]},
            {"id": "watch", "title": "夹具视频顺序", "blocks": [fixture_video()]},
        ],
    }
    course.update(overrides)
    return course


def field_catalog(**overrides) -> dict:
    catalog = {
        "schema_version": 1,
        "sources": [
            {"id": "fg-fixture-source", "url": PAGE, "title": "合成测试夹具出处",
             "author": "SYNTHETIC FIXTURE AUTHOR", "reading_depth": "仅核对简介",
             "checked_at": "2026-10-11", "locator": "合成定位", "support": "只用于验证数据契约",
             "limitation": "不代表任何真实来源结论"},
            {"id": "fg-video-source", "url": "https://field-guide-fixture.example/video/",
             "title": "合成测试夹具视频出处", "author": "SYNTHETIC FIXTURE AUTHOR",
             "reading_depth": "仅核对简介", "checked_at": "2026-10-11", "locator": "合成定位 00:12",
             "support": "只用于验证数据契约", "limitation": "未观看，不代表任何真实来源结论"},
        ],
        "gateways": [field_course()],
    }
    catalog.update(overrides)
    return catalog


def errors(course: dict, catalog: dict | None = None) -> list[str]:
    data = catalog or field_catalog()
    data = {**data, "gateways": [course]}
    return validate_gateways(data, tree(), fixture_content())


def recipe_of(course: dict) -> dict:
    return course["sections"][1]["blocks"][0]


def video_of(course: dict) -> dict:
    return course["sections"][2]["blocks"][0]


# --- the format boundary -------------------------------------------------------

def test_the_field_guide_fixture_is_valid_and_legacy_still_validates_unchanged():
    assert errors(field_course()) == []
    # The untouched chapter contract keeps its own rules; the new format adds no exception
    # keyed by course ID, it is declared per course.
    shipped = json.loads((RESEARCH / "GATEWAYS.json").read_text(encoding="utf-8"))
    content = json.loads((RESEARCH / "LEARNING_CONTENT.json").read_text(encoding="utf-8"))
    legacy_catalog = {**shipped, "gateways": [g for g in shipped['gateways'] if g.get('kind') != 'course']}
    assert validate_gateways(legacy_catalog, tree(), content) == []
    legacy = legacy_catalog['gateways'][0]
    assert "course_format" not in legacy
    assert [s["id"] for s in legacy["sections"]][:2] == ["problem", "observe"]


def test_an_unknown_format_is_invalid_rather_than_read_as_the_old_shape():
    course = field_course(course_format="field-guide-v2")
    assert any("Unknown course format" in e for e in errors(course))
    # Not silently ignored, and not silently upgraded either.
    course = field_course(course_format="legacy-v9")
    assert any("Unknown course format" in e for e in errors(course))
    # A declared-but-empty format is no more a legacy course than a wrong one is.
    assert any("Unknown course format" in e for e in errors(field_course(course_format=None)))
    # Only an absent declaration keeps the chapter contract.
    legacy_shaped = field_course()
    del legacy_shaped["course_format"]
    legacy_shaped["sections"] = [{"id": name, "title": "夹具章节", "blocks": [{"type": "paragraph", "text": "夹具段落。"}]}
                                 for name in ("problem", "observe", "principle", "contrast",
                                              "boundary", "transfer", "reflect", "sources")]
    legacy_errors = errors(legacy_shaped)
    assert not any("Field-guide" in e or "Unknown course format" in e for e in legacy_errors)
    # Its own chapter rules apply unchanged: free section ids are not enough for it.
    assert any("Incomplete observation/contrast/transfer" in e for e in legacy_errors)


def test_field_guide_needs_kind_course_and_no_chapter_or_activity_shape():
    assert any("kind=course" in e for e in errors(field_course(kind="gateway")))
    # Three sections and zero exercises are legal here; the eight-chapter rule does not apply.
    assert errors(field_course(sections=field_course()["sections"][:1])) == []


def test_free_section_ids_must_stay_unique_and_usable_as_element_ids():
    course = field_course()
    duplicate = json.loads(json.dumps(course))
    duplicate["sections"][1]["id"] = duplicate["sections"][0]["id"]
    assert any("section ID" in e for e in errors(duplicate))
    spaced = json.loads(json.dumps(course))
    spaced["sections"][1]["id"] = "operation step"
    assert any("section ID" in e for e in errors(spaced))
    numbered = json.loads(json.dumps(course))
    numbered["sections"][1]["id"] = "02-machine-height"
    assert errors(numbered) == []


# --- field_recipe --------------------------------------------------------------

@pytest.mark.parametrize("field,value", [("problem", ""), ("setup", "  "), ("instruction", None),
                                         ("cost", ""), ("why", 3)])
def test_a_recipe_without_its_operation_parts_is_refused(field, value):
    course = field_course()
    recipe_of(course)[field] = value
    assert any("field recipe" in e for e in errors(course))


@pytest.mark.parametrize("basis", ["", "measured", None, "author_measured"])
def test_an_unnamed_stopping_point_basis_is_refused(basis):
    course = field_course()
    recipe_of(course)["target"] = {"text": "夹具停止点。", "basis": basis}
    assert any("stopping point basis" in e for e in errors(course))


def test_a_measured_stopping_point_needs_a_real_source_reference():
    course = field_course()
    target = recipe_of(course)["target"] = {"text": "夹具停止点。", "basis": "source_measured"}
    assert any("needs a course source" in e for e in errors(course))
    target.update(source_id="fg-fixture-source")
    assert any("locator and conditions" in e for e in errors(course))
    target.update(locator="正文第 3 段")
    assert any("locator and conditions" in e for e in errors(course))
    target["conditions"] = ["合成夹具：同一光线"]
    assert errors(course) == []
    target["source_id"] = "no-such-course-source"
    assert any("needs a course source" in e for e in errors(course))


def test_a_proposed_starting_point_must_say_it_is_proposed():
    course = field_course()
    recipe_of(course)["target"] = {"text": "夹具起点。", "basis": "practice_start"}
    assert any("proposed=true" in e for e in errors(course))
    recipe_of(course)["target"] = {"text": "夹具起点。", "basis": "practice_start",
                                   "proposed": True, "source_id": "fg-fixture-source",
                                   "locator": "正文第 3 段"}
    # It may not borrow measured evidence and pass itself off as the author's number.
    assert any("borrow measured evidence" in e for e in errors(course))


def test_a_visible_stopping_point_carries_no_measured_fields():
    course = field_course()
    recipe_of(course)["target"]["locator"] = "正文第 3 段"
    assert any("may not carry locator" in e for e in errors(course))


def test_recipe_comparison_cases_must_belong_to_this_course():
    course = field_course()
    recipe_of(course)["comparison"]["case_ids"] = ["fg-a", "fg-case-from-another-course"]
    assert any("must belong to this course" in e for e in errors(course))
    recipe_of(course)["comparison"]["case_ids"] = ["fg-a"]
    assert errors(course) == []


def test_illustrative_comparison_may_not_read_as_a_controlled_before_after():
    course = field_course()
    comparison = recipe_of(course)["comparison"]
    comparison.update(relation="illustrative")
    assert any("controlled=false" in e for e in errors(course))
    comparison["controlled"] = False
    assert errors(course) == []
    comparison["relation"] = "before_after"
    assert any("comparison relation" in e for e in errors(course))


def test_a_recipe_without_a_failure_branch_is_refused():
    course = field_course()
    recipe_of(course)["check"] = {"success": "夹具达标。", "if_failed": ""}
    assert any("failure handling" in e for e in errors(course))
    del recipe_of(course)["check"]
    assert any("Missing field recipe check" in e for e in errors(course))


def test_recipe_ids_are_unique_and_sources_are_course_sources():
    course = field_course()
    course["sections"][1]["blocks"].append(fixture_recipe("fg-recipe"))
    assert any("Invalid field-guide field_recipe ID" in e for e in errors(course))
    course = field_course()
    recipe_of(course)["source_ids"] = ["not-a-course-source"]
    assert any("Unknown field recipe source" in e for e in errors(course))


def test_malformed_recipe_blocks_return_errors_rather_than_raising():
    for broken in [None, 7, "recipe", {}, {"type": "field_recipe"}]:
        course = field_course()
        course["sections"][1]["blocks"] = [broken]
        assert errors(course)  # a message, never a TypeError out of the validator


# --- video_sequence ------------------------------------------------------------

def test_video_sequence_bounds_must_be_finite_and_ordered():
    course = field_course()
    video_of(course).update(start_seconds=96.0, end_seconds=12.0)
    assert any("finite 0 <= start < end" in e for e in errors(course))
    course = field_course()
    video_of(course).update(start_seconds=-1.0, end_seconds=10.0)
    assert any("finite 0 <= start < end" in e for e in errors(course))
    course = field_course()
    video_of(course).update(start_seconds=float("inf"), end_seconds=10.0)
    assert any("finite 0 <= start < end" in e for e in errors(course))
    course = field_course()
    video_of(course).update(start_seconds="12", end_seconds=96.0)
    assert any("finite 0 <= start < end" in e for e in errors(course))


def test_video_steps_must_be_sorted_and_inside_the_outer_interval():
    course = field_course()
    video_of(course)["steps"].reverse()
    assert any("out of order" in e for e in errors(course))
    course = field_course()
    video_of(course)["steps"][1]["end_seconds"] = 400.0
    assert any("outside the sequence interval" in e for e in errors(course))
    course = field_course()
    video_of(course)["steps"][0]["summary"] = ""
    assert any("Malformed video sequence step" in e for e in errors(course))


def test_video_sequence_needs_a_registered_source_and_an_inspection_record():
    course = field_course()
    video_of(course)["source_id"] = "not-a-course-source"
    assert any("needs a course source" in e for e in errors(course))
    course = field_course()
    video_of(course)["inspection"] = {"method": "continuous_segment", "detail": "夹具", "checked_at": "2026-13-40"}
    assert any("inspection record" in e for e in errors(course))
    course = field_course()
    video_of(course)["inspection"]["method"] = "sampled_frames"
    assert any("inspection record" in e for e in errors(course))


def test_video_json_never_carries_a_field_that_claims_the_watching_happened():
    course = field_course()
    video_of(course)["watched"] = True
    assert any("Unknown video sequence fields" in e for e in errors(course))


# --- the two reading blocks this format shares -----------------------------------

def transfer_try(course: dict, **overrides) -> dict:
    """A free-id question about the reader's own new photograph, plus the closed answer."""
    exercise = {"type": "exercise", "id": "try-your-own-low-angle",
                "title": "用你自己的新照片试一次",
                "prompt": "合成夹具：先用你原来的机位拍一张，再降到膝盖高度拍一张，先不比较好坏。"}
    reveal = {"type": "reveal", "activity_id": exercise["id"], "title": "展开：怎么读这两张新照片",
              "paragraphs": ["合成夹具：比较两次画面里人物与背景边缘的分离程度，"
                             "并写下一处你自己仍不能确定的拍摄条件。"],
              "source_ids": ["fg-fixture-source"]}
    exercise.update(overrides.pop("exercise", {}))
    reveal.update(overrides.pop("reveal", {}))
    course["sections"][2]["blocks"] += [exercise, reveal]
    course.update(overrides)
    return course


def test_a_field_course_asks_its_own_question_and_answers_it_closed():
    # One question is enough: this format asks what it needs, not three named activities.
    assert errors(transfer_try(field_course())) == []
    course = transfer_try(field_course(), reveal={"activity_id": "no-such-exercise"})
    assert any("reveal needs one of this course's exercises" in e for e in errors(course))
    course = transfer_try(field_course(), reveal={"source_ids": ["not-a-course-source"]})
    assert any("reveal source" in e for e in errors(course))
    course = transfer_try(field_course(), reveal={"paragraphs": []})
    assert any("Malformed field-guide reveal" in e for e in errors(course))


def test_exercise_ids_are_free_but_unique_and_complete():
    course = transfer_try(field_course())
    assert errors(course) == []
    course = transfer_try(field_course(), exercise={"prompt": "  "})
    assert any("Malformed field-guide exercise" in e for e in errors(course))
    course = transfer_try(field_course(), exercise={"id": "has space"})
    assert any("Invalid field-guide exercise ID" in e for e in errors(course))
    course = field_course()
    doubled = {"type": "exercise", "id": "try-low-angle", "title": "夹具观察题", "prompt": "夹具提示。"}
    course["sections"][2]["blocks"] += [doubled, dict(doubled)]
    assert any("Invalid field-guide exercise ID" in e for e in errors(course))


@pytest.mark.parametrize("value", [[], {}, 1])
def test_a_broken_shape_is_reported_rather_than_raised(value):
    """Types are settled before any set, membership test or loop runs on them: a shape
    that is not what the reader would dereference is a message, never a TypeError."""
    for course in [field_course(course_format=value), field_course(source_ids=value),
                   field_course(cases=value)]:
        assert errors(course), course["id"]
    for path, target in [(1, 'id'), (1, 'source_ids')]:
        course = field_course()
        course["sections"][path][target] = value
        if target == 'source_ids' and value == []:
            assert errors(course) == []  # A section may have no additional citations.
        else:
            assert errors(course)
    for block in [{"type": value}, {"type": "comparison", "rows": value},
                  {"type": "tradeoffs", "rows": value}, {"type": "case_pair", "case_ids": value},
                  {"type": "case", "case_id": value}, {"type": "list", "items": value},
                  {k: v for k, v in fixture_recipe("fg-recipe").items() if k != "id"},
                  {"type": "field_recipe", "id": value, "target": value, "comparison": value,
                   "check": value, "source_ids": value},
                  {"type": "video_sequence", "id": "fg-video", "source_id": value, "steps": value}]:
        course = field_course()
        course["sections"][1]["blocks"] = [block]
        assert errors(course), block


# --- Markdown export -----------------------------------------------------------

def write_course(tmp_path: Path, course: dict | None = None, catalog: dict | None = None) -> Path:
    path = tmp_path / "COURSE.json"
    data = catalog if catalog is not None else field_catalog(
        sources=field_catalog()["sources"], gateways=[course if course else field_course()])
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "CONTENT.json").write_text(json.dumps(fixture_content(), ensure_ascii=False), encoding="utf-8")
    return path


def test_export_renders_the_operations_cases_video_and_closed_sources(tmp_path):
    markdown = export(write_course(tmp_path), None, RESEARCH / "GATEWAYS.json",
                      RESEARCH / "SKILL_TREE.json", tmp_path / "CONTENT.json")
    assert "把相机降到人物膝盖高度再拍一张。" in markdown
    assert "画面里能直接看见的停止点" in markdown
    assert "没做到怎么办" in markdown and "代价" in markdown
    # Real comparison pictures, and the video as links into the original source only.
    assert markdown.count("<details>") == markdown.count("</details>") >= 3
    assert "来源与研究记录" in markdown
    assert "](https://field-guide-fixture.example/video/?t=12s)" in markdown
    assert "](https://field-guide-fixture.example/video/?t=48s)" in markdown
    assert "<iframe" not in markdown and "<video" not in markdown
    assert '<summary>片段核对范围</summary>' in markdown
    assert '合成夹具：连续片段核对记录' in markdown
    assert '已核验视频帧' in markdown


def test_export_keeps_the_question_open_and_its_answer_folded(tmp_path):
    markdown = export(write_course(tmp_path, transfer_try(field_course())), None,
                      RESEARCH / "GATEWAYS.json", RESEARCH / "SKILL_TREE.json",
                      tmp_path / "CONTENT.json")
    assert "用你自己的新照片试一次" in markdown
    assert "<summary>展开：怎么读这两张新照片</summary>" in markdown
    assert markdown.count("<details>") == markdown.count("</details>")


def test_export_refuses_a_broken_contract_instead_of_writing_a_lesson(tmp_path):
    course = field_course()
    recipe_of(course)["target"]["basis"] = "author_measured"
    with pytest.raises(ValueError) as failure:
        export(write_course(tmp_path, course), None, RESEARCH / "GATEWAYS.json",
               RESEARCH / "SKILL_TREE.json", tmp_path / "CONTENT.json")
    assert "integrity failed" in str(failure.value)
    with pytest.raises(ValueError) as failure:
        export(write_course(tmp_path), "no-such-course", RESEARCH / "GATEWAYS.json",
               RESEARCH / "SKILL_TREE.json", tmp_path / "CONTENT.json")
    assert "No course named" in str(failure.value)


def test_export_cli_writes_the_markdown_or_fails_loudly(tmp_path, monkeypatch, capsys):
    course_file = write_course(tmp_path)
    output = tmp_path / "out" / "course.md"
    monkeypatch.setattr(sys, "argv", ["render_field_course.py", str(course_file),
                                      "--sources", str(RESEARCH / "GATEWAYS.json"),
                                      "--tree", str(RESEARCH / "SKILL_TREE.json"),
                                      "--content", str(tmp_path / "CONTENT.json"),
                                      "--output", str(output)])
    assert render_main() == 0
    assert "WROTE" in capsys.readouterr().out
    assert "把相机降到人物膝盖高度再拍一张。" in output.read_text(encoding="utf-8")
    broken = field_course()
    recipe_of(broken)["check"]["if_failed"] = ""
    monkeypatch.setattr(sys, "argv", ["render_field_course.py", str(write_course(tmp_path, broken)),
                                      "--sources", str(RESEARCH / "GATEWAYS.json"),
                                      "--tree", str(RESEARCH / "SKILL_TREE.json"),
                                      "--content", str(tmp_path / "CONTENT.json"),
                                      "--output", str(tmp_path / "never.md")])
    assert render_main() == 1
    assert "FAIL" in capsys.readouterr().out
    assert not (tmp_path / "never.md").exists()


# --- browser: the same boundary before and after the merge ---------------------

@pytest.mark.parametrize('images', [1, {}, 'bad'])
def test_malformed_media_is_reported_without_a_validator_exception(images):
    course = field_course()
    course['cases'][0]['images'] = images
    assert errors(course)


def test_field_sources_cannot_borrow_another_course_source():
    course, catalog = field_course(), field_catalog()
    catalog['sources'].append({**catalog['sources'][0], 'id': 'foreign-source'})
    recipe_of(course)['source_ids'] = ['foreign-source']
    assert any('source' in e.lower() for e in errors(course, catalog))

@pytest.fixture
def field_site(tmp_path, monkeypatch):
    """The shipped learning page, served with a synthetic field-guide course payload."""
    import shutil
    import socket
    import threading
    import time

    import uvicorn

    from ref_lab.api import create_app
    from ref_lab.config import Settings
    from ref_lab.learning_preview import STATIC_FILES
    from conftest import TOKEN

    payload = {"schema_version": 1, "extension": "field-guide-fixture",
               "gateways": [field_course()],
               "gateway_sources": field_catalog()["sources"]}
    web = tmp_path / "web"
    shutil.copytree(ROOT / "web", web)
    base = json.loads((web / 'learning-atlas.json').read_text(encoding='utf-8'))
    base['learning_content']['media'] += fixture_content()['media']
    (web / 'learning-atlas.json').write_text(json.dumps(base, ensure_ascii=False), encoding='utf-8')
    (web / "learning-action-directing.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert "learning-action-directing.json" in STATIC_FILES
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    app = create_app(Settings(tmp_path / "data", TOKEN, public_origin=origin, web_dir=web))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started, "field-guide learning server did not start"
    try:
        yield origin
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_the_reader_shows_the_operation_without_synthesised_missing_evidence(field_site, width, height):
    from test_learning_ui import _unlock

    origin = field_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        writes, errors_seen = [], []
        page.on("request", lambda request: writes.append(request.url)
                if request.method in {"PUT", "POST", "DELETE"} else None)
        page.on("pageerror", lambda error: errors_seen.append(str(error)))
        _unlock(page, origin)
        page.goto(origin + "/learning?course=fg-fixture-course")
        expect(page.locator("#gateway-dialog")).to_be_visible()
        # The reading path a field course promises, in one operation block.
        expect(page.locator(".field-recipe")).to_have_count(1)
        expect(page.locator(".field-recipe .field-stop")).to_contain_text("画面里能直接看见的停止点")
        expect(page.locator(".field-recipe .field-compare .gateway-case")).to_have_count(2)
        expect(page.locator(".field-recipe .field-failed")).to_contain_text("没做到怎么办")
        expect(page.locator(".field-recipe .field-cost")).to_contain_text("代价")
        # No four audit rows, and no invented "missing quote" prose in the lesson.
        expect(page.locator(".field-recipe .case-evidence-row")).to_have_count(0)
        expect(page.locator(".gateway-case .case-record")).to_have_count(2)
        expect(page.locator(".gateway-case .case-record").first).not_to_have_attribute("open", "")
        expect(page.locator(".gateway-case .case-record").first).to_contain_text("来源与研究记录")
        expect(page.locator("#gateway-dialog")).not_to_contain_text("未提供作者原话")
        # The video is a reading order of links, not a player.
        expect(page.locator(".field-video .video-step")).to_have_count(2)
        expect(page.locator(".field-video iframe, .field-video video")).to_have_count(0)
        expect(page.locator(".field-video a.video-time").first).to_have_attribute("href", re.compile(r"[?&]t=12s"))
        expect(page.locator(".video-inspection")).not_to_have_attribute('open', '')
        # Media rendering is reused unchanged, including its failure fallback.
        expect(page.locator(".field-compare .case-image img").first).to_have_attribute(
            "src", "/api/learning-note-media/fg-fixture-frame")
        page.locator('.field-compare').scroll_into_view_if_needed()
        expect(page.locator(".field-compare .case-load-error").first).to_be_visible()
        expect(page.locator(".field-compare")).to_contain_text("原案例与图像出处")
        # The source list is one collapsed section, not metadata under every paragraph.
        expect(page.locator(".gateway-source-fold")).to_have_count(1)
        expect(page.locator(".gateway-source-fold")).not_to_have_attribute("open", "")
        expect(page.locator(".gateway-chapter")).to_have_count(3)
        expect(page.locator("#gateway-dialog textarea, #gateway-form, #gateway-stage, #gateway-save,"
                            " [data-gw-choice]")).to_have_count(0)
        assert not page.locator("#gateway-dialog").evaluate("(el)=>el.scrollWidth>el.clientWidth")
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        page.locator('[data-gw-section="watch"]').click()
        expect(page.locator("#gw-watch")).to_be_visible()
        page.keyboard.press("Escape")
        page.locator('.course-index [data-open-gateway="fg-fixture-course"]').click()
        expect(page.locator("#gateway-dialog")).to_be_visible()
        expect(page.locator(".field-recipe")).to_have_count(1)
        # Reading this course writes nothing at all.
        assert writes == []
        assert errors_seen == []
        browser.close()


@pytest.mark.parametrize("mutation,expected", [
    ({"target": {"text": "夹具停止点。", "basis": "author_measured"}}, "basis"),
    ({"comparison": {"case_ids": ["fg-a"], "relation": "illustrative", "controlled": True,
                     "conditions": ["夹具条件"], "look_for": "夹具观察重点。"}}, "controlled=false"),
])
def test_a_malformed_field_guide_block_never_reaches_the_reader(field_site, mutation, expected):
    from test_learning_ui import _unlock

    origin = field_site
    body = json.dumps({"schema_version": 1, "extension": "field-guide-fixture",
                       "gateways": [{**field_course(), "sections": [
                           {**field_course()["sections"][0]},
                           {"id": "operation", "title": "夹具现场操作",
                            "blocks": [{**fixture_recipe("fg-recipe"), **mutation}]}]}],
                       "gateway_sources": field_catalog()["sources"]}, ensure_ascii=False)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/learning-action-directing.json",
                   lambda route: route.fulfill(status=200, content_type="application/json", body=body))
        _unlock(page, origin)
        page.goto(origin + "/learning?course=fg-fixture-course")
        page.locator("#domain-grid").wait_for()
        expect(page.locator("#gateway-dialog")).not_to_be_visible()
        expect(page.locator("#load-error")).to_contain_text(expected)
        # Nothing was merged, so the base map and its own course are untouched.
        expect(page.locator(".domain-card").first).to_be_visible()
        expect(page.locator('.course-index [data-open-gateway="sword-perspective-chapter"]')).to_have_count(1)
        browser.close()


def test_a_field_question_is_asked_open_and_its_answer_stays_folded(field_site):
    """Try first, read later: the reading blocks the legacy course already uses travel
    into this format unchanged, and reading the pair still writes nothing."""
    from test_learning_ui import _unlock

    origin = field_site
    body = json.dumps({"schema_version": 1, "extension": "field-guide-fixture",
                       "gateways": [transfer_try(field_course())],
                       "gateway_sources": field_catalog()["sources"]}, ensure_ascii=False)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        writes = []
        page.on("request", lambda request: writes.append(request.url)
                if request.method in {"PUT", "POST", "DELETE"} else None)
        page.route("**/learning-action-directing.json",
                   lambda route: route.fulfill(status=200, content_type="application/json", body=body))
        _unlock(page, origin)
        page.goto(origin + "/learning?course=fg-fixture-course")
        expect(page.locator(".gateway-exercise")).to_have_count(1)
        expect(page.locator(".gateway-exercise")).to_contain_text("先不比较好坏")
        reveal = page.locator(".gateway-reveal")
        expect(reveal).to_have_count(1)
        expect(reveal).not_to_have_attribute("open", "")
        # The analysis stays shut until the reader chooses to open it.
        expect(reveal.locator('div')).not_to_be_visible()
        reveal.scroll_into_view_if_needed()
        page.locator(".gateway-reveal summary").click()
        expect(reveal).to_contain_text("背景边缘的分离程度")
        assert writes == []
        browser.close()


def test_folded_quotes_preserve_verification_and_content_changes_reset_only_reading(field_site):
    from test_learning_ui import _unlock
    course = transfer_try(field_course())
    checked = {'text': 'SYNTHETIC CHECKED QUOTE', 'verification': 'verbatim_checked',
               'source_id': 'fg-fixture-source', 'locator': 'fixture paragraph',
               'checked_at': '2026-10-11', 'language': 'en'}
    course['cases'][0]['evidence'] = {'quote': {**checked, 'verification': 'unverified'}}
    course['cases'][1]['evidence'] = {'quote': checked}
    def body():
        return json.dumps({'schema_version': 1, 'extension': 'field-guide-fixture',
                           'gateways': [course], 'gateway_sources': field_catalog()['sources']}, ensure_ascii=False)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route('**/learning-action-directing.json', lambda route: route.fulfill(
            status=200, content_type='application/json', body=body()))
        _unlock(page, field_site)
        before = page.request.get(field_site + '/api/learning-state').json()
        writes = []
        page.on('request', lambda r: writes.append(r.url) if r.method in {'PUT','POST','DELETE'} else None)
        page.goto(field_site + '/learning?course=fg-fixture-course')
        unchecked = page.locator('[data-case="fg-a"] .case-record-line')
        expect(unchecked).to_have_attribute('data-verified', 'false')
        expect(unchecked).to_contain_text('待核引文 · 未核验')
        verified = page.locator('[data-case="fg-b"] .case-record-line')
        expect(verified).to_have_attribute('data-verified', 'true')
        expect(verified).to_contain_text('fixture paragraph')
        expect(verified.locator('a')).to_have_attribute('href', PAGE)
        page.locator('[data-gw-section="watch"]').click()
        page.locator('[data-gw-reveal] summary').click()
        expect(page.locator('[data-gw-reveal]')).to_have_attribute('open', '')
        page.locator('#gateway-close').click()
        key = 'photography-gateway-draft-v2:fg-fixture-course'
        saved = page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k))', key)
        saved.update(stage='analysis', answers={'transfer': 'prior personal answer'})
        page.evaluate('([k,v])=>sessionStorage.setItem(k,JSON.stringify(v))', [key,saved])
        course['sections'][2]['blocks'][-1]['paragraphs'][0] += ' Changed analysis.'
        page.reload()
        expect(page.locator('[data-gw-reveal]')).not_to_have_attribute('open', '')
        page.locator('#gateway-close').click()
        updated = page.evaluate('(k)=>JSON.parse(sessionStorage.getItem(k))', key)
        assert updated['version'] != saved['version']
        assert updated['stage'] == 'analysis' and updated['answers'] == saved['answers']
        assert updated['revealed'] == [] and updated['last_section'] == course['sections'][0]['id']
        assert page.request.get(field_site + '/api/learning-state').json() == before
        assert writes == []
        browser.close()


@pytest.mark.parametrize('failure', ['images', 'source_scope'])
def test_browser_refuses_bad_media_and_sources_without_losing_the_base(field_site, failure):
    from test_learning_ui import _unlock
    course, catalog = field_course(), field_catalog()
    if failure == 'images':
        course['cases'][0]['images'] = 1
    else:
        catalog['sources'].append({**catalog['sources'][0], 'id': 'foreign-source'})
        recipe_of(course)['source_ids'] = ['foreign-source']
    payload = {'schema_version': 1, 'extension': 'field-guide-fixture',
               'gateways': [course], 'gateway_sources': catalog['sources']}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route('**/learning-action-directing.json', lambda route: route.fulfill(
            status=200, content_type='application/json', body=json.dumps(payload, ensure_ascii=False)))
        seen = []
        page.on('pageerror', lambda error: seen.append(str(error)))
        _unlock(page, field_site)
        page.goto(field_site + '/learning?course=fg-fixture-course')
        page.locator('#domain-grid').wait_for()
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        expect(page.locator('#load-error')).to_contain_text('图片数据无效' if failure == 'images' else '出处')
        expect(page.locator('.domain-card').first).to_be_visible()
        assert seen == []
        browser.close()


def test_an_unknown_format_is_refused_before_the_reader_uses_it(field_site):
    from test_learning_ui import _unlock

    origin = field_site
    body = json.dumps({"schema_version": 1, "extension": "field-guide-fixture",
                       "gateways": [field_course(course_format="field-guide-v2")],
                       "gateway_sources": field_catalog()["sources"]}, ensure_ascii=False)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/learning-action-directing.json",
                   lambda route: route.fulfill(status=200, content_type="application/json", body=body))
        _unlock(page, origin)
        # The refusal reaches the reader where every other rejection does: on the page
        # that asked for this course by name.
        page.goto(origin + "/learning?course=fg-fixture-course")
        page.locator("#domain-grid").wait_for()
        expect(page.locator("#load-error")).to_contain_text("course_format")
        expect(page.locator('.course-index [data-open-gateway="sword-perspective-chapter"]')).to_have_count(1)
        browser.close()


def test_the_original_three_gateways_still_render_their_four_layer_reader(field_site):
    from test_learning_ui import _unlock

    origin = field_site
    shipped = json.loads((ROOT / "web/learning-atlas.json").read_text(encoding="utf-8"))
    gateways = [g for g in shipped["gateways"] if g.get("kind") != "course"]
    notes = shipped.get("learning_content", {}).get("notes", [])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        page.goto(origin + "/learning")
        page.locator("#domain-grid").wait_for()
        assert len(gateways) == 3
        assert len(notes) == 12
        expect(page.locator(".gateway-index-list [data-open-gateway]")).to_have_count(len(gateways))
        page.locator(f'.gateway-index-list [data-open-gateway="{gateways[0]["id"]}"]').click()
        expect(page.locator("#gateway-dialog")).to_be_visible()
        # The legacy four-layer gateway UI is untouched by the new format.
        expect(page.locator("#gateway-dialog .gateway-chapter")).to_have_count(8)
        expect(page.locator("#gateway-form")).to_have_count(1)
        expect(page.locator("#gateway-dialog [data-gw-reveal]").first).to_be_visible()
        expect(page.locator("#gateway-dialog .gateway-source-fold")).to_have_count(0)
        browser.close()


def test_the_shipped_bundle_keeps_gateways_and_declares_the_course_format():
    """Only courses opt into field guides; conceptual gateways keep their contract."""
    shipped = json.loads((ROOT / "web/learning-atlas.json").read_text(encoding="utf-8"))
    assert sum(1 for g in shipped["gateways"] if g.get("kind") != "course") == 3
    assert sum(1 for g in shipped["gateways"] if g.get("kind") == "course") == 1
    gateways = [g for g in shipped['gateways'] if g.get('kind') != 'course']
    assert not any('course_format' in g for g in gateways)
    course = next(g for g in shipped['gateways'] if g.get('kind') == 'course')
    assert course['course_format'] == 'field-guide-v1'
    assert any(b.get('type') == 'field_recipe' for s in course['sections'] for b in s['blocks'])
