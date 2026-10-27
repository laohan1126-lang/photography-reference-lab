"""Real business renderer + TestClient + Chromium, using synthetic reference pixels.
No owner's images/databases/network model calls. Not a Windows runtime test.
"""
from __future__ import annotations
import json,os
from pathlib import Path
import pytest
from playwright.sync_api import expect
from test_ui_components import component_factory
from conftest import add_reference

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def kana_ui(component_factory,client,library,project):
    for i in range(3):add_reference(client,project,i)
    page=component_factory()
    # Shared component harness loads the same presentation layers as index.html.
    page.wait_for_function("document.querySelector('#detail-panel').dataset.kanaOrganized==='true'")
    return page,library,project

@pytest.mark.parametrize('width,height',[(1440,900),(1366,768),(1024,768)])
def test_kana_primary_controls_are_right_and_in_view(kana_ui,width,height):
    page,_,_=kana_ui
    page.set_viewport_size({'width':width,'height':height})
    page.evaluate("document.querySelector('#auto-advance').checked=false;state.autoAdvance=false")
    page.locator('[data-decision=keep]').click()
    page.wait_for_function('!state.busy')
    expect(page.locator('#make-card')).to_be_visible()
    page.wait_for_timeout(350)
    metrics=page.evaluate("""() => {
      const image=document.querySelector('#image-stage').getBoundingClientRect();
      const panel=document.querySelector('#detail-panel').getBoundingClientRect();
      return {overflow:document.documentElement.scrollWidth>innerWidth,
        image:{top:image.top,bottom:image.bottom},
        controls:[...document.querySelectorAll('.decision-bar button,.kana-primary-tools button,#make-card')].map(n=>{
          const r=n.getBoundingClientRect();const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {id:n.id||n.dataset.decision,right:r.left>=image.right,top:r.top,bottom:r.bottom,visible:!!n.offsetWidth,unclipped:r.top>=panel.top&&r.bottom<=panel.bottom,hit:!!hit&&(hit===n||n.contains(hit))};})};
    }""")
    assert not metrics['overflow'],metrics
    assert metrics['image']['bottom']<=height+1,metrics
    assert len(metrics['controls'])>=10,metrics
    assert all(x['right'] and x['top']>=0 and x['bottom']<=height+1 and x['visible'] and x['unclipped'] and x['hit'] for x in metrics['controls']),metrics
    assert page.locator('.kana-hat').count()==0
    assert page.locator('#image-stage').evaluate("n=>['none','normal','\"\"'].includes(getComputedStyle(n,'::before').content)")
    out=Path(os.environ.get('LAB_TEST_ARTIFACTS',str(ROOT/'.local/kana-tests')));out.mkdir(parents=True,exist_ok=True)
    (out/f'kana-{width}-geometry.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    page.screenshot(path=str(out/f'kana-{width}-synthetic.png'))


def test_kana_moved_actions_keep_actual_handlers(kana_ui):
    page,_,_=kana_ui
    for control in ['edit-source','review-reference','edit-card']:
        button=page.locator('#'+control)
        assert button.evaluate("n=>n.parentElement.classList.contains('kana-primary-tools')")
        button.click();expect(page.locator('#editor')).to_be_visible()
        page.locator('#editor-close').click()
    assert page.evaluate("(()=>{const ids=[...document.querySelectorAll('[id]')].map(n=>n.id);return ids.length===new Set(ids).size})()")


def test_kana_real_decisions_are_not_theme_state(kana_ui):
    page,library,_=kana_ui
    page.evaluate('state.autoAdvance=false')
    reference_id=page.evaluate('state.activeId')
    page.locator('[data-decision=maybe]').click();page.wait_for_function('!state.busy')
    assert page.evaluate('current().decision')=='maybe'
    page.locator('[data-decision=keep]').click();page.wait_for_function('!state.busy')
    assert page.evaluate('current().selected_for_project')
    assert page.evaluate('!current().card')
    assert page.evaluate('state.activeId')==reference_id


def test_kana_reduced_motion_and_missing_art(kana_ui):
    page,_,_=kana_ui
    page.emulate_media(reduced_motion='reduce')
    page.locator('#studio-collect').hover()
    assert page.locator('.kana-pointer-orbit').evaluate('n=>n.hidden')
    page.evaluate("document.querySelector('#kana-theme-image').src='data:image/png;base64,AAAA'")
    expect(page.locator('#kana-asset-notice')).to_be_visible()
    expect(page.locator('[data-decision=keep]')).to_be_visible()
    page.locator('#toggle-project-nav').click()
    expect(page.locator('#toggle-project-nav')).to_have_attribute('aria-expanded','true')
    page.keyboard.press('Escape')
    expect(page.locator('#toggle-project-nav')).to_have_attribute('aria-expanded','false')

@pytest.mark.parametrize('width,height',[(390,844),(320,720)])
def test_kana_mobile_controls_are_reachable(kana_ui,width,height):
    page,_,_=kana_ui;page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(250)
    page.evaluate("document.querySelector('.workspace').getAnimations({subtree:true}).filter(a=>a.animationName==='kana-atmosphere-breathe').forEach(a=>{a.pause();a.currentTime=12500})")
    page.wait_for_timeout(50)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    for name in ['keep','inspiration','maybe','reject']:
        box=page.locator(f'[data-decision={name}]').bounding_box()
        assert box and box['y']>=0 and box['y']+box['height']<=height
    for name in ['edit-source','review-reference','edit-card','copy-image-btn']:
        expect(page.locator('#'+name)).to_be_visible()
