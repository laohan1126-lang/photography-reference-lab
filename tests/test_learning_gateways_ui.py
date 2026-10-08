"""Real HTTP/Chromium interaction checks, not evidence of human learning."""
import json

import pytest
from playwright.sync_api import expect, sync_playwright
from fastapi.testclient import TestClient
from conftest import TOKEN, image_bytes

from test_learning_ui import learning_app, learning_site, _unlock, _open_path


def test_gateway_endpoint_requires_session_and_csrf(learning_app):
    app, _, origin, _, _ = learning_app
    with TestClient(app, base_url=origin) as client:
        from ref_lab.learning_media import SOURCE_IMAGE_CSP
        policy = client.get('/learning').headers['content-security-policy']
        reference_policy = client.get('/').headers['content-security-policy']
        assert f"img-src 'self' data: blob: {SOURCE_IMAGE_CSP};" in policy
        assert 'wikimedia' not in reference_policy
        assert "script-src 'self';" in policy and "connect-src 'self';" in policy
        gateway = client.get('/static/learning-atlas.json').json()['gateways'][0]['id']
        endpoint = '/api/learning-gateways/' + gateway
        body = {'expected_revision':0, 'stage':'terms'}
        assert client.put(endpoint, json=body).status_code == 401
        session = client.post('/api/session', json={'token':TOKEN})
        assert session.status_code == 200
        assert client.put(endpoint, json=body).status_code == 403
        assert client.get('/api/learning-state').json()['revision'] == 0
        assert client.put(endpoint, json=body, headers={'X-Lab-CSRF':session.json()['csrf']}).status_code == 200


@pytest.mark.parametrize('gateway_index', [0, 1, 2])
def test_transfer_image_is_allowed_by_the_actual_page_policy(learning_site, gateway_index):
    """Synthetic pixels exercise the browser policy; separate live QA checks real photos."""
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route('https://thumb.wikimedia.org/**', lambda route: route.fulfill(
            status=200, content_type='image/png', body=image_bytes()))
        _unlock(page, origin)
        page.locator('#gateway-index [data-open-gateway]').nth(gateway_index).click()
        page.locator('[data-gw-section="transfer"]').click()
        page.wait_for_function('() => document.querySelector("#gw-transfer img").naturalWidth > 0', timeout=5000)
        expect(page.locator('#gw-transfer img')).to_be_visible()
        expect(page.locator('#gw-transfer .case-load-error')).not_to_be_visible()
        browser.close()


@pytest.mark.parametrize('gateway_index', [0, 1, 2])
def test_original_case_photos_and_source_summaries_render_inside_each_gateway(learning_site, gateway_index):
    """Synthetic SVG responses prove inline rendering; root Edge QA checks the real source pixels."""
    from ref_lab.learning_media import SOURCE_CASE_MEDIA

    app, _, origin, _ = learning_site
    gateway_ids = ('attention-and-occlusion', 'position-before-angle', 'separate-light-contributions')
    gateway_id = gateway_ids[gateway_index]
    # Pull the actual shipped catalog so this assertion follows the gateway-to-case mapping.
    from fastapi.testclient import TestClient
    with TestClient(app, base_url=origin) as client:
        atlas = client.get('/static/learning-atlas.json').json()
    gateway = next(item for item in atlas['gateways'] if item['id'] == gateway_id)
    source_cases = [case for case in gateway['cases'] if case.get('display') == 'source_remote']
    gateway_case_ids = {case['id'] for case in source_cases}
    source_urls = {image['src'] for case in source_cases for image in case['images']}
    assert source_urls == {url for case_id in gateway_case_ids for url in SOURCE_CASE_MEDIA[case_id]}
    licensed_urls = {case['src'] for case in gateway['cases'] if case.get('display') == 'licensed_remote'}
    expected_urls = source_urls | licensed_urls
    expected_dimensions = {image['src']: (image['width'], image['height'])
                           for case in source_cases for image in case['images']}
    expected_dimensions.update({case['src']: (case['width'], case['height'])
                                for case in gateway['cases'] if case.get('display') == 'licensed_remote'})
    assert expected_urls

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        for url in expected_urls:
            page.route(url, lambda route: route.fulfill(
                status=200, content_type='image/svg+xml',
                body='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="32"><rect width="24" height="32" fill="#496b55"/></svg>'))
        _unlock(page, origin)
        page.locator('#gateway-index [data-open-gateway]').nth(gateway_index).click()
        source_figures = page.locator('.gateway-case[data-case] .case-media img')
        rendered_urls = {source_figures.nth(index).get_attribute('src')
                         for index in range(source_figures.count())}
        # A teaching case can be deliberately revisited in multiple chapters.
        assert expected_urls <= rendered_urls
        assert rendered_urls <= expected_urls
        for index in range(source_figures.count()):
            image = source_figures.nth(index)
            src = image.get_attribute('src')
            assert (int(image.get_attribute('width')), int(image.get_attribute('height'))) == expected_dimensions[src]
            image.scroll_into_view_if_needed()
            page.wait_for_function(
                '(src) => [...document.querySelectorAll(".case-media img")].some(img => img.src === src && img.complete && img.naturalWidth > 0)',
                arg=src,
            )
            expect(image).to_be_visible()
            assert image.evaluate('(img) => img.closest("a") === null')
            expect(image.locator('xpath=..').locator('.case-loading')).to_be_hidden()
        for url in expected_urls:
            assert page.locator(f'.case-media img[src="{url}"]').count() >= 1
        for case in source_cases:
            summaries = page.locator(f'.gateway-case[data-case="{case["id"]}"] details.case-source-summary')
            assert summaries.count() >= 1
            summary = summaries.first
            expect(summary.locator('summary')).to_have_text('原文要点 · 中文转述')
            summary.locator('summary').click()
            expect(summary.get_by_text(case['source_summary']['text'])).to_be_visible()
            expect(summary).to_contain_text(case['source_summary']['locator'])
        assert page.url.startswith(origin + '/learning')
        browser.close()


def test_one_original_photo_failure_keeps_sibling_images_summary_and_returning_draft(learning_site):
    from ref_lab.learning_media import SOURCE_CASE_MEDIA

    _, _, origin, _ = learning_site
    urls = SOURCE_CASE_MEDIA['hobby-ambient-sequence']
    assert len(urls) == 3
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(urls[0], lambda route: route.abort())
        for url in urls[1:]:
            page.route(url, lambda route: route.fulfill(
                status=200, content_type='image/svg+xml',
                body='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="32"><rect width="24" height="32" fill="#496b55"/></svg>'))
        _unlock(page, origin)
        page.locator('#gateway-index [data-open-gateway]').nth(2).click()
        figure = page.locator('.gateway-case[data-case="hobby-ambient-sequence"]')
        images = figure.locator('.case-media img')
        assert images.count() == 3
        figure.scroll_into_view_if_needed()
        expect(figure.locator('.case-load-error').first).to_be_visible()
        summary = figure.locator('details.case-source-summary')
        summary.locator('summary').click()
        expect(summary.get_by_text('原文要点 · 中文转述')).to_be_visible()
        expect(summary).to_contain_text('Hobby')
        for index in (1, 2):
            image = images.nth(index)
            image.scroll_into_view_if_needed()
            src = image.get_attribute('src')
            page.wait_for_function(
                '(src) => [...document.querySelectorAll(".case-media img")].some(img => img.src === src && img.complete && img.naturalWidth > 0)',
                arg=src,
            )
            expect(image).to_be_visible()
        page.locator('#gw-answer-observation').fill('原图暂时失败时，正文和其余照片仍可观察。')
        page.keyboard.press('Escape')
        page.locator('#gateway-index [data-open-gateway]').nth(2).click()
        expect(page.locator('#gw-answer-observation')).to_have_value('原图暂时失败时，正文和其余照片仍可观察。')
        browser.close()


def test_late_save_owns_its_gateway_and_preserves_newer_draft(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        page.locator('#gateway-index [data-open-gateway]').first.click()
        first = page.locator('#gateway-switch').input_value()
        ids = page.locator('#gateway-switch option').evaluate_all('(items)=>items.map(x=>x.value)')
        pending = []

        def hold_response(route):
            response = route.fetch()
            pending.append((route, response))

        page.route('**/api/learning-gateways/*', hold_response)
        page.locator('#gw-answer-observation').fill('发送时的观察')
        page.locator('[data-gw-section="reflect"]').click()
        page.locator('#gateway-save').click()
        expect(page.locator('#gateway-save')).to_be_disabled()
        page.locator('#gw-answer-observation').fill('请求途中继续修改的观察')
        page.locator('#gateway-switch').select_option(ids[1])
        page.locator('#gw-answer-observation').fill('另一个入口的独立草稿')
        assert len(pending) == 1
        pending[0][0].fulfill(response=pending[0][1])
        expect(page.locator('#gateway-save')).to_be_enabled()
        expect(page.locator('#gw-answer-observation')).to_have_value('另一个入口的独立草稿')
        page.locator('#gateway-switch').select_option(first)
        expect(page.locator('#gw-answer-observation')).to_have_value('请求途中继续修改的观察')
        expect(page.locator('#gateway-message')).to_contain_text('未保存')
        server = page.request.get(origin + '/api/learning-state').json()
        assert server['gateways'][first]['answers']['observation'] == '发送时的观察'
        assert ids[1] not in server['gateways']
        browser.close()


@pytest.mark.parametrize('gateway_index', [0, 1, 2])
def test_each_gateway_full_path_keeps_legacy_status_and_persists_observations(learning_site, gateway_index):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        _unlock(page, origin)
        atlas = page.request.get(origin + '/static/learning-atlas.json').json()
        gateway = atlas['gateways'][gateway_index]
        skill = next(s for s in atlas['skills'] if s['id'] == gateway['skill_ids'][0])
        module = next(m for m in atlas['modules'] if m['id'] == skill['module_id'])
        _open_path(page, module['domain_id'], module['id'], skill['id'])
        entry = page.locator(f'#skill-view [data-open-gateway="{gateway["id"]}"]')
        entry.click()
        expect(page.locator('#gateway-dialog')).to_be_visible()
        expect(page.locator('#gateway-title')).to_have_text(gateway['title'])
        page.locator('#gw-answer-observation').fill('先观察能看见的变量，不猜 EXIF。')
        page.locator('[data-gw-section="contrast"]').click()
        page.locator('#gw-answer-comparison').fill('对照同时改变的变量也要注明。')
        page.locator('[data-gw-section="transfer"]').click()
        expect(page.locator('[data-gw-reveal="transfer"]')).not_to_have_attribute('open', '')
        page.locator('#gw-answer-transfer').fill('新图中看到的证据与仍未知的条件。')
        page.locator('[data-gw-reveal="transfer"] summary').click()
        page.locator('[data-gw-section="reflect"]').click()
        expect(page.locator('#gateway-stage')).to_have_value('unassessed')
        page.locator('#gateway-stage').select_option('analysis')
        page.locator('#gw-confusion').fill('下次实拍验证我的解释。')
        with page.expect_response(lambda r: r.request.method == 'PUT' and '/api/learning-gateways/' in r.url) as saving:
            page.locator('#gateway-save').click()
        assert saving.value.status == 200, saving.value.text()
        expect(page.locator('#gateway-message')).to_contain_text('已保存')
        page.keyboard.press('Escape')
        expect(entry).to_be_focused()
        expect(page.locator('#skill-status')).to_have_value('unassessed')
        page.reload()
        page.locator(f'#skill-view [data-open-gateway="{gateway["id"]}"]').click()
        expect(page.locator('#gw-answer-transfer')).to_have_value('新图中看到的证据与仍未知的条件。')
        state = page.request.get(origin + '/api/learning-state').json()
        assert state['gateways'][gateway['id']]['stage'] == 'analysis'
        assert skill['id'] not in state['skills']
        browser.close()


@pytest.mark.parametrize('width,height', [(1440,1000),(390,844)])
def test_drawer_position_switching_drafts_keyboard_and_history(learning_site, width, height):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':width,'height':height})
        _unlock(page, origin)
        buttons = page.locator('#gateway-index [data-open-gateway]')
        first = buttons.nth(0)
        first.scroll_into_view_if_needed()
        before = page.evaluate('window.scrollY')
        first.focus()
        page.keyboard.press('Enter')
        page.locator('#gw-answer-observation').fill('关闭、切换和重开必须保留。')
        page.locator('[data-gw-section="transfer"]').click()
        pos = page.locator('.gateway-scroll').evaluate('(el)=>el.scrollTop')
        assert pos > 0
        page.keyboard.press('Escape')
        expect(first).to_be_focused()
        assert abs(page.evaluate('window.scrollY') - before) < 3
        first.click()
        assert abs(page.locator('.gateway-scroll').evaluate('(el)=>el.scrollTop') - pos) < 5
        expect(page.locator('#gw-answer-observation')).to_have_value('关闭、切换和重开必须保留。')
        ids = page.locator('#gateway-switch option').evaluate_all('(items)=>items.map(x=>x.value)')
        page.locator('#gateway-switch').select_option(ids[1])
        page.locator('#gw-answer-observation').fill('第二个入口独立的观察。')
        page.locator('#gateway-switch').select_option(ids[0])
        expect(page.locator('#gw-answer-observation')).to_have_value('关闭、切换和重开必须保留。')
        assert not page.locator('#gateway-dialog').evaluate('(el)=>el.scrollWidth>el.clientWidth')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.locator('#gateway-close').focus()
        page.keyboard.press('Tab')
        assert page.evaluate('document.querySelector("#gateway-dialog").contains(document.activeElement)')
        page.evaluate('location.hash="#domain=perspective"')
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        expect(page.locator('#domain-title')).to_be_visible()
        browser.close()


def test_gateway_conflict_keeps_draft_and_requires_explicit_reload(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        csrf = _unlock(page, origin)
        page.locator('#gateway-index [data-open-gateway]').first.click()
        gateway_id = page.locator('#gateway-switch').input_value()
        page.locator('#gw-answer-observation').fill('本页尚未保存的判断')
        remote = page.request.put(origin + '/api/learning-gateways/' + gateway_id,
                                  headers={'X-Lab-CSRF':csrf}, data={'expected_revision':0,'answers':{'observation':'另一页面的新记录'},'stage':'terms'})
        assert remote.status == 200
        page.locator('[data-gw-section="reflect"]').click()
        page.locator('#gateway-save').click()
        expect(page.locator('#gateway-message')).to_contain_text('服务器记录已更新')
        expect(page.locator('#gw-answer-observation')).to_have_value('本页尚未保存的判断')
        page.locator('#gateway-reload').click()
        expect(page.locator('#gw-answer-observation')).to_have_value('另一页面的新记录')
        expect(page.locator('#gateway-stage')).to_have_value('terms')
        browser.close()


def test_gateway_refresh_does_not_authorize_a_stale_skill_form(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        csrf = _unlock(page, origin)
        skill = 'perspective-skill-height-vs-pitch'
        _open_path(page, 'perspective', 'perspective-1', skill)
        page.locator('#skill-notes').fill('本页尚未保存的技能草稿')
        page.locator('#skill-view [data-open-gateway]').first.click()
        page.locator('#gw-answer-observation').fill('本页认知入口草稿')
        remote = page.request.put(origin + '/api/learning-state/' + skill,
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':0,'notes':'另一窗口的新备注'})
        assert remote.status == 200
        page.locator('[data-gw-section="reflect"]').click()
        page.locator('#gateway-save').click()
        expect(page.locator('#gateway-message')).to_contain_text('服务器记录已更新')
        page.keyboard.press('Escape')
        expect(page.locator('#skill-notes')).to_have_value('本页尚未保存的技能草稿')
        page.locator('#notes-save').click()
        expect(page.locator('#skill-save-message')).to_contain_text('核对服务器版本')
        persisted = page.request.get(origin + '/api/learning-state').json()
        assert persisted['skills'][skill]['notes'] == '另一窗口的新备注'
        page.locator('#skill-record-reload').click()
        expect(page.locator('#skill-notes')).to_have_value('另一窗口的新备注')
        page.locator('#skill-view [data-open-gateway]').first.click()
        expect(page.locator('#gw-answer-observation')).to_have_value('本页认知入口草稿')
        browser.close()
