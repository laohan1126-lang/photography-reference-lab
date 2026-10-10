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
        _unlock(page, origin)
        before = page.request.get(origin + '/api/learning-state').json()
        writes=[]
        page.on('request', lambda request: writes.append(request.url) if request.method in {'PUT','POST','DELETE'} else None)
        page.goto(origin + '/learning?course=' + COURSE)
        expect(page.locator('#gateway-dialog')).to_be_visible()
        expect(page.locator('#gateway-switch')).to_have_value(COURSE)
        expect(page.locator('#gateway-stage')).to_have_value('unassessed')
        page.locator('#gw-answer-observation').fill('有意夸张，先检验工作距离。')
        page.locator('[data-gw-section="transfer"]').click()
        expect(page.locator('#gw-transfer .gateway-case')).to_have_count(4)
        expect(page.locator('[data-gw-reveal="transfer"]')).not_to_have_attribute('open', '')
        expect(page.locator('#gw-transfer .case-load-error').first).to_be_visible()
        page.locator('#gw-answer-transfer').fill('A：先定意图；B：剑与脸分离；C：检验动作深度。')
        page.locator('[data-gw-reveal="transfer"] summary').click()
        expect(page.locator('.gateway-reading')).to_contain_text('不是作者原点评或计分考试')
        assert not page.locator('#gateway-dialog').evaluate('(el)=>el.scrollWidth>el.clientWidth')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.keyboard.press('Escape')
        page.locator(f'.course-index [data-open-gateway="{COURSE}"]').click()
        expect(page.locator('#gw-answer-observation')).to_have_value('有意夸张，先检验工作距离。')
        expect(page.locator('#gw-answer-transfer')).to_contain_text('A：先定意图')
        page.locator('[data-gw-section="principle"]').click()
        expect(page.locator('#gw-principle .case-load-error').first).to_be_visible()
        assert page.locator('#gw-principle img').first.get_attribute('src').startswith('/api/learning-note-media/')
        expect(page.locator('#gw-principle .case-playback').first).to_have_attribute(
            'href', 'https://www.bilibili.com/video/BV1od4y1n7Ag/?t=55')
        page.locator('[data-gw-section="contrast"]').click()
        expect(page.locator('#gw-contrast .case-playback').first).to_have_attribute(
            'href', 'https://www.bilibili.com/video/BV1MD421L7VK/?t=132')
        expect(page.locator('#gw-contrast .case-playback').first).to_have_text('播放出处 02:12–02:30 ↗')
        page.locator('[data-gw-skill]').first.click()
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        expect(page.locator('#skill-status')).to_have_value('unassessed')
        assert writes == []
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
