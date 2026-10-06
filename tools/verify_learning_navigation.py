"""Read-only browser check of the two running local photography workspaces.

Only the learning prototype's tab-local recent history is edited. No reference-library
decisions are submitted. Screenshots remain under the ignored .local directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def loopback_url(value):
    url = urlsplit(value)
    if url.scheme != 'http' or url.hostname not in {'localhost', '127.0.0.1'} or url.username or url.password:
        raise argparse.ArgumentTypeError('Use a local HTTP workspace URL')
    return value


def verify(learning_url, reference_url, output):
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        try:
            for width in (1440, 390):
                context = browser.new_context(viewport={'width': width, 'height': 900})
                page = context.new_page()
                errors, writes = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: writes.append(request.url) if request.method not in {'GET', 'HEAD', 'OPTIONS'} else None)
                page.goto(learning_url + '#map')
                expect(page.locator('#topic-grid a[data-topic]')).to_have_count(10)
                page.locator('#topic-grid img').evaluate_all('(images)=>Promise.all(images.map(i=>i.decode()))')
                page.screenshot(path=str(output / f'map-{width}.png'), full_page=True)
                page.locator('#topic-grid a[data-topic="perspective"]').click()
                page.locator('#case-gallery img').evaluate_all('(images)=>Promise.all(images.map(i=>i.decode()))')
                return_url, title = page.url, page.locator('#topic-title').inner_text()
                page.screenshot(path=str(output / f'topic-{width}.png'))
                page.screenshot(path=str(output / f'topic-full-{width}.png'), full_page=True)
                opener = page.locator('#case-gallery .case-open[data-case="0"]')
                opener.click()
                expect(page.locator('#case-viewer')).to_be_visible()
                page.locator('#viewer-image').evaluate('(i)=>i.decode()')
                page.screenshot(path=str(output / f'case-{width}.png'))
                page.keyboard.press('Escape')
                expect(page.locator('#case-viewer')).not_to_be_visible()
                assert opener.evaluate('(element)=>element===document.activeElement')
                for cycle in range(2):
                    page.locator('#reference-link').click()
                    expect(page.locator('#application')).to_be_visible()
                    assert urlsplit(page.url).netloc == urlsplit(reference_url).netloc
                    link = page.get_by_role('link', name='摄影学习', exact=False)
                    expect(link).to_be_visible(timeout=3000)
                    assert link.get_attribute('target') != '_blank'
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    if cycle == 0:
                        page.reload()
                        expect(link).to_be_visible()
                        # Keep the return entrance in the screenshot on narrow screens.
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(output / f'reference-nav-{width}.png'))
                    link.click()
                    expect(page).to_have_url(return_url)
                    expect(page.locator('#topic-title')).to_have_text(title)
                    expect(page.locator('#research-note')).to_contain_text('低机位不等于必须让相机剧烈上仰')
                    assert len(context.pages) == 1
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('#back-to-map').click()
                expect(page.locator('#topic-grid a[data-topic]')).to_have_count(10)
                page.locator('#recent-toggle').click()
                expect(page.locator('#recent-panel [data-recent="perspective"]')).to_be_visible()
                page.locator('#recent-toggle').click()
                page.screenshot(path=str(output / f'learning-return-{width}.png'))
                assert not errors, errors
                assert not writes, writes
                results.append({'width': width, 'roundtrips': 2, 'tabs': len(context.pages),
                                'topic_route_and_recent_retained': True, 'page_errors': errors,
                                'business_write_requests': writes})
                context.close()
        finally:
            browser.close()
    (output / 'navigation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--learning-url', type=loopback_url, default='http://127.0.0.1:18767/learning')
    parser.add_argument('--reference-url', type=loopback_url, default='http://127.0.0.1:18766/')
    parser.add_argument('--output', type=Path, default=Path('.local/learning-preview/navigation'))
    args = parser.parse_args()
    verify(args.learning_url, args.reference_url, args.output)
