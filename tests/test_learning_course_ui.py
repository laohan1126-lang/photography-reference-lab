"""Actual HTTP/Chromium boundaries, separate from real-photo/pedagogy QA."""
import pytest
from playwright.sync_api import expect, sync_playwright

from test_learning_ui import learning_app, learning_site, _unlock

COURSE = 'sword-perspective-chapter'


@pytest.mark.parametrize('width,height', [(1440,1000), (390,844)])
def test_course_direct_link_keeps_map_records_and_unrevealed_transfer(learning_site, width, height):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':width, 'height':height})
        page.route('https://cosplaymode.net/**', lambda route: route.abort())
        csrf = _unlock(page, origin)
        # Existing owner records survive the presentation change; only fixture data is written.
        previous = page.request.put(origin + '/api/learning-gateways/' + COURSE,
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':0, 'stage':'analysis',
            'answers':{'observation':'先前的观察', 'transfer':'先前的新图判断', 'confusion':'先前的疑问'},
            'revealed':[], 'last_section':'problem'})
        assert previous.status == 200
        before = page.request.get(origin + '/api/learning-state').json()
        writes=[]
        errors=[]
        page.on('request', lambda request: writes.append(request.url) if request.method in {'PUT','POST','DELETE'} else None)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/learning?course=' + COURSE)
        expect(page.locator('#gateway-dialog')).to_be_visible()
        expect(page.locator('#gateway-switch')).to_have_value(COURSE)
        expect(page.locator('#gateway-dialog textarea, #gateway-form, #gateway-stage, #gateway-save, [data-gw-choice]')).to_have_count(0)
        expect(page.locator('#gateway-dialog .gateway-exercise')).to_have_count(3)
        expect(page.locator('#gw-problem .gateway-exercise')).to_contain_text('下一张只能先试一个主要变化')
        page.locator('[data-gw-section="transfer"]').click()
        expect(page.locator('#gw-transfer .gateway-case')).to_have_count(3)
        expect(page.locator('[data-gw-reveal="transfer"]')).not_to_have_attribute('open', '')
        expect(page.locator('#gw-transfer .case-load-error').first).to_be_visible()
        expect(page.locator('#gw-transfer .gateway-exercise')).to_contain_text('A若拍沉着的剑士')
        page.locator('[data-gw-reveal="transfer"] summary').click()
        expect(page.locator('.gateway-reading')).to_contain_text('不是作者原点评或计分考试')
        assert not page.locator('#gateway-dialog').evaluate('(el)=>el.scrollWidth>el.clientWidth')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.keyboard.press('Escape')
        page.locator(f'.course-index [data-open-gateway="{COURSE}"]').click()
        expect(page.locator('#gateway-dialog textarea, #gateway-form, #gateway-stage, #gateway-save, [data-gw-choice]')).to_have_count(0)
        expect(page.locator('[data-gw-reveal="transfer"]')).to_have_attribute('open', '')
        page.locator('[data-gw-section="principle"]').click()
        expect(page.locator('#gw-principle .case-load-error').first).to_be_visible()
        assert page.locator('#gw-principle img').first.get_attribute('src').startswith('/api/learning-note-media/')
        page.locator('[data-gw-skill]').first.click()
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        expect(page.locator('#skill-status')).to_have_value('unassessed')
        assert writes == []
        assert errors == []
        assert page.request.get(origin + '/api/learning-state').json() == before
        browser.close()


def test_unknown_course_parameter_does_not_open_a_different_course(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page()
        _unlock(page, origin)
        page.goto(origin + '/learning?course=unregistered-course')
        page.locator('#domain-grid').wait_for()
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        browser.close()
