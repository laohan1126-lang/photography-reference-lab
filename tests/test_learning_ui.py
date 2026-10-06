"""Learning prototype: real HTTP/Chromium, isolated synthetic media, no owner DB."""
from __future__ import annotations

import json
import re
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
    expect(page.locator('#map-view')).to_be_visible()
    expect(page.locator("#topic-grid a[data-topic]")).to_have_count(10)


def hash_params(page):
    return page.evaluate("() => Object.fromEntries(new URLSearchParams(location.hash.slice(1)))")


def test_map_has_ten_topics_search_filters_and_empty_state(prototype_site,browser_page):
    url,_,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    expect(page.locator("#topic-grid a[data-topic='perspective']")).to_contain_text('机位、焦段与透视')

    search=page.locator('#search')
    search.fill('透视')
    expect(page.locator('#map-view')).to_be_visible()
    expect(page.locator("#topic-grid a[data-topic]")).to_have_count(1)
    expect(page.locator("#topic-grid a[data-topic='perspective']")).to_be_visible()
    assert hash_params(page).get('q') == '透视'

    search.fill('没有这个专题')
    expect(page.locator("#topic-grid a[data-topic]")).to_have_count(0)
    expect(page.locator('#empty-state')).to_contain_text('没有找到')


def test_empty_media_still_allows_topic_learning(prototype,prototype_site,browser_page):
    _,_,samples=prototype
    (samples/'manifest.json').unlink()
    url,_,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    page.locator("#topic-grid a[data-topic='perspective']").click()
    expect(page.locator('#topic-view')).to_be_visible()
    expect(page.locator('#topic-title')).to_contain_text('机位、焦段与透视')


def test_perspective_research_note_and_shared_topic_template(prototype_site,browser_page):
    url,_,_=prototype_site
    page,_=browser_page
    media_requests=[]
    page.on('request',lambda r:media_requests.append(r.method) if '/api/learning-preview' in r.url else None)
    open_prototype(page,url)
    page.locator("#topic-grid a[data-topic='perspective']").click()
    expect(page.locator('#topic-view')).to_be_visible()
    expect(page.locator('#topic-title')).to_contain_text('机位、焦段与透视')
    note=page.locator('#research-note')
    expect(note.locator("[data-section='question']")).to_contain_text('为什么低机位并不天然产生威严感')
    rules=note.locator("[data-section='rules']")
    for rule in (
        '相机高度与镜头俯仰是两个变量',
        '广角近距离会强化前后距离差',
        '仰拍是否产生气势，与人物姿态、画面垂直线、焦段和主体占比共同相关',
        '低机位不等于必须让相机剧烈上仰',
    ):
        expect(rules).to_contain_text(rule)
    for section in ('problems','conclusion','next'):
        expect(note.locator(f"[data-section='{section}']")).not_to_be_empty()

    gallery=page.locator('#case-gallery')
    case_count=gallery.locator('.case-open').count()
    assert 1 <= case_count <= 9, case_count
    gallery.locator('img').evaluate_all('imgs => Promise.all(imgs.map(i => {i.loading="eager"; return i.decode();}))')
    ratios=gallery.locator('img').evaluate_all('imgs => imgs.map(i => i.naturalWidth / i.naturalHeight)')
    assert len({round(ratio,2) for ratio in ratios if ratio}) > 1, ratios
    assert gallery.locator('img').evaluate_all('imgs => imgs.every(i => Math.abs(i.getBoundingClientRect().width / i.getBoundingClientRect().height - i.naturalWidth / i.naturalHeight) < .02)')

    for topic in ('composition','pose','props','light','scale','expression','direction','post','motion'):
        page.locator('#back-to-map').click()
        page.locator(f"#topic-grid a[data-topic='{topic}']").click()
        expect(page.locator('#topic-view')).to_be_visible()
        expect(page.locator('#research-note')).to_contain_text('示例')
        assert hash_params(page).get('topic') == topic
    assert 'GET' in media_requests, media_requests
    assert not [method for method in media_requests if method not in {'GET','HEAD'}], media_requests


def test_case_viewer_keyboard_navigation_focus_return_and_route_history(prototype_site,browser_page):
    url,_,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    page.locator("#topic-grid a[data-topic='perspective']").click()
    opener=page.locator("#case-gallery .case-open[data-case='0']")
    page.mouse.move(0,0)
    expect(opener.locator('.case-overlay')).to_have_css('opacity','0')
    opener.hover()
    expect(opener.locator('.case-overlay')).to_have_css('opacity','1')
    page.mouse.move(0,0)
    opener.focus()
    # :focus-visible follows keyboard modality, not a programmatic focus after a click.
    page.keyboard.press('Tab')
    page.keyboard.press('Shift+Tab')
    expect(opener).to_be_focused()
    expect(opener.locator('.case-overlay')).to_have_css('opacity','1')
    expect(opener.locator('.case-overlay')).to_contain_text('示例')
    opener.click()
    dialog=page.locator('#case-viewer')
    expect(dialog).to_be_visible()
    expect(page.locator('#viewer-image')).to_be_visible()
    first_src=page.locator('#viewer-image').get_attribute('src')
    expect(page.locator('#viewer-title')).not_to_be_empty()
    expect(page.locator('#viewer-note')).not_to_be_empty()
    expect(page.locator('#viewer-source')).not_to_be_empty()
    page.locator('#viewer-next').click()
    assert page.locator('#viewer-image').get_attribute('src') != first_src
    page.locator('#viewer-prev').click()
    assert page.locator('#viewer-image').get_attribute('src') == first_src
    page.keyboard.press('Escape')
    expect(dialog).not_to_be_visible()
    assert opener.evaluate('(e) => document.activeElement === e')
    assert hash_params(page).get('topic') == 'perspective'
    assert 'case' not in hash_params(page)

    page.locator("#case-gallery .case-open[data-case='0']").click()
    assert hash_params(page).get('case') == '0'
    page.go_back()
    expect(page.locator('#topic-view')).to_be_visible()
    page.go_back()
    expect(page.locator('#map-view')).to_be_visible()
    expect(page.locator("#topic-grid a[data-topic='perspective']")).to_be_focused()


def test_recent_learning_refresh_and_deep_link_priority(prototype_site,browser_page):
    url,_,_=prototype_site
    page,_=browser_page
    open_prototype(page,url)
    expect(page.locator('#recent-panel [data-recent]')).to_have_count(0)
    page.locator('#recent-toggle').click()
    expect(page.locator('#recent-panel')).to_contain_text('还没有最近学习')
    page.locator('#recent-toggle').click()
    page.locator("#topic-grid a[data-topic='perspective']").click()
    assert hash_params(page).get('topic') == 'perspective'
    page.reload()
    expect(page.locator('#topic-view')).to_be_visible()
    expect(page.locator('#topic-title')).to_contain_text('机位、焦段与透视')
    page.locator('#back-to-map').click()
    page.locator('#recent-toggle').click()
    recent=page.locator("#recent-panel [data-recent='perspective']")
    expect(recent).to_be_visible()
    recent.click()
    expect(page.locator('#topic-view')).to_be_visible()
    page.goto(url+'/learning#topic=composition')
    expect(page.locator('#topic-title')).to_contain_text('构图与画面组织')
    page.goto(url+'/learning#q=透视')
    expect(page.locator('#map-view')).to_be_visible()
    expect(page.locator('#search')).to_have_value('透视')
    expect(page.locator("#topic-grid a[data-topic='perspective']")).to_be_visible()


@pytest.mark.parametrize('width', [1440, 390])
def test_workspace_switch_roundtrip_keeps_learning_place(prototype_site, browser_page, width):
    url, _, _ = prototype_site
    page, _ = browser_page
    page.set_viewport_size({'width': width, 'height': 900})
    open_prototype(page, url)
    page.locator("#topic-grid a[data-topic='perspective']").click()
    expect(page.locator('#topic-view')).to_be_visible()
    page.locator('#reference-link').click()
    expect(page.locator('#application')).to_be_visible()
    learning_link = page.get_by_role('link', name='摄影学习', exact=False)
    expect(learning_link).to_be_visible()
    assert learning_link.get_attribute('target') in (None, '')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.reload()
    page.get_by_role('link', name='摄影学习', exact=False).click()
    expect(page).to_have_url(re.compile(r'/learning(?:#.*)?$'))
    expect(page.locator('#topic-view')).to_be_visible()
    expect(page.locator('#topic-title')).to_contain_text('机位、焦段与透视')
    assert hash_params(page).get('topic') == 'perspective'
    assert len(page.context.pages) == 1
    writes=[]
    page.on('request',lambda r:writes.append(f'{r.method} {r.url}') if r.method not in {'GET','HEAD'} else None)
    page.locator('#back-to-map').click()
    expect(page.locator('#map-view')).to_be_visible()
    assert writes == [], writes
    assert len(page.context.pages) == 1
