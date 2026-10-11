"""Actual HTTP/Chromium boundaries, separate from real-photo/pedagogy QA."""
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from test_learning_ui import learning_app, learning_site, _unlock

WEB = Path(__file__).resolve().parents[1] / 'web'
COURSE = 'sword-perspective-chapter'


def shipped_course() -> dict:
    """The base bundle's own course. Its shape comes from the file, not from a fixed
    chapter count, so a course rewritten into the field-guide format keeps these checks
    about behaviour instead of about a layout the author no longer uses."""
    bundle = json.loads((WEB / 'learning-atlas.json').read_text(encoding='utf-8'))
    return next(g for g in bundle['gateways'] if g['id'] == COURSE)


def field_guide(course: dict) -> bool:
    return course.get('course_format') == 'field-guide-v1'


@pytest.mark.parametrize('width,height', [(1440,1000), (390,844)])
def test_course_direct_link_keeps_map_records_and_unrevealed_transfer(learning_site, width, height):
    course = shipped_course()
    sections = [s['id'] for s in course['sections']]
    case_section = 'transfer'
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
            'revealed':[], 'last_section':sections[0]})
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
        expect(page.locator('#gateway-dialog .gateway-chapter')).to_have_count(len(sections))
        if field_guide(course):
            recipes = [b for s in course['sections'] for b in s['blocks'] if b['type'] == 'field_recipe']
            expect(page.locator('.field-recipe')).to_have_count(len(recipes))
            page.locator('.field-recipe').first.scroll_into_view_if_needed()
            expect(page.locator('.field-recipe .field-compare .gateway-case').first).to_be_visible()
            expect(page.locator('#gateway-dialog')).not_to_contain_text('未提供作者原话')
        else:
            expect(page.locator('#gateway-dialog .gateway-exercise')).to_have_count(3)
            expect(page.locator('#gw-problem .gateway-exercise')).to_contain_text('下一张只能先试一个主要变化')
        page.locator(f'[data-gw-section="{case_section}"]').click()
        expect(page.locator(f'#gw-{case_section} .gateway-case').first).to_be_visible()
        expect(page.locator(f'#gw-{case_section} .case-load-error').first).to_be_visible()
        if not field_guide(course):
            expect(page.locator(f'#gw-{case_section} .gateway-case')).to_have_count(3)
        expect(page.locator('[data-gw-reveal="transfer"]')).not_to_have_attribute('open', '')
        page.locator('#gw-transfer .gateway-exercise').scroll_into_view_if_needed()
        expect(page.locator('[data-gw-reveal="transfer"] summary')).to_be_visible()
        assert not page.locator('#gateway-dialog').evaluate('(el)=>el.scrollWidth>el.clientWidth')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.keyboard.press('Escape')
        page.locator(f'.course-index [data-open-gateway="{COURSE}"]').click()
        expect(page.locator('#gateway-dialog textarea, #gateway-form, #gateway-stage, #gateway-save, [data-gw-choice]')).to_have_count(0)
        media_section = sections[2]
        page.locator(f'[data-gw-section="{media_section}"]').click()
        note_case = page.locator(f'#gw-{media_section} [data-case="course-height"]')
        note_case.scroll_into_view_if_needed()
        expect(note_case.locator('.case-load-error').first).to_be_visible()
        assert note_case.locator('img').first.get_attribute('src').startswith('/api/learning-note-media/')
        page.locator('[data-gw-skill]').first.click()
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        expect(page.locator('#skill-status')).to_have_value('unassessed')
        assert writes == []
        assert errors == []
        assert page.request.get(origin + '/api/learning-state').json() == before
        browser.close()


def test_shipped_course_keeps_a_try_before_reveal_transfer():
    course = shipped_course()
    if field_guide(course):
        exercises = [b for s in course['sections'] for b in s['blocks'] if b.get('type') == 'exercise']
        assert [b['id'] for b in exercises] == ['transfer']
        reveals = [b for s in course['sections'] for b in s['blocks'] if b.get('type') == 'reveal']
        assert [b['activity_id'] for b in reveals] == ['transfer']
    else:
        assert 'course_format' not in course
        exercises = [b for s in course['sections'] for b in s['blocks'] if b.get('type') == 'exercise']
        assert sorted(b['id'] for b in exercises) == ['comparison', 'observation', 'transfer']


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
