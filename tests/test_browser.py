"""Browser workflows use explicitly synthetic fixtures, not claims about real cosplay images."""
from __future__ import annotations

import io
import os
import shutil
import socket
import threading
import time
import zipfile
from pathlib import Path
import pytest
import uvicorn
from ref_lab.api import create_app
from ref_lab.config import Settings
from ref_lab.models import CandidateInput, Card, ProjectInput, ReferenceEdit, Source, VisualReview
from conftest import TOKEN, card_data, image_bytes, review_data


@pytest.fixture
def live_site(tmp_path):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    settings = Settings(tmp_path / "data", TOKEN, public_origin=f"http://127.0.0.1:{port}")
    app = create_app(settings)
    library = app.state.library
    project = library.create_project(ProjectInput(character="王昭君", work="王者荣耀", costume="长夜焕生", brief="漫展实用；以站姿、回眸与自然互动为主。"))
    for index in range(3):
        asset = library.ingest_asset(image_bytes(index))
        library.add_candidate(project["id"], CandidateInput(asset_sha=asset["id"], title=f"独立参考 {index+1}"))
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    for _ in range(150):
        if server.started: break
        time.sleep(.02)
    assert server.started
    yield settings.public_origin, library, project
    server.should_exit = True
    thread.join(timeout=8)
    sock.close()


@pytest.fixture
def browser_page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as engine:
        executable = os.environ.get("LAB_CHROMIUM") or shutil.which("chromium") or shutil.which("chromium-browser")
        if not executable and not Path(engine.chromium.executable_path).exists():
            pytest.skip("Chromium not installed; run python -m playwright install chromium")
        browser = engine.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        yield page, errors
        browser.close()
        assert not errors, errors


def unlock(page, url):
    page.goto(url)
    page.get_by_label("访问口令").fill(TOKEN)
    page.get_by_role("button", name="进入我的参考库").click()
    page.locator("#main-image").wait_for()


def artifact(page, name):
    folder = Path(os.environ.get("LAB_TEST_ARTIFACTS", ".local/test-artifacts"))
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / name), full_page=True)


def test_browser_select_persist_filter_and_mobile(live_site, browser_page):
    url, library, project = live_site
    page, errors = browser_page
    unlock(page, url)
    page.get_by_label("我喜欢／不喜欢的地方").fill("只借鉴动作，不借鉴服装")
    page.get_by_role("button", name="✓ 保留 K", exact=True).click()
    page.wait_for_function("document.querySelector('#stats').textContent.includes('1人工保留')")
    ref = library.references(project["id"], decision="keep")["items"][0]
    assert ref["preference"] == "只借鉴动作，不借鉴服装"
    page.reload()
    page.locator("#main-image").wait_for()
    page.get_by_label("选择状态", exact=True).select_option("keep")
    page.wait_for_function("document.querySelector('.pagination').textContent.includes('1–1 / 1')")
    assert page.get_by_label("我喜欢／不喜欢的地方").input_value() == "只借鉴动作，不借鉴服装"
    artifact(page, "desktop-synthetic-reference.png")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(120)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    artifact(page, "mobile-synthetic-reference.png")
    page.get_by_role("button", name="查看独立原图", exact=True).click()
    assert page.locator("#lightbox").is_visible()
    page.get_by_role("button", name="关闭", exact=True).click()
    page.get_by_role("button", name="现场卡", exact=True).click()
    page.get_by_text("还没有已确认的现场卡", exact=True).wait_for()


def test_browser_review_card_accept_and_offline_pack(live_site, browser_page, tmp_path):
    url, library, project = live_site
    page, errors = browser_page
    unlock(page, url)
    page.locator("#auto-advance").uncheck()
    page.get_by_role("button", name="✓ 保留 K", exact=True).click()
    page.get_by_role("button", name="人工核验", exact=True).wait_for()
    page.get_by_role("button", name="人工核验", exact=True).click()
    page.get_by_label("图片实际类型").select_option("cosplay_photo")
    page.get_by_label("与目标角色的关系").select_option("exact")
    for text in ("图中有明确可见的人物", "需要借鉴的肢体／动作看得清", "这是独立画面，不是多个画面的拼图", "实际清晰度足以支持动作分析"):
        page.get_by_label(text, exact=True).check()
    page.get_by_label("看得见的事实（每行一条）*").fill("Synthetic regression evidence, not actual image analysis.")
    page.get_by_role("button", name="保存人工核验", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="来源与标题", exact=True).click()
    page.get_by_label("权利状态").select_option("owned")
    page.get_by_label("使用权／来源说明").fill("Synthetic image generated in this test")
    page.get_by_label("我已检查原发布页，或确认这是我的自有作品").check()
    page.get_by_role("button", name="保存来源", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="编写资料卡", exact=True).click()
    form = page.locator("#editor form")
    for name, value in {"intent":"Test only", "verbal_cues":"身体朝那边，舒服地回头。", "static_steps":"先调整朝向。", "photographer_steps":"先确定构图。", "safety":"不要强扭颈部。", "fallback":"减小转身角度。", "visible_evidence":"Synthetic image, not real lighting evidence.", "interpretation":"Test reproduction plan, not original equipment.", "available_gear_plan":"One-light test plan."}.items():
        form.locator(f'[name="{name}"]').fill(value)
    page.get_by_role("button", name="保存资料卡草稿", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="我已核对，确认为现场卡", exact=True).click()
    page.get_by_text("已通过入库门槛，并由你确认。可加入离线拍摄包。", exact=True).wait_for()
    page.get_by_role("button", name="离线拍摄包", exact=True).click()
    with page.expect_download() as download_info:
        page.get_by_role("button", name="生成并下载", exact=True).click()
    pack = tmp_path / "pack.zip"
    download_info.value.save_as(pack)
    extracted = tmp_path / "offline"
    with zipfile.ZipFile(pack) as archive:
        archive.extractall(extracted)  # Trusted, newly generated test output, not user input.
    page.context.set_offline(True)
    page.goto((extracted / "index.html").as_uri())
    page.wait_for_function("document.querySelector('#photo').naturalWidth > 0")
    assert "身体朝那边" in page.locator("#guide").text_content()
    assert page.locator("#photo").evaluate("image => image.naturalWidth") == 800
    artifact(page, "offline-synthetic-field-card.png")


def test_browser_project_creation_notes_and_inert_html(live_site, browser_page):
    url, library, project = live_site
    page, errors = browser_page
    unlock(page, url)
    page.get_by_role("button", name="新建角色项目", exact=True).click()
    page.get_by_label("角色名 *", exact=True).fill("有马加奈")
    page.get_by_label("补充要求", exact=True).fill("日常人像与自然动作，服装版本以后再补。")
    page.get_by_role("button", name="建立项目", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="摄影笔记", exact=True).click()
    page.get_by_role("button", name="＋ 写摄影笔记", exact=True).click()
    page.get_by_label("笔记标题 *", exact=True).fill("引导笔记")
    page.get_by_label("正文（支持保留 Markdown）", exact=True).fill("# 观察\n<script>window.evil=1</script>\n先沟通，再调整。")
    page.get_by_role("button", name="保存笔记", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.locator("[data-note]").first.click()
    assert page.evaluate("window.evil") is None
    page.get_by_role("button", name="编辑笔记", exact=True).click()
    page.get_by_label("正文（支持保留 Markdown）", exact=True).fill("# 更新\n保留有效的引导。")
    page.get_by_role("button", name="保存笔记", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    assert "保留有效的引导" in page.locator("[data-note]").text_content()
    page.get_by_role("button", name="采集与分析", exact=True).click()
    page.get_by_role("button", name="＋ 建立采集任务", exact=True).click()
    page.get_by_role("button", name="建立待执行任务", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_text("等待执行／受阻", exact=True).wait_for()
