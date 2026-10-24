'''F5: a duplicate payload is temporary, and a known address is not fetched.

The collector used to keep every cover preview forever, so a confirmed
duplicate stayed on disk as a second copy of a picture the library already
owns. The payload now lives in the run's own staging area and is removed as
soon as its decision was made, while the evidence row keeps the SHA, the
address and the sizes. A cover address that the library already received is
not transferred at all.

Synthetic bytes and a synthetic history only.
'''
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

import pytest
from PIL import Image

from ref_lab.collection_history import ImageHistory
from tools import collect_verified as worker


def _png(size=(270, 360), color=(40, 80, 120)):
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, format='PNG')
    return buffer.getvalue()


def _pin(url='https://i.pinimg.com/236x/exact-observed.png'):
    return {'page': 'https://www.pinterest.com/pin/1234/', 'cover_url': url,
            'cover_width': 270, 'cover_height': 360, 'text': ''}


def _stream(monkeypatch, raw):
    requested = []

    def fetch(method, url, **kwargs):
        requested.append(url)

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def raise_for_status(self):
                return None

            def iter_bytes(self):
                yield raw

        return _Response()

    monkeypatch.setattr(worker.httpx, 'stream', fetch)
    return requested


def _history_with(tmp_path, raw):
    path = tmp_path / 'old.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return ImageHistory([path])


def test_a_matched_cover_keeps_the_evidence_but_not_the_payload(tmp_path, monkeypatch):
    raw = _png()
    history = _history_with(tmp_path / 'h', raw)
    try:
        requested = _stream(monkeypatch, raw)
        browser = worker.Browser(tmp_path / 'run')
        found = browser.check_duplicate(_pin(), history)
        assert found is not None
        assert found['duplicate_of'] == hashlib.sha256(raw).hexdigest()
        assert found['preview_sha256'] == hashlib.sha256(raw).hexdigest()
        assert found['preview_payload'] == 'temporary_removed'
        staged = tmp_path / 'run' / 'incoming' / 'previews'
        assert not (staged.is_dir() and list(staged.glob('*'))), 'the payload stayed on disk'
        assert requested == [_pin()['cover_url']], 'the cover was fetched once'
        assert browser.preview_payloads['removed'] == 1
        assert browser.preview_payloads['bytes'] == len(raw)
    finally:
        history.close(wait=True, timeout=5)


def test_an_unmatched_preview_is_removed_after_the_detail_used_it(tmp_path, monkeypatch):
    raw = _png()
    history = ImageHistory([])
    try:
        _stream(monkeypatch, raw)
        browser = worker.Browser(tmp_path / 'run')
        assert browser.check_duplicate(_pin(), history) is None, 'an unrelated cover is no duplicate'
        staged = tmp_path / 'run' / 'incoming' / 'previews'
        assert list(staged.glob('*')), 'the payload waits for the detail that reuses it'
        browser.command = lambda *args, **kwargs: '{}'
        monkeypatch.setattr(worker, 'fetch_pinterest_detail_metadata',
                            lambda *args, **kwargs: {'image_url': _pin()['cover_url']})

        def fail(*args, **kwargs):
            raise AssertionError('the same bytes were downloaded twice')

        monkeypatch.setattr(worker.httpx, 'stream', fail)
        step = {'source': 'pinterest', 'query': '西木野真姬'}
        rows = browser.receive({'page': 'https://www.pinterest.com/pin/1234/'}, step)
        assert rows and rows[0]['preview_bytes_reused'] is True
        assert not list(staged.glob('*')), 'the temporary payload outlived its use'
    finally:
        history.close(wait=True, timeout=5)


def test_a_known_cover_address_is_not_downloaded_at_all(tmp_path, monkeypatch):
    raw = _png()
    history = _history_with(tmp_path / 'known', raw)
    try:
        requested = _stream(monkeypatch, raw)
        browser = worker.Browser(tmp_path / 'run')
        key = worker.normalize_image_url(_pin()['cover_url'])
        browser.known_sources = {key: hashlib.sha256(raw).hexdigest()}
        found = browser.check_duplicate(_pin(), history)
        assert found is not None
        assert found['reason'] == 'known_source_url'
        assert found['source_address_precheck'] is True
        assert found['preview_payload'] == 'not_downloaded'
        assert requested == [], 'a known address was fetched again'
        incoming = tmp_path / 'run' / 'incoming'
        assert not incoming.exists() or not list(incoming.rglob('*')), 'a payload was written'
    finally:
        history.close(wait=True, timeout=5)


def test_the_staging_area_is_cleaned_with_the_rest_of_the_temporary_files(tmp_path):
    incoming = tmp_path / 'incoming'
    (incoming / 'previews').mkdir(parents=True)
    (incoming / 'previews' / ('a'*32+'.png')).write_bytes(b'preview-bytes')
    (incoming / 'b.part').write_bytes(b'download-bytes')
    result = worker.cleanup_incoming(tmp_path)
    assert result['files'] == 2
    assert result['bytes'] == len(b'preview-bytes') + len(b'download-bytes')
    assert not list(incoming.rglob('*'))


def test_the_public_gallery_does_not_keep_a_second_physical_copy(tmp_path):
    '''The published picture shares the file with the received original.

    One physical copy for both paths is the contract. An environment that
    cannot create a hard link at all cannot express it, so the check is
    skipped there and expected to run with normal permission.
    '''
    probe = tmp_path / 'link-probe.bin'
    probe.write_bytes(b'probe')
    link = tmp_path / 'link-probe-link.bin'
    try:
        os.link(probe, link)
    except OSError:
        pytest.skip('this environment cannot create hard links; the physical-copy '
                    'contract needs a normal-permission run')
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    images = tmp_path / 'run' / 'images'
    images.mkdir(parents=True)
    source = images / 'candidate.png'
    source.write_bytes(raw)
    rows = [{'asset_sha': sha, 'original_path': str(source),
             'page_url': 'https://example.invalid/note/1',
             'image_url': 'https://example.invalid/1.jpg', 'search_query': '测试'}]
    worker.render_search_gallery(tmp_path / 'run', rows)
    published = tmp_path / 'run' / 'public' / 'candidate.png'
    assert published.is_file()
    assert hashlib.sha256(published.read_bytes()).hexdigest() == sha
    assert os.path.samefile(source, published), \
        'the published picture is a second physical copy of the original'
    assert os.stat(source).st_ino == os.stat(published).st_ino
    assert os.stat(source).st_nlink >= 2


def test_the_public_gallery_publishes_the_same_bytes(tmp_path, monkeypatch):
    import re
    raw = _png()
    sha = hashlib.sha256(raw).hexdigest()
    images = tmp_path / 'run' / 'images'
    images.mkdir(parents=True)
    source = images / 'candidate.png'
    source.write_bytes(raw)
    def denied(*args,**kwargs):raise PermissionError('synthetic hardlink denial')
    monkeypatch.setattr(worker.os,'link',denied)
    rows = [{'asset_sha':sha,'original_path':str(source),'page_url':'https://example.invalid/note/1',
             'image_url':'https://example.invalid/1.jpg','search_query':'test'}]
    worker.render_search_gallery(tmp_path/'run',rows)
    public=tmp_path/'run/public'
    url=re.search(r'<img src="([^"]+)"',(public/'search-index.html').read_text('utf8'))[1]
    assert (public/url).resolve()==source.resolve()
    assert (public/url).read_bytes()==raw
    assert not list(public.glob('*.png'))


def test_gallery_rejects_changed_original_without_overwriting_public_bytes(tmp_path):
    source=tmp_path/'source.png';source.write_bytes(_png())
    target=tmp_path/'public.png';target.write_bytes(b'existing-content')
    with pytest.raises(ValueError,match='original SHA'):
        worker._publish_same_bytes(source,target,'0'*64)
    assert target.read_bytes()==b'existing-content'


def test_preview_released_on_next_card_and_on_history_error(tmp_path,monkeypatch):
    raw=_png();_stream(monkeypatch,raw)
    history=ImageHistory([]);browser=worker.Browser(tmp_path/'run')
    try:
        browser.check_duplicate(_pin(),history)
        first=Path(browser.preview['path']);assert first.exists()
        browser.check_duplicate({},history)
        assert not first.exists()
        def fail(*args):raise ValueError('synthetic matcher error')
        monkeypatch.setattr(history,'match',fail)
        assert browser.check_duplicate(_pin(),history) is None
        assert not list((tmp_path/'run/incoming/previews').glob('*'))
    finally:history.close()


def test_preview_cleanup_never_removes_an_unowned_path(tmp_path):
    source=tmp_path/'images/original.png';source.parent.mkdir();source.write_bytes(_png())
    browser=worker.Browser(tmp_path)
    browser.preview={'path':str(source),'sha':hashlib.sha256(source.read_bytes()).hexdigest()}
    browser._discard_preview()
    assert source.exists()
