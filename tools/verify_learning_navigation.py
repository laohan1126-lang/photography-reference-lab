"""Read-only browser check of the two running local photography workspaces.

Only the learning prototype's tab-local state is edited. No reference-library
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
                page.goto(learning_url)
                page.locator('#gallery .image-open').first.wait_for()
                page.locator('[data-topic="光影"]').click()
                page.locator('#gallery .image-open').first.click()
                page.locator('#detail-save').click()
                page.locator('#study-note').fill('导航回归：返回后继续观察。')
                return_url, title = page.url, page.locator('#detail-title').inner_text()
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
                    expect(page.locator('#detail-title')).to_have_text(title)
                    expect(page.locator('#detail-save')).to_have_attribute('aria-pressed', 'true')
                    expect(page.locator('#study-note')).to_have_value('导航回归：返回后继续观察。')
                    assert len(context.pages) == 1
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('#back-to-wall').click()
                expect(page.locator('[data-topic="光影"]')).to_have_attribute('aria-pressed', 'true')
                page.screenshot(path=str(output / f'learning-return-{width}.png'))
                assert not errors, errors
                assert not writes, writes
                results.append({'width': width, 'roundtrips': 2, 'tabs': len(context.pages),
                                'route_notes_saved_retained': True, 'page_errors': errors,
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
