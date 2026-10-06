"""Learning prototype: real HTTP/Chromium, isolated synthetic media, no owner DB."""
from __future__ import annotations

import json
import shutil
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient
from playwright.sync_api import expect

from conftest import TOKEN, image_bytes
from ref_lab.api import create_app
from ref_lab.config import Settings
from test_browser import browser_page

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prototype(tmp_path):
    web = tmp_path / 'web'
    web.mkdir()
    for name in ('index.html', 'app.js', 'styles.css', 'learning.html', 'learning.js', 'learning.css', 'learning-icons.json'):
        shutil.copyfile(ROOT / 'web' / name, web / name)
    samples = tmp_path / '.local/learning-preview'
    samples.mkdir(parents=True)
    items = []
    for i in range(1, 13):
        data = image_bytes(i, size=(600,900) if i % 2 else (900,600))
        (samples / f'P{i}.png').write_bytes(data)
        items.append({'id':f'P{i}', 'src':f'/api/learning-preview/P{i}.png',
                      'width':600 if i%2 else 900, 'height':900 if i%2 else 600,
                      'title':f'合成参考 {i}', 'originalTitle':f'合成测试画面 {i}',
                      'topic':'光影' if i%2 else '构图', 'author':'测试署名',
                      'sourceUrl':'https://example.org/reference', 'restrictions':'合成像素，不是视觉准确性证据。'})
    (samples / 'manifest.json').write_text(json.dumps({'items':items},ensure_ascii=False),encoding='utf-8')
    settings = Settings(tmp_path / 'data', TOKEN, web_dir=web, public_origin='http://127.0.0.1:18765')
    app = create_app(settings)
    return app, items, samples


def test_private_samples_static_allowlist_and_read_only(prototype):
    app, items, samples = prototype
    with TestClient(app,base_url='http://127.0.0.1:18765') as client:
        assert client.get('/learning').status_code == 200
        assert client.get('/static/learning.js').status_code == 200
        assert client.get('/static/manifest.json').status_code == 404
        assert client.get('/api/learning-preview').status_code == 401
        assert client.get('/api/learning-preview/P1.png').status_code == 401
        assert client.post('/api/session',json={'token':TOKEN}).status_code == 200
        before = client.get('/api/projects').json()
        assert client.get('/api/learning-preview').json()['items'] == items
        response = client.get('/api/learning-preview/P1.png')
        assert response.content == (samples / 'P1.png').read_bytes()
        assert response.headers['cache-control'] == 'private, no-store'
        for path in ('/api/learning-preview/manifest.json', '/api/learning-preview/P1.txt', '/api/learning-preview/%2e%2e%2faccess-token'):
            assert client.get(path).status_code == 404
        assert client.get('/api/projects').json() == before
        (samples / 'manifest.json').unlink()
        assert client.get('/api/learning-preview').json() == {'items':[]}


@pytest.fixture
def prototype_site(prototype):
    app, items, _ = prototype
    sock=socket.socket()
    sock.bind(('127.0.0.1',0))
    port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
    thread.start()
    for _ in range(150):
        if server.started: break
        time.sleep(.02)
    assert server.started
    try:
        yield f'http://127.0.0.1:{port}',app,items
    finally:
        server.should_exit=True
        thread.join(timeout=8)
        sock.close()


def open_prototype(page,url):
    assert page.request.post(url+'/api/session',data={'token':TOKEN}).status == 200
    page.goto(url+'/learning')
    expect(page.locator('#gallery .photo-card')).to_have_count(12)


def test_save_notes_practice_refresh_and_source(prototype_site,browser_page):
    url,app,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    writes=[]
    page.on('request',lambda r:writes.append(r.url) if r.method not in {'GET','HEAD'} else None)
    page.locator('#gallery [data-open="P1"]').first.click()
    page.locator('#detail-save').click()
    page.locator('#study-note').fill('留意边缘的明暗。<img src=x onerror=alert(1)>')
    page.locator('[data-detail-tab="source"]').click()
    expect(page.locator('#detail-panel')).to_contain_text('合成像素')
    page.locator('[data-detail-tab="notes"]').click()
    expect(page.locator('#study-note')).to_have_value('留意边缘的明暗。<img src=x onerror=alert(1)>')
    page.locator('#add-practice').click()
    page.reload()
    expect(page.locator('#detail-save')).to_have_attribute('aria-pressed','true')
    expect(page.locator('#study-note')).to_have_value('留意边缘的明暗。<img src=x onerror=alert(1)>')
    page.locator('#enlarge-photo').click()
    expect(page.locator('#viewer')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#viewer')).not_to_be_visible()
    page.locator('#back-to-wall').click()
    page.locator('.view-tabs [data-view="practice"]').click()
    expect(page.locator('#gallery .photo-card')).to_have_count(1)
    page.locator('[data-complete="P1"]').check()
    expect(page.locator('#gallery')).to_contain_text('这次练过了')
    page.reload()
    expect(page.locator('[data-complete="P1"]')).to_be_checked()
    assert not writes, writes
    assert page.request.get(url+'/api/projects').json() == []
    assert page.request.get(url+'/api/inspirations').json()['total'] == 0


def test_filters_clear_keep_scope_skip_link_and_browser_back(prototype_site,browser_page):
    url,_,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    page.locator('#gallery [data-save="P1"]').click()
    page.locator('.view-tabs [data-view="saved"]').click()
    page.locator('#search').fill('nothing-matches')
    expect(page.locator('#empty-action')).to_have_text('清除筛选')
    page.locator('#empty-action').click()
    expect(page.locator('.view-tabs [data-view="saved"]')).to_have_class('active')
    expect(page.locator('#gallery .photo-card')).to_have_count(1)
    for detail in (False,True):
        if detail: page.locator('#gallery [data-open="P1"]').first.click()
        before=page.url
        page.locator('.skip-link').focus()
        page.keyboard.press('Enter')
        assert page.url == before
        assert page.evaluate('document.activeElement.id') == 'main'
    page.locator('#back-to-wall').click()
    page.locator('.view-tabs [data-view="discover"]').click()
    page.locator('[data-topic="光影"]').click()
    expect(page.locator('#gallery .photo-card')).to_have_count(6)
    page.locator('#gallery [data-open="P1"]').first.click()
    page.keyboard.press('ArrowRight')
    expect(page.locator('#detail-title')).to_have_text('合成参考 3')
    page.go_back()
    expect(page.locator('#detail-title')).to_have_text('合成参考 1')
    page.go_back()
    expect(page.locator('#browse-view')).to_be_visible()
    expect(page.locator('#gallery .photo-card')).to_have_count(6)


def test_mobile_topics_empty_saved_and_layout(prototype_site,browser_page):
    url,_,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.locator('#gallery').evaluate('e=>getComputedStyle(e).columnCount') == '2'
    page.locator('.rail [data-view="saved"]').click()
    expect(page.locator('#empty-title')).to_have_text('喜欢的画面，先留在这里')
    page.locator('#empty-action').click()
    page.locator('.rail [data-view="topics"]').click()
    expect(page.locator('.topic-tile')).to_have_count(5)
    page.locator('.topic-tile[data-topic="构图"]').click()
    expect(page.locator('#gallery .photo-card')).to_have_count(6)
    page.locator('#gallery .image-open').first.click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#study-note').fill('手机端观察')
    page.locator('#add-practice').click()
    page.locator('.rail [data-view="practice"]').click()
    page.locator('#search').fill('nothing-matches')
    expect(page.locator('#empty-action')).to_have_text('清除筛选')
    page.locator('#empty-action').click()
    expect(page.locator('.view-tabs [data-view="practice"]')).to_have_class('active')
    expect(page.locator('#gallery .photo-card')).to_have_count(1)
    page.locator('#prototype-info').click()
    expect(page.locator('#info-dialog')).to_be_visible()
    page.locator('#info-done').click()
    expect(page.locator('#info-dialog')).not_to_be_visible()
