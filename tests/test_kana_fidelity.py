"""Fidelity invariants are not a beauty score. Real app DOM and a synthetic DB."""
import re
from pathlib import Path
import pytest
from test_kana_presentation import kana_ui
from test_ui_components import component_factory
ROOT=Path(__file__).resolve().parents[1]

def test_single_owner_stylesheet():
    html=(ROOT/'web/index.html').read_text()
    styles=re.findall(r'href="/static/([^?\"]+)\?',html)
    assert styles==['styles.css','kana-editorial.css']
    assert not any(x in html for x in ('studio.js?','studio.css?','kana.css?','kana-atmosphere.css?','kana-painting.css?'))

@pytest.mark.parametrize('width,height',[(1672,941),(1440,900),(1366,768)])
def test_title_and_core_geometry_are_not_cosmetic_claims(kana_ui,width,height):
    page,_,_=kana_ui
    page.set_viewport_size({'width':width,'height':height})
    page.wait_for_timeout(150)
    m=page.evaluate('''()=>{const r=s=>document.querySelector(s).getBoundingClientRect();const image=r('#image-stage'), title=r('#canvas-title'),tabs=r('#view-tabs'),side=r('#detail-panel');return {image:{left:image.left,right:image.right,top:image.top,width:image.width},title:{right:title.right,bottom:title.bottom},tabs:{top:tabs.top},side:{left:side.left},width:innerWidth};}''')
    assert m['title']['bottom'] <= m['tabs']['top']+2,m
    assert .22*width <= m['image']['left'] <= .30*width,m
    assert m['image']['width'] >= .43*width,m
    assert m['side']['left'] > m['image']['right'],m

def test_no_domain_image_filter_or_forced_crop(kana_ui):
    page,_,_=kana_ui
    assert page.locator('#main-image').evaluate("n=>getComputedStyle(n).objectFit")=='contain'
    assert page.locator('#main-image').evaluate("n=>getComputedStyle(n).filter")=='none'

def test_quick_tools_are_live_after_reference_switch(kana_ui):
    page,_,_=kana_ui
    before=page.evaluate('state.activeId')
    page.locator('#next-image').click()
    assert page.evaluate('state.activeId')!=before
    page.locator('#edit-source').click()
    assert page.locator('#editor').is_visible()
    page.locator('#editor-close').click()
    assert page.locator('#canvas-filter-slot #search-ref').count()==1

def test_motion_has_painted_state_and_honors_reduction(kana_ui):
    page,_,_=kana_ui
    page.locator('#canvas-title').hover();page.wait_for_timeout(80)
    one=page.locator('.canvas-orbit').evaluate('n=>({hidden:n.hidden,items:n.children.length,transform:n.firstElementChild.style.transform})')
    page.wait_for_timeout(120)
    two=page.locator('.canvas-orbit').evaluate('n=>n.firstElementChild.style.transform')
    assert not one['hidden'] and one['items']==5 and one['transform']!=two
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function("document.querySelector('.canvas-orbit').hidden")
    assert page.locator('.canvas-orbit').evaluate('n=>n.hidden')

def test_other_view_toolbars_survive_presentation_observer(kana_ui):
    page,_,_=kana_ui
    page.evaluate("navigate('notes')")
    page.locator('#new-note').wait_for(state='visible')
    # Re-run the presentation observer after the asynchronous view mount.
    page.evaluate("document.querySelector('#view').append(document.createElement('span'))")
    page.wait_for_timeout(80)
    assert page.locator('#view > .toolbar #new-note').count()==1
    assert page.locator('#canvas-filter-slot #new-note').count()==0
    page.locator('#new-note').click()
    assert page.locator('#editor').is_visible()
    page.locator('#editor-close').click()
    page.evaluate("navigate('references')")
    page.locator('#canvas-filter-slot #search-ref').wait_for(state='visible')
