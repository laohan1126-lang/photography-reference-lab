"""Action-directing course extension: schema, additive merge and safety boundaries.

Every fixture here is synthetic. These checks prove the payload contract, the
additive merge and the media allow-list — they are not evidence that the course
teaches well, that the referenced photographs mean what a caption says, or that
any user has accepted the chapter.
"""
from __future__ import annotations

import json
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect, sync_playwright

from ref_lab.action_directing_media import (ACTION_DIRECTING_SOURCE_CASE_MEDIA,
                                           ACTION_DIRECTING_SOURCE_IMAGE_CSP)
from ref_lab.learning_media import SOURCE_CASE_MEDIA
from ref_lab.learning_preview import STATIC_FILES
from tools.build_action_directing import EXTENSION, build_payload, main as build_main, serialized
from tools.build_photography_atlas import build_payload as build_base_payload
from conftest import TOKEN
from test_learning_ui import _unlock

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
RESEARCH = ROOT / "docs/research/photography-atlas"
COURSE_URL = "/learning?course=action-directing-module"
FIXTURE_PAGE = "https://westcottu.com/jerry-action-directing/"


# --- synthetic course fixture -------------------------------------------------

def fixture_skill_ids() -> list[str]:
    """Real skill IDs from the tree, so unknown-skill checks stay meaningful."""
    tree = json.loads((RESEARCH / "SKILL_TREE.json").read_text(encoding="utf-8"))
    preferred = [s["id"] for s in tree["skills"] if s["id"].startswith("posing-") and "action" in s["id"]]
    return preferred[:2] or [s["id"] for s in tree["skills"]][:2]


def _case(case_id: str, title: str, src: str, alt: str) -> dict:
    return {
        "id": case_id, "title": title,
        "author": "SYNTHETIC FIXTURE AUTHOR",
        "caption": "合成测试夹具图片说明，不代表真实案例判断。",
        "alt": alt, "url": FIXTURE_PAGE, "display": "source_remote",
        "images": [{"src": src, "width": 1366, "height": 2048, "alt": alt}],
        "source_summary": {"text": "合成测试夹具转述；原页定位仅用于校验契约。",
                           "locator": "合成定位", "source_id": "ad-fixture-source",
                           "checked_at": "2026-10-11"},
        "rights": {"allowed": False, "url": FIXTURE_PAGE,
                   "statement": "合成测试夹具：无再分发许可，不缓存、不提交图片。"},
        "review": {"level": "pixel_reviewed", "checked_at": "2026-10-11",
                   "detail": "合成测试夹具：不代表真实像素复核记录。"},
    }


def _section(section_id: str, title: str, blocks: list) -> dict:
    return {"id": section_id, "title": title, "blocks": blocks}


def synthetic_course() -> dict:
    """A minimal contract-valid course. Text is fixture text, not teaching content."""
    solo, transfer = [urls[0] for urls in ACTION_DIRECTING_SOURCE_CASE_MEDIA.values()]
    source_ids = ["ad-fixture-source"]
    return {
        "schema_version": 1,
        "meta": {"label": "PHOTO ATLAS · 完整课程", "note": "合成测试夹具课程"},
        "sources": [{"id": "ad-fixture-source", "url": FIXTURE_PAGE, "title": "合成测试夹具出处",
                     "author": "SYNTHETIC FIXTURE AUTHOR", "reading_depth": "仅核对简介",
                     "checked_at": "2026-10-11", "locator": "合成定位",
                     "support": "只用于验证数据契约", "limitation": "不代表任何真实来源结论"}],
        "gateways": [{
            "id": EXTENSION, "kind": "course", "label": "PHOTO ATLAS · 完整课程",
            "title": "合成测试夹具课程 · 动作指导", "question": "夹具问题？",
            "outcome": "夹具结果说明。", "method": "夹具方法。",
            "author": "SYNTHETIC FIXTURE", "reading_depth": "合成测试夹具",
            "prior_knowledge": "合成测试夹具先修说明。",
            "skill_ids": fixture_skill_ids(), "source_ids": source_ids,
            "cases": [_case("action-jerry-solo", "夹具案例 A", solo, "合成测试夹具图像描述 A"),
                      _case("action-jerry-transfer", "夹具案例 B", transfer, "合成测试夹具图像描述 B")],
            "sections": [
                _section("problem", "夹具问题", [
                    {"type": "exercise", "id": "observation", "title": "夹具观察题",
                     "prompt": "先看什么？"}]),
                _section("observe", "夹具观察", [{"type": "paragraph", "text": "合成测试夹具段落。"}]),
                _section("principle", "夹具原理", [{"type": "case", "case_id": "action-jerry-solo"}]),
                _section("contrast", "夹具对照", [
                    {"type": "comparison", "rows": [{"novice": "夹具新手", "expert": "夹具熟手",
                                                     "question": "夹具追问"}]}]),
                _section("boundary", "夹具边界", [
                    {"type": "tradeoffs", "rows": [{"action": "夹具动作", "effect": "夹具预计变化",
                                                    "cost": "夹具代价", "test": "夹具检查"}]},
                    {"type": "paragraph", "text": "合成测试夹具段落。"}]),
                _section("transfer", "夹具迁移", [
                    {"type": "exercise", "id": "comparison", "title": "夹具对照题", "prompt": "差别在哪？"},
                    {"type": "exercise", "id": "transfer", "title": "夹具迁移题", "prompt": "你会怎么改？"},
                    {"type": "case", "case_id": "action-jerry-transfer"},
                    {"type": "reveal", "activity_id": "observation", "title": "夹具观察解析",
                     "paragraphs": ["合成测试夹具解析。"], "source_ids": source_ids},
                    {"type": "reveal", "activity_id": "comparison", "title": "夹具对照解析",
                     "paragraphs": ["合成测试夹具解析。"], "source_ids": source_ids},
                    {"type": "reveal", "activity_id": "transfer", "title": "夹具迁移解析",
                     "paragraphs": ["合成测试夹具解析。"], "source_ids": source_ids}]),
                _section("reflect", "夹具回顾", [{"type": "paragraph", "text": "合成测试夹具段落。"}]),
                _section("sources", "夹具出处", [
                    {"type": "paragraph", "text": "合成测试夹具段落。", "source_ids": source_ids}]),
            ],
        }],
    }


def research_with_fixture(tmp_path: Path) -> Path:
    directory = tmp_path / "research"
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL_TREE.json", "LEARNING_CONTENT.json", "GATEWAYS.json"):
        shutil.copy(RESEARCH / name, directory / name)
    (directory / "COURSE.json").write_text(
        json.dumps(synthetic_course(), ensure_ascii=False), encoding="utf-8")
    return directory


def build_with_fixture(tmp_path: Path, course: dict | None = None) -> dict:
    directory = research_with_fixture(tmp_path)
    if course is not None:
        (directory / "COURSE.json").write_text(json.dumps(course, ensure_ascii=False), encoding="utf-8")
    return build_payload(directory)


# --- media registry and content security policy ------------------------------

def _csp_image_tokens(policy: str) -> set[str]:
    """Read img-src sources the way a browser does: by token, not by substring."""
    directive = next(part for part in policy.split(";") if part.strip().startswith("img-src"))
    return set(directive.split()[1:])


def _is_exact_image_source(token: str) -> bool:
    """One full https URL naming a file — never a bare host, never a wildcard."""
    parsed = urlparse(token)
    return (parsed.scheme == "https" and bool(parsed.netloc) and parsed.path not in ("", "/")
            and not parsed.query and not parsed.fragment)


def test_course_media_is_registered_exactly_and_kept_separate_from_the_base(tmp_path):
    assert ACTION_DIRECTING_SOURCE_CASE_MEDIA == {
        "action-jerry-solo": (
            "https://westcottu.com/wp-content/uploads/Portrait-Lit-from-the-Front-Using-One-Ice-Light-3-on-a-Boom-Arm.jpg",
        ),
        "action-jerry-transfer": (
            "https://westcottu.com/wp-content/uploads/Studio-Couples-Portrait-with-Two-Ice-Light-3-Bi-Color-Lights.jpg",
        ),
    }
    before = dict(SOURCE_CASE_MEDIA)
    payload = build_with_fixture(tmp_path)
    # Building the course extension must not add to, drop from or reorder the base
    # registry. Its size belongs to the base atlas's own reviewed work, so the boundary
    # is proved by unchanged content, not by a fixed count.
    assert SOURCE_CASE_MEDIA == before
    assert list(SOURCE_CASE_MEDIA) == list(before)
    # The base chapter registry keeps owning exactly its own reviewed cases.
    assert not SOURCE_CASE_MEDIA.keys() & ACTION_DIRECTING_SOURCE_CASE_MEDIA.keys()
    assert not any("westcottu" in url for urls in SOURCE_CASE_MEDIA.values() for url in urls)
    assert {case["id"] for case in payload["gateways"][0]["cases"]} == set(
        ACTION_DIRECTING_SOURCE_CASE_MEDIA)
    # The real shipped bundle still resolves on its own old case ids, with none of the
    # extension's cases present.
    shipped = json.loads((WEB / "learning-atlas.json").read_text(encoding="utf-8"))
    shipped_course = next(g for g in shipped["gateways"]
                          if g["id"] == "sword-perspective-chapter")
    assert {case["id"] for case in shipped_course.get("cases", [])} - set(ACTION_DIRECTING_SOURCE_CASE_MEDIA)
    assert shipped_course.get("cases")
    urls = ACTION_DIRECTING_SOURCE_IMAGE_CSP.split()
    assert sorted(urls) == sorted(url for images in ACTION_DIRECTING_SOURCE_CASE_MEDIA.values()
                                  for url in images)
    # Token-level policy: both full originals are allowed, and neither a bare host nor a
    # wildcard is granted. A substring check would also reject the exact URLs.
    tokens = _csp_image_tokens('img-src ' + ACTION_DIRECTING_SOURCE_IMAGE_CSP)
    assert tokens == set(urls)
    assert all(_is_exact_image_source(token) for token in tokens)
    assert "https://westcottu.com" not in tokens
    assert not any("*" in token for token in tokens)


def test_only_the_learning_document_allows_the_course_images(client):
    learning = client.get("/learning")
    assert learning.status_code == 200
    policy = learning.headers["content-security-policy"]
    assert all(url in policy for url in ACTION_DIRECTING_SOURCE_IMAGE_CSP.split())
    tokens = _csp_image_tokens(policy)
    assert set(ACTION_DIRECTING_SOURCE_IMAGE_CSP.split()) <= tokens
    assert "https://westcottu.com" not in tokens
    assert not any("*" in token for token in tokens)
    for path in ("/api/session", "/health"):
        other = client.get(path).headers["content-security-policy"]
        assert "westcottu.com" not in other


def test_preview_whitelist_carries_the_named_payload_only():
    assert "learning-action-directing.json" in STATIC_FILES
    assert "learning-atlas.json" in STATIC_FILES
    assert not any(name.startswith("action-directing") for name in STATIC_FILES)


# --- builder contract ---------------------------------------------------------

def _run_builder(monkeypatch, research: Path, output: Path, *flags: str) -> int:
    monkeypatch.setattr(sys, "argv", ["build_action_directing.py", "--directory", str(research),
                                      "--base-directory", str(research),
                                      "--output", str(output), *flags])
    return build_main()


def test_fixture_course_is_additive_reproducible_and_checkable(tmp_path):
    payload = build_with_fixture(tmp_path)
    assert payload["schema_version"] == 1 and payload["extension"] == EXTENSION
    assert [gateway["id"] for gateway in payload["gateways"]] == [EXTENSION]
    assert all(gateway["kind"] == "course" for gateway in payload["gateways"])
    assert [source["id"] for source in payload["gateway_sources"]] == ["ad-fixture-source"]
    # Serialization is byte-stable, so --check can compare a shipped payload.
    assert serialized(payload) == serialized(build_with_fixture(tmp_path / "second"))
    # The extension carries teaching payload only; no base atlas fields travel with it.
    assert set(payload) == {"schema_version", "extension", "content_digest", "meta",
                            "gateways", "gateway_sources"}


def test_base_research_files_may_live_beside_the_course_or_in_their_own_base_directory(tmp_path):
    """The course has its own directory; SKILL_TREE/GATEWAYS/LEARNING_CONTENT stay base files."""
    directory = research_with_fixture(tmp_path)
    base = tmp_path / "base"
    base.mkdir()
    for name in ("SKILL_TREE.json", "LEARNING_CONTENT.json", "GATEWAYS.json"):
        shutil.move(str(directory / name), str(base / name))
    # Without a base directory the builder cannot invent the base files it does not own.
    with pytest.raises(ValueError) as failure:
        build_payload(directory)
    assert "--base-directory" in str(failure.value)
    assert not list(directory.glob("*.json")) or {path.name for path in directory.glob("*.json")} == {"COURSE.json"}
    # Naming the base directory reads them in place; nothing is copied into the course
    # directory, so the shipped course never carries another task's working files.
    payload = build_payload(directory, base_directory=base)
    assert [gateway["id"] for gateway in payload["gateways"]] == [EXTENSION]
    assert not list(directory.glob("SKILL_TREE.json"))
    assert not list(directory.glob("GATEWAYS.json"))
    assert not list(directory.glob("LEARNING_CONTENT.json"))


def test_builder_cli_never_reports_success_for_a_missing_or_drifted_payload(tmp_path, monkeypatch, capsys):
    research = research_with_fixture(tmp_path)
    output = tmp_path / "web" / "learning-action-directing.json"

    assert _run_builder(monkeypatch, research, output) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "DRY_RUN"
    assert not output.exists()
    # Each run's output is read before the next run, so a FAIL line can never be parsed
    # as the next run's JSON status.
    assert _run_builder(monkeypatch, research, output, "--check") == 1
    assert "FAIL" in capsys.readouterr().out
    assert _run_builder(monkeypatch, research, output, "--write") == 0
    assert json.loads(capsys.readouterr().out)["status"] == "WRITTEN"
    assert _run_builder(monkeypatch, research, output, "--check") == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
    output.write_text(output.read_text(encoding="utf-8").replace('"gateways"', '"gateways_v2"'),
                      encoding="utf-8")
    assert _run_builder(monkeypatch, research, output, "--check") == 1
    assert "FAIL" in capsys.readouterr().out


def test_missing_canonical_course_fails_loudly_without_writing_anything(tmp_path, monkeypatch, capsys):
    directory = research_with_fixture(tmp_path)
    output = tmp_path / "web" / "learning-action-directing.json"
    (directory / "COURSE.json").unlink()
    with pytest.raises(ValueError) as failure:
        build_payload(directory)
    assert "COURSE.json" in str(failure.value)
    assert _run_builder(monkeypatch, directory, output) == 1
    assert "FAIL" in capsys.readouterr().out
    assert _run_builder(monkeypatch, directory, output, "--check") == 1
    assert not output.exists()


def test_gateway_or_source_id_collisions_with_the_base_catalogue_are_rejected(tmp_path):
    course = synthetic_course()
    course["gateways"][0]["id"] = "sword-perspective-chapter"
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "collides" in str(failure.value)

    course = synthetic_course()
    course["sources"][0]["id"] = "course-sword"
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "collides" in str(failure.value)


def test_only_read_only_course_entries_are_accepted(tmp_path):
    course = synthetic_course()
    course["gateways"][0]["kind"] = "gateway"
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "Unsupported course kind" in str(failure.value)

    course = synthetic_course()
    course["skills"] = [{"id": "posing-action-stance-context"}]
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "base atlas fields" in str(failure.value)

    course = synthetic_course()
    course["gateways"][0]["skill_ids"] = ["no-such-skill-in-the-tree"]
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "skill" in str(failure.value)


def test_unregistered_unsafe_or_resized_media_is_rejected(tmp_path):
    course = synthetic_course()
    course["gateways"][0]["cases"][0]["images"][0]["src"] = (
        "https://westcottu.com/wp-content/uploads/Some-Other-Westcott-Page.jpg")
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "page policy" in str(failure.value)

    course = synthetic_course()
    course["gateways"][0]["cases"][0]["images"][0]["src"] = "javascript:alert(1)"
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "page policy" in str(failure.value)

    course = synthetic_course()
    course["gateways"][0]["cases"][0]["images"][0]["width"] = "1366"
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "dimensions" in str(failure.value)


def test_legacy_base_bundle_entries_stay_exactly_as_shipped():
    base = build_base_payload(RESEARCH)
    shipped_text = (WEB / "learning-atlas.json").read_text(encoding="utf-8")
    shipped = json.loads(shipped_text)
    assert [gateway["id"] for gateway in shipped["gateways"]] == [g["id"] for g in base["gateways"]]
    assert EXTENSION not in {gateway["id"] for gateway in base["gateways"]}
    assert "westcottu.com" not in shipped_text
    assert "sword-perspective-chapter" in {gateway["id"] for gateway in base["gateways"]}
    # The base course keeps its own old case ids and resolves them without the extension.
    shipped_course = next(g for g in shipped["gateways"] if g["id"] == "sword-perspective-chapter")
    assert shipped_course.get("kind") == "course"
    referenced = set()
    for section in shipped_course.get("sections", []):
        for block in section.get("blocks", []):
            if block.get("type") == "case":
                referenced.add(block.get("case_id"))
            elif block.get("type") == "case_pair":
                referenced.update(block.get("case_ids") or [])
    assert referenced
    assert referenced <= {case["id"] for case in shipped_course.get("cases", [])}
    # The base bundle still carries no case from the extension registry.
    assert not referenced & ACTION_DIRECTING_SOURCE_CASE_MEDIA.keys()
    assert (not {case["id"] for gateway in base["gateways"] for case in gateway.get("cases", [])}
            & ACTION_DIRECTING_SOURCE_CASE_MEDIA.keys())


def test_video_cases_stay_link_only_in_the_existing_case_and_source_ui(tmp_path):
    """The planned video case may only link out; no embed, downloader or hidden API."""
    course = synthetic_course()
    course["sources"].append({"id": "ad-fixture-video", "url": "https://westcottu.com/jerry-video-lesson/",
                              "title": "合成测试夹具视频出处", "author": "SYNTHETIC FIXTURE AUTHOR",
                              "reading_depth": "仅核对简介", "checked_at": "2026-10-11",
                              "locator": "合成定位 12:34", "support": "只用于验证数据契约",
                              "limitation": "未观看，不代表任何真实来源结论"})
    case = course["gateways"][0]["cases"][1]
    case["id"] = "action-jerry-video"
    for section in course["gateways"][0]["sections"]:
        for block in section["blocks"]:
            if block.get("case_id") == "action-jerry-transfer":
                block["case_id"] = "action-jerry-video"
    case["url"] = "https://westcottu.com/jerry-video-lesson/"
    case.pop("images")
    case.pop("source_summary")
    case.update(display="external_only", caption="合成测试夹具：仅提供原页与时间点链接。")
    course["gateways"][0]["source_ids"].append("ad-fixture-video")
    payload = build_with_fixture(tmp_path, course)
    video = next(item for item in payload["gateways"][0]["cases"] if item["id"] == "action-jerry-video")
    assert "src" not in video and "images" not in video
    case["src"] = "https://vimeo.com/embed/000000"
    with pytest.raises(ValueError) as failure:
        build_with_fixture(tmp_path, course)
    assert "display" in str(failure.value)


# --- browser: additive merge and visible failure ------------------------------

@pytest.fixture
def action_directing_site(tmp_path):
    from ref_lab.api import create_app
    from ref_lab.config import Settings
    import uvicorn

    payload = build_with_fixture(tmp_path)
    web = tmp_path / "web"
    shutil.copytree(WEB, web)
    (web / "learning-action-directing.json").write_text(serialized(payload), encoding="utf-8")
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
    assert server.started, "action-directing learning server did not start"
    try:
        yield app, tmp_path / "data", origin
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def _watch(page):
    writes, errors = [], []
    page.on("request", lambda request: writes.append(request.url)
            if request.method in {"PUT", "POST", "DELETE"} else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    return writes, errors


def test_course_extension_adds_a_read_only_course_without_touching_the_base(action_directing_site):
    _, _, origin = action_directing_site
    shipped = json.loads((WEB / "learning-atlas.json").read_text(encoding="utf-8"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("https://westcottu.com/**", lambda route: route.abort())
        _unlock(page, origin)
        writes, errors = _watch(page)
        page.goto(origin + COURSE_URL)
        expect(page.locator("#gateway-dialog")).to_be_visible()
        expect(page.locator("#gateway-title")).to_contain_text("合成测试夹具课程")
        # A full course is no longer announced as a sample, and it stays question-only.
        expect(page.locator("#gateway-dialog .gateway-reader-header .eyebrow")).to_contain_text("完整课程")
        expect(page.locator("#gateway-dialog .gateway-exercise")).to_have_count(3)
        expect(page.locator("#gateway-dialog textarea, #gateway-form, #gateway-stage, #gateway-save,"
                            " [data-gw-choice]")).to_have_count(0)
        page.keyboard.press("Escape")
        # The combined catalogue keeps every base course and adds exactly this one. The
        # count is derived from the shipped bundle, not hard-coded, so the base atlas's
        # own future work cannot be mistaken for a merge regression.
        base_courses = [g for g in shipped["gateways"] if g.get("kind") == "course"]
        expect(page.locator(".course-index [data-open-gateway]")).to_have_count(len(base_courses) + 1)
        expect(page.locator('.course-index [data-open-gateway="sword-perspective-chapter"]')).to_have_count(1)
        expect(page.locator(".domain-card")).to_have_count(len(shipped["domains"]))
        page.locator(f'.course-index [data-open-gateway="{EXTENSION}"]').click()
        expect(page.locator("#gateway-dialog")).to_be_visible()
        page.locator('[data-gw-section="transfer"]').click()
        expect(page.locator("#gw-transfer .gateway-case")).to_have_count(1)
        page.keyboard.press("Escape")
        page.locator('.course-index [data-open-gateway="sword-perspective-chapter"]').click()
        expect(page.locator("#gateway-dialog")).to_be_visible()
        expect(page.locator("#gateway-title")).to_contain_text("持剑人物")
        assert writes == []
        assert errors == []
        browser.close()


@pytest.mark.parametrize("body", [
    "this is not json",
    json.dumps({"schema_version": 1, "extension": "action-directing-module",
                "gateways": [{"id": "sword-perspective-chapter", "kind": "course",
                              "skill_ids": [], "source_ids": []}],
                "gateway_sources": []}),
    json.dumps({"schema_version": 1, "extension": "action-directing-module",
                "gateways": [{"id": "action-directing-module", "kind": "course",
                              "skill_ids": ["no-such-skill"], "source_ids": []}],
                "gateway_sources": []}),
    # Legal JSON with a legal id, kind, skill mapping, source and case, and no sections
    # at all. Merging it used to break the whole reading page once it was opened.
    json.dumps({"schema_version": 1, "extension": EXTENSION,
                "gateways": [{**synthetic_course()["gateways"][0], "sections": None}],
                "gateway_sources": synthetic_course()["sources"]}),
])
def test_rejected_extension_keeps_the_base_atlas_usable_and_explains_itself(action_directing_site, body):
    _, _, origin = action_directing_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/learning-action-directing.json",
                   lambda route: route.fulfill(status=200, content_type="application/json", body=body))
        _unlock(page, origin)
        page.goto(origin + COURSE_URL)
        page.locator("#domain-grid").wait_for()
        expect(page.locator("#gateway-dialog")).not_to_be_visible()
        expect(page.locator("#domain-grid")).to_be_visible()
        expect(page.locator("#load-error")).to_be_visible()
        expect(page.locator("#load-error")).to_contain_text("课程")
        expect(page.locator('.course-index [data-open-gateway="sword-perspective-chapter"]')).to_have_count(1)
        browser.close()


def test_unreachable_extension_is_reported_instead_of_a_silent_missing_course(action_directing_site):
    _, _, origin = action_directing_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/learning-action-directing.json", lambda route: route.abort())
        _unlock(page, origin)
        page.goto(origin + COURSE_URL)
        page.locator("#domain-grid").wait_for()
        expect(page.locator("#gateway-dialog")).not_to_be_visible()
        expect(page.locator("#load-error")).to_contain_text(EXTENSION)
        expect(page.locator("#domain-grid")).to_be_visible()
        browser.close()


def test_unknown_course_name_is_explained_rather_than_ignored(action_directing_site):
    _, _, origin = action_directing_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        page.goto(origin + "/learning?course=no-such-course")
        page.locator("#domain-grid").wait_for()
        expect(page.locator("#gateway-dialog")).not_to_be_visible()
        expect(page.locator("#load-error")).to_contain_text("未找到课程")
        browser.close()
