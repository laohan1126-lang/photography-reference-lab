"""Rendered CSS regression for the Kana rail and expanded workspace menu."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def layout_page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as engine:
        executable = os.environ.get("LAB_CHROMIUM") or shutil.which("chromium")
        if not executable and not Path(engine.chromium.executable_path).exists():
            pytest.skip("Install Chromium to run the rendered layout regression")
        browser = engine.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        markup = re.sub(r"<link[^>]*>|<script[^>]*>.*?</script>", "", (ROOT / "web/index.html").read_text(encoding="utf-8"))
        page.set_content(markup)
        for filename in ("styles.css", "kana-editorial.css"):
            page.add_style_tag(content=(ROOT / "web" / filename).read_text(encoding="utf-8"))
        page.add_script_tag(content=(ROOT / "web/kana.js").read_text(encoding="utf-8"))
        page.evaluate(
            """() => {
          document.querySelector('#application').hidden = false;
          document.querySelector('#project-header').innerHTML = '<div><h1>安养寺姬芽</h1><p>角色参考 · 尚未制卡</p></div><div class="header-actions"><button id="collect-project" class="primary">找一批参考</button><button id="import-reference">导入参考</button><details class="project-tools"><summary>项目设置与导出</summary><button>角色与要求</button><button>离线拍摄包</button><button>变更记录</button><button>删除项目</button></details></div>';
          document.querySelector('#stats').innerHTML = '<div class="stat"><strong>1</strong><span>候选流</span></div><div class="stat"><strong>0</strong><span>待挑选</span></div>';
          document.querySelector('#project-list').innerHTML = '<div class="project-nav-row"><button class="project-link selected"><span class="project-avatar">安</span><span><strong>安养寺姬芽</strong><small>莲之空</small></span></button><button class="project-pin">☆</button></div><div class="project-nav-row"><button class="project-link"><span class="project-avatar">南</span><span><strong>南小鸟</strong><small>全部项目</small></span></button></div>';
          document.querySelector('#view').innerHTML = '<div class="toolbar"><input id="search-ref" aria-label="搜索参考" placeholder="搜索标题、作者、审美反馈"><select aria-label="选择状态"><option>全部未淘汰</option></select><button>已选 0</button></div><div id="collection-context"></div><div id="reference-empty" hidden></div><div id="reference-content" class="review-layout"><div class="image-column"><div id="stage-and-cues" class="stage-and-cues"><aside id="mobile-cues-panel" hidden></aside><div id="image-stage" class="image-stage"><span id="stage-counter"></span><button id="stage-prev-btn" class="stage-nav stage-prev" type="button">‹</button><img id="main-image" alt=""><button id="stage-next-btn" class="stage-nav stage-next" type="button">›</button><div id="missing-image" hidden></div></div></div><div id="image-caption-text"></div><div id="filmstrip" class="filmstrip" role="group"></div><div id="auto-advance"></div></div><aside id="detail-panel" class="detail-panel"><h3>开始取景</h3></aside></div>';
            }"""
        )
        yield page
        browser.close()


def _box(page, selector: str) -> dict[str, float]:
    return page.locator(selector).evaluate(
        "n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}}"
    )


def _overlap(a: dict[str, float], b: dict[str, float]) -> bool:
    return min(a["right"], b["right"]) > max(a["left"], b["left"]) and min(a["bottom"], b["bottom"]) > max(a["top"], b["top"])


def _hit(page, selector: str) -> bool:
    return page.locator(selector).evaluate(
        "n=>{const r=n.getBoundingClientRect(),hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return !!hit&&(hit===n||n.contains(hit))}"
    )


@pytest.mark.parametrize("width,height", [(1920, 1080), (1366, 768), (1528, 651)])
def test_collapsed_navigation_is_complete_and_more_workspaces_scrolls_independently(layout_page, width, height):
    page = layout_page
    page.set_viewport_size({"width": width, "height": height})
    page.evaluate("scrollTo(0,0)")

    logo = _box(page, ".brand")
    first_navigation = _box(page, ".photography-branches>[aria-current]")
    assert first_navigation["top"] >= logo["bottom"] - 1
    assert first_navigation["top"] - logo["bottom"] < 120, (width, logo, first_navigation)
    for selector in (".photography-branches", "#toggle-project-nav", "[data-view=library]", ".global-more summary"):
        assert page.locator(selector).is_visible(), selector
        assert _hit(page, selector), selector
    assert page.locator(".print-left").evaluate("n=>getComputedStyle(n).display") == "none"

    page.evaluate("scrollTo(0,326)")
    project = _box(page, "#project-navigation")
    for selector in ("[data-view=library]", ".global-more summary"):
        assert page.locator(selector).is_visible(), selector
    assert max(_box(page, "[data-view=library]")["bottom"], _box(page, ".global-more")["bottom"]) <= project["top"]

    page.evaluate("scrollTo(0,0)")
    collapsed_top = _box(page, "#project-navigation")["top"]
    assert page.locator("#project-navigation").evaluate("n=>n.closest('.sidebar')!==null")
    more = page.locator(".global-more")
    page.locator(".global-more summary").click()
    assert more.evaluate("n=>n.open")

    menu = _box(page, ".global-more")
    assert _box(page, "#project-navigation")["top"] > collapsed_top
    title_gap = _box(page, ".index-heading")["top"] - menu["bottom"]
    assert title_gap < 48, (width, menu, _box(page, ".index-heading"))
    for selector in ("#collect-project", "#import-reference", "#project-navigation .project-tools summary"):
        assert not _overlap(menu, _box(page, selector)), (selector, menu, _box(page, selector))
    flow = more.evaluate("n=>({clientHeight:n.clientHeight,scrollHeight:n.scrollHeight,overflow:getComputedStyle(n).overflowY})")
    assert flow["overflow"] == "auto" and 0 < flow["clientHeight"] < flow["scrollHeight"], flow

    for selector in ("[data-view=study]", "[data-view=notes]", "#lock-library"):
        more.locator(selector).scroll_into_view_if_needed()
        assert _hit(page, selector), selector

    for selector in ("#collect-project", "#import-reference", "#project-navigation .project-tools summary"):
        page.locator(selector).scroll_into_view_if_needed()
        assert _hit(page, selector), selector

    more.locator("summary").click()
    assert not more.evaluate("n=>n.open")
    page.evaluate("scrollTo(0,0)")
    assert _box(page, "#project-navigation")["top"] == collapsed_top


def test_mobile_drawer_more_workspaces_remains_reachable(layout_page):
    page = layout_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#toggle-project-nav").click()
    page.wait_for_timeout(50)
    more = page.locator(".global-more")
    page.locator(".global-more summary").click()
    page.wait_for_timeout(50)
    assert "nav-open" in page.locator("body").get_attribute("class")
    for selector in ("#learning-link", "#lock-library", "#project-header", "#search-ref"):
        page.locator(selector).scroll_into_view_if_needed()
        assert page.locator(selector).is_visible(), selector
        assert _hit(page, selector), selector
    assert page.locator(".print-left").evaluate("n=>getComputedStyle(n).display") == "none"
