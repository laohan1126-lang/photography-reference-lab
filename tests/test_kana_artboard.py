"""Chromium checks for the accepted Kana painting, using synthetic business fixtures."""
from pathlib import Path

import pytest
from test_kana_presentation import kana_ui
from test_ui_components import component_factory

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("width,height", [(1440, 900), (1366, 768)])
def test_artboard_visual_layers_and_real_actions(kana_ui, width, height):
    page, _, _ = kana_ui
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_function("document.documentElement.dataset.kanaArtboard === 'approved-concept'")
    page.wait_for_timeout(180)
    result = page.evaluate("""() => {
      const image=document.querySelector('#image-stage').getBoundingClientRect();
      const controls=[...document.querySelectorAll('.decision-bar button,.kana-primary-tools button')];
      return {
        overflow:document.documentElement.scrollWidth>innerWidth,
        imageBottom:image.bottom,
        imageRight:image.right,
        words:document.querySelectorAll('.artboard-arima,.artboard-kana').length,
        controls:controls.map(c=>{
          const r=c.getBoundingClientRect();
          return {left:r.left,top:r.top,bottom:r.bottom,visible:r.width>0&&r.height>0};
        })
      };
    }""")
    assert not result["overflow"], result
    assert result["words"] == 2
    assert result["imageBottom"] <= height + 1, result
    assert len(result["controls"]) >= 4
    assert all(x["visible"] and x["left"] >= result["imageRight"] - 1 and x["top"] >= 0 and x["bottom"] <= height + 1 for x in result["controls"]), result


@pytest.mark.parametrize("width,height", [(390, 844), (320, 750)])
def test_artboard_mobile_decisions_stay_in_viewport(kana_ui, width, height):
    page, _, _ = kana_ui
    page.set_viewport_size({"width":width, "height":height})
    page.wait_for_timeout(180)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    for action in ("keep","inspiration","maybe","reject"):
        rect=page.locator(f'.decision-bar [data-decision="{action}"]').bounding_box()
        assert rect and rect["y"] >= 0 and rect["y"] + rect["height"] <= height, (action, rect)


def test_artboard_remains_presentation_only(kana_ui):
    page, _, _ = kana_ui
    assert page.locator(".kana-editorial-lettering").count() == 1
    assert page.locator("#main-image").count() == 1
    assert page.locator(".decision-bar button").count() == 4
    assert page.evaluate("""() => {
      const ids=[...document.querySelectorAll('[id]')].map(n=>n.id);
      return ids.length===new Set(ids).size;
    }""")
    js=(ROOT/"web"/"kana-artboard.js").read_text(encoding="utf-8")
    assert "fetch(" not in js and "/api/" not in js
    assert (ROOT/"web/ui-art/kana-artboard-arima.svg").is_file()
    assert (ROOT/"web/ui-art/kana-artboard-kana.svg").is_file()
