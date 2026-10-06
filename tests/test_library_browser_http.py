"""Real HTTP/cookie gallery journey, not the component TestClient bridge."""
from playwright.sync_api import expect
from test_browser import live_site, browser_page, unlock


def test_library_gallery_http_static_scripts_cookie_reload(live_site, browser_page):
    url, library, project = live_site
    page, _ = browser_page
    unlock(page, url)
    page.get_by_role('button', name='图库 · 跨项目找图', exact=True).click()
    expect(page.locator('.library-tile')).to_have_count(3)
    page.locator('.library-preview').first.click()
    page.locator('#editor select[name=viewpoint]').select_option('low_angle')
    page.get_by_role('button', name='保存摄影分类', exact=True).click()
    expect(page.locator('#editor')).not_to_be_visible()
    page.locator('#library-filter-form [name=viewpoint]').select_option('low_angle')
    page.get_by_role('button', name='查找', exact=True).click()
    expect(page.locator('.library-tile')).to_have_count(1)
    page.locator('#library-save-search').click()
    page.get_by_label('搜索名称', exact=True).fill('HTTP 仰拍')
    page.get_by_role('button', name='保存搜索', exact=True).click()
    expect(page.locator('#editor')).not_to_be_visible()
    page.reload()
    expect(page.locator('.library-tile')).to_have_count(1)
    expect(page.locator('#library-saved-search option')).to_have_count(2)
    assert all(r['decision'] == 'pending' for r in library.references(project['id'])['items'])
    page.locator('.library-preview').first.click()
    page.locator('[data-library-use]').first.click()
    expect(page.locator('#main-image')).to_be_visible()
