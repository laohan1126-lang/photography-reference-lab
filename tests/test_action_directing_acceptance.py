"""Independent frozen-criteria acceptance; fixture data stays in verifier .local.

Photographic truth is separately inspected in SOURCE_AUDIT.md. Aborting media here
tests a real failure fallback, never substitutes synthetic image accuracy evidence.
"""
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from test_learning_ui import learning_app, learning_site, _unlock

EVIDENCE = Path(__file__).resolve().parents[1] / '.local/verifier'
COURSE = 'action-directing-module'
SKILL = 'posing-instruction-clarity'
OLD_GATEWAY = 'attention-and-occlusion'


@pytest.mark.parametrize('width,height', [(1440,1000),(390,844)])
def test_reading_revealing_navigation_and_legacy_state_are_read_only(learning_site, width, height):
    _, data_dir, origin, _ = learning_site
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':width,'height':height})
        page.route('https://westcottu.com/**', lambda route: route.abort())
        csrf = _unlock(page, origin)
        first = page.request.put(origin+'/api/learning-state/'+SKILL,
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':0,'status':'practicing','weak':True,'focus':True,'notes':'Verifier isolated pre-existing note'})
        assert first.status == 200, first.text()
        old = page.request.put(origin+'/api/learning-gateways/'+OLD_GATEWAY,
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':1,'stage':'analysis','answers':{'observation':'Old independent fixture answer'},'revealed':['observation'],'last_section':'observe'})
        assert old.status == 200, old.text()
        log = page.request.post(origin+'/api/learning-state/'+SKILL+'/logs',
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':2,'text':'Existing isolated practice log','photo_ids':[]})
        assert log.status == 201, log.text()
        before = page.request.get(origin+'/api/learning-state').json()
        state_path = data_dir/'learning/learning-state.json'
        before_bytes = state_path.read_bytes()
        writes, errors = [], []
        page.on('request', lambda request: writes.append({'method':request.method,'url':request.url}) if request.method not in {'GET','HEAD','OPTIONS'} else None)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin+'/learning?course='+COURSE)
        expect(page.locator('#gateway-dialog')).to_be_visible()
        expect(page.locator('#gateway-switch')).to_have_value(COURSE)
        expect(page.locator('#gateway-dialog textarea, #gateway-dialog input, #gateway-form, #gateway-stage, #gateway-save, [data-gw-choice]')).to_have_count(0)
        expect(page.locator('.gateway-chapter')).to_have_count(8)
        expect(page.locator('#gateway-dialog .gateway-exercise')).to_have_count(3)
        expect(page.locator('[data-gw-reveal="transfer"]')).not_to_have_attribute('open','')
        page.screenshot(path=str(EVIDENCE/f'reader-{width}-start.png'))
        for section in ['observe','principle','contrast','boundary','transfer','reflect','sources','problem']:
            page.locator(f'[data-gw-section="{section}"]').click()
            expect(page.locator('#gw-'+section)).to_be_visible()
            assert not page.locator('#gateway-dialog').evaluate('(e)=>e.scrollWidth>e.clientWidth')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.locator('[data-gw-section="observe"]').click()
        expect(page.locator('#gw-observe .case-load-error')).to_be_visible()
        expect(page.locator('#gw-observe [data-case="action-jerry-solo"]')).to_contain_text('Jerry Ghionis')
        assert page.locator('#gw-observe a[href^="https://westcottu.com/"]').count() > 0
        case = page.locator('#gw-observe [data-case="action-jerry-solo"]')
        expect(case.locator('.case-teaching > [data-evidence-layer="observation"]')).to_contain_text('长裙覆盖腿脚')
        expect(case.locator('.case-teaching > [data-evidence-layer="advice"]')).to_contain_text('宽袖')
        expect(case.locator('.case-evidence-row:visible')).to_have_count(0)
        source_record = case.locator('.case-evidence-record')
        expect(source_record).not_to_have_attribute('open', '')
        source_record.locator('summary').click()
        expect(source_record.locator('a[href^="https://westcottu.com/"]')).to_be_visible()
        source_record.locator('summary').click()
        page.screenshot(path=str(EVIDENCE/f'reader-{width}-observe.png'))
        page.locator('[data-gw-section="transfer"]').click()
        expect(page.locator('#gw-transfer .case-load-error')).to_be_visible()
        expect(page.locator('#gw-transfer')).to_contain_text('面罩')
        fold = page.locator('[data-gw-reveal="transfer"]')
        fold.locator('summary').click()
        expect(fold).to_have_attribute('open','')
        expect(fold).to_contain_text('仅仅改变视线')
        page.screenshot(path=str(EVIDENCE/f'reader-{width}-transfer.png'))
        fold.locator('summary').click()
        expect(fold).not_to_have_attribute('open','')
        page.locator('#gateway-close').click()
        page.locator(f'.course-index [data-open-gateway="{COURSE}"]').click()
        expect(page.locator('#gateway-switch')).to_have_value(COURSE)
        page.reload()
        expect(page.locator('#gateway-dialog')).to_be_visible()
        page.locator('[data-gw-skill="'+SKILL+'"]').click()
        expect(page.locator('#gateway-dialog')).not_to_be_visible()
        expect(page.locator('#skill-status')).to_have_value('practicing')
        page.goto(origin+'/learning?course=sword-perspective-chapter')
        expect(page.locator('#gateway-switch')).to_have_value('sword-perspective-chapter')
        expect(page.locator('#gateway-dialog textarea, #gateway-stage, #gateway-save')).to_have_count(0)
        page.locator('#gateway-switch').select_option(OLD_GATEWAY)
        expect(page.locator('#gateway-switch')).to_have_value(OLD_GATEWAY)
        expect(page.locator('#gateway-dialog textarea')).to_have_count(4)
        assert page.locator('#gw-answer-observation').input_value() == 'Old independent fixture answer'
        assert writes == []
        assert errors == []
        assert page.request.get(origin+'/api/learning-state').json() == before
        assert state_path.read_bytes() == before_bytes
        # Actual revision boundary remains in place; a rejected stale edit does not mutate.
        stale = page.request.put(origin+'/api/learning-state/'+SKILL,
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':0,'status':'mastered'})
        assert stale.status == 409
        assert state_path.read_bytes() == before_bytes
        forbidden = page.request.put(origin+'/api/learning-gateways/'+COURSE,
            headers={'X-Lab-CSRF':csrf}, data={'expected_revision':3,'stage':'field'})
        assert forbidden.status == 404
        (EVIDENCE/f'isolated-readonly-{width}.json').write_text(json.dumps({'width':width,'read_writes':writes,'errors':errors,'state_bytes_unchanged':True,'revision':before['revision'],'stale_status':stale.status,'course_write_status':forbidden.status},indent=2),encoding='utf-8')
        browser.close()
