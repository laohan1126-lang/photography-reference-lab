from __future__ import annotations

import asyncio
import random
import socket
import shutil
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright

from ref_lab.api import create_app
from ref_lab.config import Settings
from conftest import TOKEN, image_bytes
from test_browser import browser_page, live_site, unlock as unlock_reference_app


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
LOW_VIEW_SKILL = "perspective-gap-skill-low-view-expression-context"


@pytest.fixture
def learning_app(tmp_path):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    web = tmp_path / "web"
    shutil.copytree(WEB, web)
    app = create_app(Settings(tmp_path / "data", TOKEN, public_origin=origin, web_dir=web))
    response_gate = {"entered": threading.Event(), "release": threading.Event()}

    @app.middleware("http")
    async def hold_test_response(request, call_next):
        response = await call_next(request)
        if (request.method == "PUT" and request.url.path == f"/api/learning-state/{LOW_VIEW_SKILL}"
                and request.headers.get("x-test-hold-response") == "1"):
            response_gate["entered"].set()
            await asyncio.to_thread(response_gate["release"].wait, 10)
        return response

    yield app, tmp_path / "data", origin, listener, response_gate
    listener.close()


@pytest.fixture
def learning_site(learning_app):
    app, data_dir, origin, listener, response_gate = learning_app
    config = uvicorn.Config(app, log_level="error", lifespan="on")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started, "learning UI server did not start"
    try:
        yield app, data_dir, origin, response_gate
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _unlock(page, origin):
    session = page.request.post(origin + "/api/session", data={"token": TOKEN})
    assert session.status == 200, session.text()
    page.set_extra_http_headers({"X-Lab-CSRF": session.json()["csrf"]})
    page.goto(origin + "/learning")
    page.locator("#domain-grid").wait_for()
    return session.json()["csrf"]


def _open_path(page, domain, module, skill):
    page.locator('.brand-mark').click()
    page.locator(f'.domain-link[data-domain="{domain}"]').click()
    assert page.url.endswith(f"#domain={domain}")
    page.locator(f'.module-link[data-module="{module}"]').click()
    assert page.url.endswith(f"#module={module}")
    page.locator(f'.skill-open[data-skill="{skill}"]').first.click()
    assert page.url.endswith(f"#skill={skill}")


def _mutate_and_wait(page, method, path_suffix, action):
    with page.expect_response(
        lambda response: response.request.method == method and path_suffix in response.url
    ) as pending:
        action()
    response = pending.value
    assert response.status == 200, response.text()


def test_real_atlas_has_14_domains_and_five_reproducible_unassessed_paths(learning_app):
    app, data_dir, origin, _, _ = learning_app
    with TestClient(app, base_url=origin) as client:
        bundle_response = client.get("/static/learning-atlas.json")
    assert bundle_response.status_code == 200, bundle_response.text
    atlas = bundle_response.json()
    assert len(atlas["domains"]) == 14
    assert len(atlas["modules"]) == 71
    assert len(atlas["skills"]) >= 246
    assert len({item["id"] for item in atlas["domains"]}) == 14
    assert all(skill.get("initial_status", "unassessed") == "unassessed" for skill in atlas["skills"])
    domain_ids = {item["id"] for item in atlas["domains"]}
    module_map = {item["id"]: item for item in atlas["modules"]}
    skill_map = {item["id"]: item for item in atlas["skills"]}
    assert all(module["domain_id"] in domain_ids for module in atlas["modules"])
    assert all(skill["module_id"] in module_map for skill in atlas["skills"])

    paths = [
        ("composition", "composition-1", "composition-edge-sweep"),
        ("perspective", "perspective-1", "perspective-skill-height-vs-pitch"),
        ("posing", "posing-5", "posing-hand-orientation"),
        ("natural-light", "natural-light-5", "light-022"),
        ("costume", "costume-2", "cosplay-c06-large-prop-pose-variants"),
    ]
    for domain_id, module_id, skill_id in paths:
        assert module_map[module_id]["domain_id"] == domain_id
        assert skill_map[skill_id]["module_id"] == module_id


def test_unreadable_private_state_is_not_presented_as_unassessed(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/api/learning-state", lambda route: route.fulfill(
            status=503, content_type="application/json", body='{"detail":"state unavailable"}'))
        _unlock(page, origin)
        page.locator('.domain-link[data-domain="perspective"]').click()
        page.locator('.module-link[data-module="perspective-1"]').click()
        expect(page.locator('#status-filter')).to_be_disabled()
        expect(page.locator('.skill-row .status-label').first).to_have_text('状态不可读')
        assert page.locator('.skill-row[data-status="unassessed"]').count() == 0
        browser.close()


def test_learning_ui_five_paths_search_under_30_seconds_and_focus_navigation(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        media_methods = []
        page.on("request", lambda request: media_methods.append(request.method) if "/api/learning-preview" in request.url else None)
        _unlock(page, origin)
        atlas = page.request.get(origin + "/static/learning-atlas.json").json()
        rng = random.Random(20261008)
        sampled = rng.sample(atlas["skills"], 5)
        modules = {module["id"]: module for module in atlas["modules"]}
        paths = [(modules[skill["module_id"]]["domain_id"], skill["module_id"], skill["id"]) for skill in sampled]
        print(f"seed=20261008 sampled_skill_ids={[skill['id'] for skill in sampled]}")
        assert page.locator("#domain-grid .domain-placeholder").count() > 0
        for domain, module, skill in paths:
            _open_path(page, domain, module, skill)
            assert page.locator("#skill-status").input_value() == "unassessed"
        assert media_methods and set(media_methods).issubset({"GET", "HEAD"}), media_methods

        page.locator("#recent-toggle").click()
        page.locator(f'#recent-panel .skill-open[data-skill="{paths[-1][2]}"]').click()
        assert page.url.endswith(f"#skill={paths[-1][2]}")

        page.go_back()
        assert page.url.endswith(f"#module={paths[-1][1]}")
        page.go_forward()
        assert page.url.endswith(f"#skill={paths[-1][2]}")

        started = time.monotonic()
        page.locator("#search").fill("仰拍为什么没有气势")
        problem = page.locator('.result-row[data-problem]').filter(has_text="低机位没有产生气势").first
        problem.wait_for()
        problem.click()
        page.locator(f'#problem-view .skill-open[data-skill="{LOW_VIEW_SKILL}"]').click()
        assert page.url.endswith(f"#skill={LOW_VIEW_SKILL}")
        assert time.monotonic() - started < 30

        _mutate_and_wait(page, "PUT", f"/api/learning-state/{LOW_VIEW_SKILL}", page.locator("#skill-focus").click)
        page.locator("#skill-focus[aria-pressed='true']").wait_for()
        page.locator('.brand-mark').click()
        page.locator("#next-practice").get_by_text("你的重点").wait_for()
        page.locator(f'#next-practice .skill-open[data-skill="{LOW_VIEW_SKILL}"]').click()
        assert page.url.endswith(f"#skill={LOW_VIEW_SKILL}")
        browser.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_reference_viewer_escape_focus_and_learning_roundtrip(live_site, browser_page, width):
    url, _, _ = live_site
    page, _ = browser_page
    page.set_viewport_size({"width": width, "height": 900})
    unlock_reference_app(page, url)
    opener = page.locator("#view-original")
    opener.focus()
    opener.click()
    dialog = page.locator("#lightbox")
    expect(dialog).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(opener).to_be_focused()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

    page.locator("#learning-link").click()
    expect(page.locator("#domain-grid")).to_be_visible()
    _open_path(page, "perspective", "perspective-1", "perspective-skill-height-vs-pitch")
    assert page.locator("#skill-status").input_value() == "unassessed"
    page.locator("#reference-link").click()
    expect(page.locator("#application")).to_be_visible()
    assert len(page.context.pages) == 1
    page.go_back()
    expect(page.locator("#skill-view")).to_be_visible()
    assert page.url.endswith("#skill=perspective-skill-height-vs-pitch")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_learning_api_private_csrf_allowlist_and_no_owner_library_mutation(learning_app):
    app, data_dir, origin, _, _ = learning_app
    library_db = data_dir / "library.sqlite3"
    with TestClient(app, base_url=origin) as client:
        public = client.get("/static/learning-atlas.json")
        assert public.status_code == 200
        assert len(public.json()["skills"]) >= 246
        before_db = library_db.read_bytes() if library_db.exists() else None
        for path in ("/api/learning-state", f"/api/learning-state/{LOW_VIEW_SKILL}", "/api/learning-photos/example.jpg"):
            assert client.get(path).status_code in (401, 404)
        assert client.get("/api/learning-preview").status_code == 401
        assert client.get("/api/learning-preview/P1.png").status_code == 401
        for path in ("/api/learning-state", f"/api/learning-state/{LOW_VIEW_SKILL}"):
            assert client.put(path, json={"expected_revision": 0, "status": "learning"}).status_code in (401, 404, 405)
        for path in ("/static/library.sqlite3", "/static/learning-state.json", "/static/access-token"):
            assert client.get(path).status_code == 404

        session = client.post("/api/session", json={"token": TOKEN})
        assert session.status_code == 200, session.text
        csrf = session.json()["csrf"]
        state = client.get("/api/learning-state")
        assert state.status_code == 200, state.text
        assert client.get("/api/learning-preview").json() == {"items": []}
        for path in ("/api/learning-preview/manifest.json", "/api/learning-preview/P1.txt", "/api/learning-preview/%2e%2e%2faccess-token"):
            assert client.get(path).status_code == 404
        revision = state.json()["revision"]
        bad_csrf = client.put(f"/api/learning-state/{LOW_VIEW_SKILL}", json={"expected_revision": revision, "status": "learning"})
        assert bad_csrf.status_code == 403
        client.headers["X-Lab-CSRF"] = csrf
        updated = client.put(
            f"/api/learning-state/{LOW_VIEW_SKILL}",
            json={"expected_revision": revision, "status": "learning", "weak": True, "focus": True, "notes": "测试备注"},
        )
        assert updated.status_code == 200, updated.text
        unknown = client.put("/api/learning-state/not-a-real-skill", json={"expected_revision": updated.json()["revision"], "status": "learning"})
        assert unknown.status_code == 404
        assert client.get("/api/assets").status_code in (404, 405)
    after_db = library_db.read_bytes() if library_db.exists() else None
    assert before_db == after_db


def test_browser_state_log_and_synthetic_photo_persist_without_auto_promotion(learning_site):
    _, data_dir, origin, _ = learning_site
    library_db = data_dir / "library.sqlite3"
    before_db = library_db.read_bytes() if library_db.exists() else None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        writes = []
        page.on("request", lambda request: writes.append((request.method, request.url)) if request.method in {"POST", "PUT", "PATCH", "DELETE"} else None)
        _unlock(page, origin)
        _open_path(page, "perspective", "perspective-1", LOW_VIEW_SKILL)
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{LOW_VIEW_SKILL}", lambda: page.locator("#skill-status").select_option("learning"))
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{LOW_VIEW_SKILL}", page.locator("#skill-weak").click)
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{LOW_VIEW_SKILL}", page.locator("#skill-focus").click)
        page.locator("#skill-notes").fill("先比较相机高度，再单独调整俯仰。")
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{LOW_VIEW_SKILL}", page.locator("#notes-save").click)
        page.locator("#record-open").click()
        page.locator("#record-text").fill("在现场做了高低机位对照。")
        page.locator("#record-caption").fill("仅验证上传流程的合成 PNG")
        page.locator("#record-photo").set_input_files({
            "name": "synthetic-test.png", "mimeType": "image/png", "buffer": image_bytes(91, (80, 100))
        })
        with page.expect_response(lambda response: response.request.method == "POST" and f"/api/learning-state/{LOW_VIEW_SKILL}/photos" in response.url) as photo_response:
            with page.expect_response(lambda response: response.request.method == "POST" and f"/api/learning-state/{LOW_VIEW_SKILL}/logs" in response.url) as log_response:
                page.locator("#record-save").click()
        assert photo_response.value.status == 201, photo_response.value.text()
        assert log_response.value.status == 201, log_response.value.text()
        page.locator("#record-list").get_by_text("在现场做了高低机位对照。").wait_for()
        page.reload()
        _unlock(page, origin)
        page.goto(origin + f"/learning#skill={LOW_VIEW_SKILL}")
        page.locator("#skill-status").wait_for()
        assert page.locator("#skill-status").input_value() == "learning"
        assert page.locator("#skill-weak").get_attribute("aria-pressed") == "true"
        assert page.locator("#skill-focus").get_attribute("aria-pressed") == "true"
        assert page.locator("#skill-notes").input_value() == "先比较相机高度，再单独调整俯仰。"
        assert page.locator("#record-list").get_by_text("在现场做了高低机位对照。").count() == 1
        assert page.locator("#record-list img").count() == 1
        photo_opener = page.locator(".personal-photo-open[data-photo-id]").first
        photo_opener.focus()
        photo_opener.click()
        photo_dialog = page.locator("#photo-dialog")
        expect(photo_dialog).to_be_visible()
        expect(page.locator("#photo-view-image")).to_be_visible()
        page.keyboard.press("Escape")
        expect(photo_dialog).not_to_be_visible()
        expect(photo_opener).to_be_focused()
        assert page.locator("#next-practice").get_by_text("你的重点").count() >= 1
        photo_paths = list((data_dir / "learning" / "photos").glob("*"))
        assert len(photo_paths) == 1
        assert photo_paths[0].read_bytes() == image_bytes(91, (80, 100))
        assert writes
        assert all(url.startswith(origin + "/api/session") or url.startswith(origin + f"/api/learning-state/{LOW_VIEW_SKILL}") for _, url in writes)
        browser.close()
    after_db = library_db.read_bytes() if library_db.exists() else None
    assert before_db == after_db


def test_delayed_skill_response_cannot_overwrite_current_skill_state(learning_site):
    _, _, origin, response_gate = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        csrf = _unlock(page, origin)
        skill_b = "perspective-skill-height-vs-pitch"
        _open_path(page, "perspective", "perspective-1", skill_b)
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{skill_b}", lambda: page.locator("#skill-status").select_option("practicing"))
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{skill_b}", page.locator("#skill-weak").click)
        _mutate_and_wait(page, "PUT", f"/api/learning-state/{skill_b}", page.locator("#skill-focus").click)

        page.evaluate("location.hash = '#map'")
        page.locator("#domain-grid").wait_for()
        _open_path(page, "perspective", "perspective-1", LOW_VIEW_SKILL)
        page.set_extra_http_headers({"X-Lab-CSRF": csrf, "X-Test-Hold-Response": "1"})
        page.locator("#skill-status").select_option("learning")
        assert response_gate["entered"].wait(10), "server never reached the delayed response gate"
        page.set_extra_http_headers({"X-Lab-CSRF": csrf})
        page.evaluate(f"location.hash = '#skill={skill_b}'")
        expect(page.locator("#skill-status")).to_have_value("practicing")
        expect(page.locator("#skill-weak")).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#skill-focus")).to_have_attribute("aria-pressed", "true")
        with page.expect_response(lambda response: response.request.method == "PUT" and f"/api/learning-state/{LOW_VIEW_SKILL}" in response.url) as pending:
            response_gate["release"].set()
        assert pending.value.status == 200
        expect(page.locator("#skill-status")).to_be_enabled()
        expect(page.locator("#skill-status option")).to_have_count(6)
        expect(page.locator("#skill-status")).to_have_value("practicing")
        expect(page.locator("#skill-weak")).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#skill-focus")).to_have_attribute("aria-pressed", "true")
        persisted = page.request.get(origin + "/api/learning-state").json()
        assert persisted["skills"][skill_b]["status"] == "practicing"
        assert persisted["skills"][skill_b]["weak"] is True
        assert persisted["skills"][skill_b]["focus"] is True
        assert persisted["skills"][LOW_VIEW_SKILL]["status"] == "learning"
        browser.close()


def test_conflicting_notes_save_keeps_unsaved_draft(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        csrf = _unlock(page, origin)
        skill_b = "perspective-skill-height-vs-pitch"
        _open_path(page, "perspective", "perspective-1", skill_b)
        draft = "保留这段尚未保存的冲突备注。"
        page.locator("#skill-notes").fill(draft)

        current = page.request.get(origin + "/api/learning-state").json()
        external_update = page.request.put(
            origin + f"/api/learning-state/{LOW_VIEW_SKILL}",
            data={"expected_revision": current["revision"], "status": "learning"},
            headers={"X-Lab-CSRF": csrf},
        )
        assert external_update.status == 200, external_update.text()
        with page.expect_response(lambda response: response.request.method == "PUT" and f"/api/learning-state/{skill_b}" in response.url) as conflict:
            page.locator("#notes-save").click()
        assert conflict.value.status == 409, conflict.value.text()
        expect(page.locator("#skill-notes")).to_have_value(draft)
        browser.close()


def test_reference_links_are_source_backed_and_mobile_navigation_has_no_horizontal_overflow(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        _unlock(page, origin)
        _open_path(page, "perspective", "perspective-1", LOW_VIEW_SKILL)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        links = page.locator("#skill-view a[href^='http']")
        count = links.count()
        assert count > 0
        for index in range(count):
            link = links.nth(index)
            assert link.get_attribute("target") == "_blank"
            rel = set((link.get_attribute("rel") or "").split())
            assert {"noopener", "noreferrer"}.issubset(rel)
        browser.close()


def test_routes_have_one_visible_view_and_reset_scroll_after_bottom_card(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        _unlock(page, origin)
        page.locator('.domain-link').last.click()
        expect(page.locator('#domain-view')).to_be_visible()
        assert page.locator('#domain-title').bounding_box()['y'] >= 0
        assert page.locator('#domain-title').bounding_box()['y'] < 400
        page.locator('#search').fill('匕首')
        page.locator('#search-results a.result-gap').first.click()
        expect(page.locator('#problem-view')).to_be_visible()
        expect(page.locator('#map-view')).not_to_be_visible()
        assert page.locator('#problem-title').bounding_box()['y'] < 400
        browser.close()


def test_personal_filter_is_a_history_route_and_home_resets_it(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        page.locator('[data-mine-filter="unassessed"]').click()
        expect(page.locator('#mine-view')).to_be_visible()
        assert '#mine=' in page.url
        page.locator('.brand-mark').click()
        expect(page.locator('#home-view')).to_be_visible()
        expect(page.locator('#mine-view')).not_to_be_visible()
        page.go_back()
        expect(page.locator('#mine-view')).to_be_visible()
        expect(page.locator('#home-view')).not_to_be_visible()
        browser.close()


def test_practice_dialog_keeps_originating_skill_when_history_changes(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        first = 'perspective-skill-height-vs-pitch'
        _open_path(page, 'perspective', 'perspective-1', first)
        page.locator('#record-open').click()
        page.locator('#record-text').fill('这条记录属于打开对话框时的相机高度技能。')
        # Browser history can change behind a modal without clicking inert page content.
        page.evaluate(f"location.hash = '#skill={LOW_VIEW_SKILL}'")
        expect(page.locator('#skill-title')).to_have_text('按人物姿态与场景判断低视点的表达效果')
        with page.expect_response(lambda response: response.request.method == 'POST' and '/logs' in response.url) as saved:
            page.locator('#record-save').click()
        assert saved.value.status == 201
        stored = page.request.get(origin + '/api/learning-state').json()['skills']
        assert stored.get(first, {}).get('logs'), 'practice log must stay with the skill named by the dialog'
        assert not stored.get(LOW_VIEW_SKILL, {}).get('logs')
        browser.close()


@pytest.mark.parametrize('width', [1440, 390])
def test_companion_materials_are_actionable_and_preserve_research_and_navigation(learning_site, width):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': width, 'height': 900})
        _unlock(page, origin)
        atlas = page.request.get(origin + '/static/learning-atlas.json').json()
        skill = 'perspective-skill-angle-comparison'
        page.goto(origin + f'/learning#skill={skill}')
        page.locator('[data-section-target="skill-tutorials"]').click()
        companions = page.locator('#skill-tutorials')
        expect(companions.locator('[data-tutorial]').first).to_be_visible()
        expect(companions.get_by_text('从这里开始', exact=True).first).to_be_visible()
        expect(companions.get_by_text('看完试一遍', exact=True).first).to_be_visible()
        expected_links = {item['url'] for item in atlas['tutorials'] if skill in item['skill_ids']}
        actual_links = companions.locator('h3 a').evaluate_all('(links) => links.map(link => link.href)')
        assert set(actual_links) == expected_links
        before = page.url
        page.locator('[data-section-target="skill-research"]').click()
        expect(page.locator('#skill-research')).to_have_attribute('open', '')
        expect(page.locator('#skill-research .source-link').first).to_be_visible()
        assert page.url == before, 'section navigation must not replace the skill route'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')

        video = next(item for item in atlas['tutorials'] if item['verification']['level'] == 'page_and_description')
        page.goto(origin + '/learning#skill=' + video['skill_ids'][0])
        page.locator('[data-section-target="skill-tutorials"]').click()
        page.locator('#skill-tutorials').wait_for()
        more = page.locator('#skill-tutorials .more-tutorials')
        if more.count():
            more.locator(':scope > summary').click()
        recommendation = page.locator(f'[data-tutorial="{video["id"]}"]')
        expect(recommendation).to_be_visible()
        expect(recommendation.locator('.tutorial-check > summary')).to_contain_text('已核对简介，未观看')
        expect(page.locator('#skill-status')).to_have_value('unassessed')

        curated_ids = {ident for item in atlas['tutorials'] for ident in item['skill_ids']}
        fallback = next(item for item in atlas['skills'] if item['id'] not in curated_ids)
        page.goto(origin + '/learning#skill=' + fallback['id'])
        page.locator('[data-section-target="skill-tutorials"]').click()
        expect(page.locator('#skill-tutorials')).to_contain_text('尚未精选到专门教程')
        expect(page.locator('#skill-tutorials .original-reading a').first).to_be_visible()
        assert page.locator('#skill-tutorials [data-tutorial]').count() == 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        browser.close()


def test_shared_textbook_does_not_attach_unrelated_conflicts_to_a_skill(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        _open_path(page, 'perspective', 'perspective-1', 'perspective-skill-height-vs-pitch')
        expect(page.locator('#skill-view')).not_to_contain_text('浅景深与主体清晰范围')
        page.goto(origin + '/learning#skill=perspective-skill-crop-height')
        expect(page.locator('#skill-view')).to_contain_text('肖像机位高度建议')
        page.goto(origin + '/learning#skill=mot-03')
        expect(page.locator('#skill-view')).to_contain_text('静态照片里追随摇摄与固定机位长曝光都能表现运动')
        page.locator('[data-section-target="skill-research"]').click()
        conflict = page.locator('#skill-view .evidence-item').filter(has_text='静态照片里追随摇摄与固定机位长曝光都能表现运动')
        conflict.get_by_text('关联来源', exact=True).click()
        expect(conflict.locator('a.source-link')).to_have_count(4)
        browser.close()
