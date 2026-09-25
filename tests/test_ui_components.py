"""No-network browser component tests.

DOM/JS are real. API transport is an explicit in-process TestClient bridge and
image URLs are replaced by synthetic data URIs. These are NOT cookie, CORS,
network, live-browser-collector or offline file:// end-to-end tests.
"""
from __future__ import annotations
import base64
import os
import re
import shutil
from pathlib import Path
import pytest
from conftest import add_reference, card_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ui(client, library, project):
    playwright = pytest.importorskip("playwright.sync_api")
    for i in range(3): add_reference(client, project, i)
    with playwright.sync_playwright() as engine:
        executable = os.environ.get("LAB_CHROMIUM") or shutil.which("chromium")
        if not executable and not Path(engine.chromium.executable_path).exists():
            pytest.skip("Install Chromium to run browser component tests")
        browser = engine.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width":1440, "height":1100})
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        def request(_source, path, method, body, headers):
            response = client.request(method, path, content=body, headers=headers)
            return {"status":response.status_code, "data":response.json()}
        page.expose_binding("__testRequest", request)
        images = {}
        for ref in library.references(project["id"])["items"]:
            for variant in ("original", "preview", "thumb"):
                path = library.assets.path(ref["asset"], variant)
                mime = ref["asset"]["mime"] if variant == "original" else "image/jpeg"
                images[f"/api/assets/{ref['asset_sha']}/{variant}"] = f"data:{mime};base64,"+base64.b64encode(path.read_bytes()).decode()
        markup = (ROOT / "web/index.html").read_text()
        markup = re.sub(r'<link[^>]*>|<script[^>]*>.*?</script>', '', markup)
        def mount():
            page.set_content(markup)
            page.add_style_tag(content=(ROOT / "web/styles.css").read_text())
            page.evaluate("""images => {
                window.fetch = async (path, options={}) => {
                    const result=await window.__testRequest(path, options.method||'GET', options.body||null, Object.fromEntries(options.headers||[]));
                    return new Response(JSON.stringify(result.data),{status:result.status,headers:{'Content-Type':'application/json'}});
                };
                const replace=()=>document.querySelectorAll('img').forEach(img=>{const src=img.getAttribute('src');if(images[src])img.src=images[src]});
                new MutationObserver(replace).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src']});
            }""", images)
            # A fresh script realm is needed for a second mount; tests use a single mount.
            page.add_script_tag(content=(ROOT / "web/app.js").read_text())
            page.locator("#main-image").wait_for()
        mount()
        yield page, library, project
        browser.close()
        assert not errors, errors


def screenshot(page, name):
    folder = Path(os.environ.get("LAB_TEST_ARTIFACTS", ".local/test-artifacts"))
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder/name), full_page=True)


def test_ui_selection_preference_filters_and_responsive_layout(ui):
    page, library, project = ui
    page.get_by_label("我喜欢／不喜欢的地方").fill("只借鉴动作，不借鉴服装")
    page.get_by_role("button", name="✓ 保留 K", exact=True).click()
    page.wait_for_function("document.querySelector('#stats').textContent.includes('1人工保留')")
    assert library.references(project["id"], decision="keep")["items"][0]["preference"] == "只借鉴动作，不借鉴服装"
    page.get_by_label("选择状态", exact=True).select_option("keep")
    page.wait_for_function("document.querySelector('.pagination').textContent.includes('1–1 / 1')")
    screenshot(page, "desktop-component-synthetic.png")
    page.set_viewport_size({"width":390,"height":844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    screenshot(page, "mobile-component-synthetic.png")
    page.get_by_role("button", name="现场卡", exact=True).click()
    page.get_by_text("还没有已确认的现场卡", exact=True).wait_for()


def test_ui_review_then_card_requires_separate_acceptance(ui):
    page, library, project = ui
    page.locator("#auto-advance").uncheck()
    page.get_by_role("button", name="✓ 保留 K", exact=True).click()
    page.get_by_role("button", name="人工核验", exact=True).click()
    page.get_by_label("图片实际类型").select_option("cosplay_photo")
    page.get_by_label("与目标角色的关系").select_option("exact")
    for text in ("图中有明确可见的人物", "需要借鉴的肢体／动作看得清", "这是独立画面，不是多个画面的拼图", "实际清晰度足以支持动作分析"):
        page.get_by_label(text, exact=True).check()
    page.get_by_label("看得见的事实（每行一条）*").fill("Synthetic component-test observation, not an image assessment.")
    page.get_by_role("button", name="保存人工核验", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="来源与标题", exact=True).click()
    page.get_by_label("权利状态").select_option("owned")
    page.get_by_label("使用权／来源说明").fill("Generated synthetic fixture")
    page.get_by_label("我已检查原发布页，或确认这是我的自有作品").check()
    page.get_by_role("button", name="保存来源", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="编写资料卡", exact=True).click()
    form=page.locator("#editor form")
    for name, value in {"intent":"Test only", "verbal_cues":"身体朝那边，舒服地回头。", "static_steps":"先调整朝向。", "photographer_steps":"先确定构图。", "safety":"不要强扭颈部。", "fallback":"减小转身角度。", "visible_evidence":"Synthetic image, not real lighting evidence.", "interpretation":"Test reproduction plan, not original equipment.", "available_gear_plan":"One-light test plan."}.items():
        form.locator(f'[name="{name}"]').fill(value)
    page.get_by_role("button", name="保存资料卡草稿", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    assert library.stats(project["id"])["ready"] == 0
    page.get_by_role("button", name="我已核对，确认为现场卡", exact=True).click()
    page.get_by_text("已通过入库门槛，并由你确认。可加入离线拍摄包。", exact=True).wait_for()
    assert library.stats(project["id"])["ready"] == 1
    screenshot(page, "field-card-component-synthetic.png")


def test_ui_new_character_editable_note_and_blocked_job(ui):
    page, library, project = ui
    page.get_by_role("button", name="新建角色项目", exact=True).click()
    page.get_by_label("角色名 *", exact=True).fill("有马加奈")
    page.get_by_label("补充要求", exact=True).fill("日常人像和自然互动")
    page.get_by_role("button", name="建立项目", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    page.get_by_role("button", name="摄影笔记", exact=True).click()
    page.get_by_role("button", name="＋ 写摄影笔记", exact=True).click()
    page.get_by_label("笔记标题 *", exact=True).fill("引导笔记")
    page.get_by_label("正文（支持保留 Markdown）", exact=True).fill("# 观察\n<script>window.evil=1</script>\n先沟通。")
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
