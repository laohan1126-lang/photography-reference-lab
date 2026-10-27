from fastapi.testclient import TestClient

from ref_lab.api import create_app
from ref_lab.config import Settings

TOKEN = 'test-only-access-token-not-a-live-credential-123'


def test_kana_static_resources_and_private_access(tmp_path):
    web = tmp_path / 'web'
    files = {
        'kana.css': b'body{}', 'kana-atmosphere.css': b'body{}', 'kana-painting.css': b'body{color:pink}', 'kana.js': b'void 0;',
        'ui-art/kana-wordmark.svg': b'<svg/>', 'ui-art/kana-frame.svg': b'<svg/>',
        'private/kana/summer.webp': b'synthetic summer',
        'private/kana/rain.webp': b'synthetic rain',
        'private/kana/portrait.webp': b'synthetic portrait',
    }
    for name, content in files.items():
        path = web / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (web / 'private' / 'kana' / 'other.webp').write_bytes(b'private')
    settings = Settings(tmp_path / 'data', TOKEN, public_origin='http://testserver', web_dir=web)
    with TestClient(create_app(settings)) as client:
        for name in ('kana.css', 'kana-atmosphere.css', 'kana-painting.css', 'kana.js', 'ui-art/kana-wordmark.svg', 'ui-art/kana-frame.svg'):
            response = client.get('/static/' + name)
            assert response.status_code == 200
            assert response.content == files[name]
        assert client.get('/static/private/kana/summer.webp').status_code == 401
        assert client.post('/api/session', json={'token': TOKEN}).status_code == 200
        for name in ('summer.webp', 'rain.webp', 'portrait.webp'):
            response = client.get('/static/private/kana/' + name)
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'private, no-store'
            assert response.content == files['private/kana/' + name]
        assert client.get('/static/private/kana/other.webp').status_code == 404
        assert client.get('/static/private/kana/%2e%2e/kana/other.webp').status_code == 404
        (web / 'private' / 'kana' / 'rain.webp').unlink()
        assert client.get('/static/private/kana/rain.webp').status_code == 404


def test_login_retries_private_art_on_actual_http(tmp_path):
    import os
    import shutil
    import socket
    import threading
    import time
    from pathlib import Path

    from PIL import Image
    from playwright.sync_api import expect, sync_playwright
    import uvicorn

    web = tmp_path / 'web'
    shutil.copytree(Path(__file__).resolve().parents[1] / 'web', web,
                    ignore=shutil.ignore_patterns('private'))
    art = web / 'private' / 'kana' / 'summer.webp'
    art.parent.mkdir(parents=True)
    for name in ('summer.webp', 'rain.webp', 'portrait.webp'):
        Image.new('RGB', (20, 20), 'red').save(art.parent / name, 'WEBP')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    settings = Settings(tmp_path / 'data', TOKEN, public_origin=f'http://127.0.0.1:{port}', web_dir=web)
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host='127.0.0.1', port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.1)
        assert server.started
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('LAB_CHROMIUM'), headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{port}/')
            page.locator('#login-token').fill(TOKEN)
            page.locator('#login-form button').click()
            expect(page.locator('#kana-theme-image')).to_have_attribute('data-asset-ready', 'true')
            assert page.locator('#application').is_visible()
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
