'''F2: a repeat sighting must still lend its new name evidence to the photo.

The collector stops the download as soon as it knows the bytes are already
known. That is correct for the bytes, but the new source can carry the name
that the first sighting did not have. The evidence has to be merged into the
photo this Job already holds, without downloading it again and without
counting it twice.

Synthetic pixels and a synthetic browser: these regressions protect the
collection rules, not a platform or a model.
'''
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote

import pytest

from ref_lab import collection_history as history_module
from tools import collect_verified as worker
from tests.photo_type_fixture import synthetic_type
from tests.test_browserskill_recovery import SyntheticAgent, _job
from tests.test_collage_split import _collage, _textured

TARGET = '西木野真姬'


@pytest.fixture(autouse=True)
def _no_production_data(monkeypatch):
    """A synthetic fixture must never read the exported production library."""
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)


def _raw(image=None):
    buffer = io.BytesIO()
    (image if image is not None else _textured((800, 600), 41, (70, 90, 120))).save(buffer, format='PNG')
    return buffer.getvalue()


class _Browser:
    '''One photo, seen from two sources; each source has its own card text.'''

    supports_sort = True
    session = 'synthetic-f2'
    return_failed = False
    return_error = None
    preview_reused = 0
    download_errors = []
    known_shas = known_sources = incoming_dir = None

    def __init__(self, folder, raw, sha, named_sources, detail_titles=None):
        self.folder = folder
        self.raw = raw
        self.sha = sha
        self.named_sources = set(named_sources)
        self.detail_titles = dict(detail_titles or {})

    def start(self):
        pass

    def close(self):
        pass

    def search(self, step, sort='relevance'):
        source = step['source']
        named = source in self.named_sources
        page = ('https://www.pinterest.com/pin/1234/' if source == 'pinterest'
                else 'https://www.xiaohongshu.com/explore/' + 'a' * 24)
        url = ('https://www.pinterest.com/search/pins/?q=' if source == 'pinterest'
               else 'https://www.xiaohongshu.com/search_result?keyword=') + quote(step['query'])
        return {'url': url, 'search': step['query'],
                'visibleMain': TARGET,
                'cards': [{'page': page, 'text': (TARGET + ' cos 摄影') if named else '周末记录'}],
                'login_required': False, 'challenge': False}

    def more(self, step):
        return self.search(step)

    def receive(self, card, step):
        row = {'asset_sha': self.sha, 'page_url': card['page'],
               'image_url': 'https://sns-img.xhscdn.com/sample.png',
               'source_text': card['text'], 'width': 800, 'height': 600,
               'author_detail': {'title': self.detail_titles.get(step['source'], card['text'])}}
        if self.sha in (self.known_shas or ()):
            # The bytes are known: no download, only a sighting.
            return [{**row, 'duplicate': True, 'reason': 'same_bytes_known'}]
        path = self.folder / 'incoming' / 'image.part'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.raw)
        row.update(original_path=str(path), ext='png', temporary=True)
        synthetic_type(self.folder, row)
        return [row]


def _run(folder, *, named_sources, sources=('xiaohongshu', 'pinterest'), history=None, image=None,
         target=1, detail_titles=None):
    raw = _raw(image)
    sha = hashlib.sha256(raw).hexdigest()
    browser = _Browser(folder, raw, sha, named_sources, detail_titles)
    job = {**_job(target=target), 'preferred_sources': list(sources)}
    history = history if history is not None else history_module.ImageHistory([])
    summary, _ = worker.collect(job, SyntheticAgent(), browser, folder,
                                 history=history, search_only=True)
    history.close(wait=True, timeout=5)
    return summary, sha


def _received(folder):
    path = folder / 'received.json'
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else []


def _duplicates(folder):
    path = folder / 'duplicates.json'
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else []


def test_a_repeat_that_names_the_photo_still_names_it(tmp_path):
    '''The first sighting had no name; the repeat carries it.'''
    summary, sha = _run(tmp_path, named_sources={'pinterest'})
    assert summary['counts']['found'] == 1, 'the repeat is not a second photo'
    assert summary['counts']['usable_named'] == 1, 'the new name evidence was lost'
    assert summary['counts']['target_confirmed'] == 1
    assert summary['stop_reason'] == 'target_reached'
    rows = _received(tmp_path)
    assert len(rows) == 1 and rows[0]['asset_sha'] == sha
    assert rows[0]['relevance']['tier'] == 'target_named'
    assert rows[0].get('discovery_evidence_history'), 'the old evidence is kept'
    assert _duplicates(tmp_path), 'the repeat was really seen'


def test_the_name_survives_a_repeat_from_another_source_first(tmp_path):
    '''The other order: the photo was named first and the repeat adds nothing.

    The target is two, so the collector cannot stop at the first sighting and
    really meets the repeat; a later unnamed source must not erase the name.
    '''
    summary, sha = _run(tmp_path, named_sources={'xiaohongshu'}, target=2)
    assert summary['counts']['found'] == 1
    assert summary['counts']['usable_named'] == 1
    rows = _received(tmp_path)
    assert len(rows) == 1 and rows[0]['asset_sha'] == sha
    assert rows[0]['relevance']['tier'] == 'target_named'
    assert _duplicates(tmp_path), 'the repeat was really seen'
    assert len(rows[0].get('discovery_evidence_history', [])) >= 2, 'the repeat left its evidence'


def test_a_historical_photo_is_never_made_new_by_a_repeat(tmp_path):
    '''A photo the library already owns stays history, whatever the source says.'''
    raw = _raw()
    sha = hashlib.sha256(raw).hexdigest()
    kept = tmp_path / 'history.png'
    kept.write_bytes(raw)
    history = history_module.ImageHistory([kept])
    try:
        summary, _ = _run(tmp_path, named_sources={'xiaohongshu', 'pinterest'}, history=history)
    finally:
        history.close(wait=True, timeout=5)
    assert summary['counts']['found'] == 0, 'a historical photo is not a new one'
    assert _received(tmp_path) == []


def test_the_duplicate_receipt_is_still_written(tmp_path):
    '''Blocking the download must not lose the record of the sighting.'''
    _run(tmp_path, named_sources={'pinterest'})
    duplicates = json.loads((tmp_path / 'duplicates.json').read_text(encoding='utf8'))
    assert duplicates, 'the repeated sighting is recorded'
    assert all(entry.get('page_url') for entry in duplicates)


def test_a_warning_on_the_repeat_blocks_the_photo(tmp_path):
    '''A source warning on the repeat keeps the photo out of the qualified set.'''
    raw = _raw()
    sha = hashlib.sha256(raw).hexdigest()

    class _WarningBrowser(_Browser):
        def receive(self, card, step):
            rows = super().receive(card, step)
            if rows[0].get('duplicate'):
                rows[0]['source_text'] = '含 AI 生成内容'
            return rows

    browser = _WarningBrowser(tmp_path, raw, sha, {'pinterest'})
    history = history_module.ImageHistory([])
    job = {**_job(target=1), 'preferred_sources': ['xiaohongshu', 'pinterest']}
    summary, _ = worker.collect(job, SyntheticAgent(), browser, tmp_path,
                                history=history, search_only=True)
    history.close(wait=True, timeout=5)
    assert summary['counts']['found'] == 1
    rows = _received(tmp_path)
    assert rows, 'the photo is still received'
    from ref_lab.search_relevance import source_warnings
    assert source_warnings(rows[0]), 'the warning from the repeat is kept'
    assert summary['counts']['usable_named'] == 0, 'a warned photo is not a qualified photo'
    assert summary['counts']['source_pending'] == 1, 'the photo waits for a human'
    assert Path(rows[0]['original_path']).is_file(), 'the received bytes are untouched'


def test_a_warning_on_the_repeat_blocks_its_tiles(tmp_path):
    '''A warned collage is blocked as a whole, tiles included.'''
    from ref_lab.collage import DerivedStore, VALID

    raw = _raw(_collage(2, 1, tile=(800, 600)))
    sha = hashlib.sha256(raw).hexdigest()

    class _WarningBrowser(_Browser):
        def receive(self, card, step):
            rows = super().receive(card, step)
            if rows[0].get('duplicate'):
                rows[0]['source_text'] = '含 AI 生成内容'
            return rows

    browser = _WarningBrowser(tmp_path, raw, sha, {'pinterest'})
    history = history_module.ImageHistory([])
    job = {**_job(target=1), 'preferred_sources': ['xiaohongshu', 'pinterest']}
    summary, _ = worker.collect(job, SyntheticAgent(), browser, tmp_path,
                                history=history, search_only=True)
    history.close(wait=True, timeout=5)
    records = DerivedStore(tmp_path).items()
    children = [child for record in records.values() for child in record.get('children', [])
                if child.get('status') == VALID]
    assert children, 'the collage was split into tiles'
    assert summary['counts']['usable_named'] == 0, 'warned tiles are not qualified tiles'
    assert summary['counts']['source_pending'] == len(children), 'every tile waits for a human'
    for child in children:
        assert Path(child['path']).is_file(), 'the tile bytes are untouched'


def test_the_new_name_reaches_the_derived_tiles(tmp_path):
    '''A collage parent and its tiles are one photo: the name applies to both.'''
    from ref_lab.collage import DerivedStore, VALID
    from ref_lab.collection_counts import compute

    summary, _ = _run(tmp_path, named_sources={'pinterest'}, image=_collage(2, 1, tile=(800, 600)))
    assert summary['counts']['found'] == 1
    rows = _received(tmp_path)
    assert rows and rows[0]['relevance']['tier'] == 'target_named'

    records = DerivedStore(tmp_path).items()
    children = [child for record in records.values() for child in record.get('children', [])
                if child.get('status') == VALID]
    assert children, 'the collage was split into tiles'
    for child in children:
        synthetic_type(tmp_path, {'asset_sha': child['child_sha'], 'original_path': child['path']})

    counts = compute(tmp_path, rows, records)
    assert counts['usable_named'] == len(children), 'the tiles carry the new name'


def test_a_conflicting_character_source_keeps_the_name_evidence(tmp_path):
    '''A repeat that points at another character does not erase the name.

    The name-text association and the contradicting sighting both stay in the
    trail; the positive association decides the count in both source orders,
    and neither of them claims a strict visual identity.
    '''
    summary, sha = _run(tmp_path, named_sources={'xiaohongshu', 'pinterest'},
                        detail_titles={'pinterest': '另一个角色的 cos 摄影'}, target=2)
    assert summary['counts']['found'] == 1
    rows = _received(tmp_path)
    assert rows and rows[0]['asset_sha'] == sha
    assert rows[0]['relevance']['tier'] == 'target_named'
    trail = rows[0].get('discovery_evidence_history', [])
    assert len(trail) >= 2, 'the contradicting sighting stays in the trail'
    assert any(entry.get('tier') == 'other_character' for entry in trail), \
        'the conflicting character tier is kept, not dropped'
    assert summary['counts']['usable_named'] == 1


def test_the_name_evidence_wins_in_the_other_source_order(tmp_path):
    '''The contradicting source comes first: the name still decides the count.'''
    summary, sha = _run(tmp_path, named_sources={'xiaohongshu', 'pinterest'},
                        sources=('pinterest', 'xiaohongshu'),
                        detail_titles={'pinterest': '另一个角色的 cos 摄影'})
    assert summary['counts']['found'] == 1
    rows = _received(tmp_path)
    assert rows and rows[0]['relevance']['tier'] == 'target_named'
    trail = rows[0].get('discovery_evidence_history', [])
    assert any(entry.get('tier') == 'other_character' for entry in trail)
    assert summary['counts']['usable_named'] == 1


@pytest.mark.parametrize('text,tier,qualified',[
    ('其他角色的 cos 摄影','other_character',1),
    ('含 AI 生成内容','non_photo',0)])
def test_reliable_cover_keeps_negative_discovery_trail(tmp_path,monkeypatch,text,tier,qualified):
    raw=_raw();sha=hashlib.sha256(raw).hexdigest();cover='https://i.pinimg.com/known.png'
    monkeypatch.setattr(worker,'_known_image_sources',lambda *a:{worker.normalize_image_url(cover):sha})
    class Covers(_Browser):
        def search(self,step,sort='relevance'):
            snapshot=super().search(step,sort)
            if step['source']=='pinterest':snapshot['cards'][0].update(text=text,cover_url=cover)
            return snapshot
        def check_duplicate(self,card,history):
            if card.get('cover_url')==cover and sha in history.records:
                return {'duplicate_of':sha,'reason':'known_source_url'}
    history=history_module.ImageHistory([])
    try:
        summary,_=worker.collect(_job(target=2),SyntheticAgent(),Covers(tmp_path,raw,sha,{'xiaohongshu'}),
                                  tmp_path,history=history,search_only=True)
    finally:history.close()
    row=_received(tmp_path)[0]
    assert any(item.get('tier')==tier for item in row['discovery_evidence_history'])
    assert summary['counts']['usable_named']==qualified
    assert summary['counts']['source_pending']==1-qualified
    assert Path(row['original_path']).read_bytes()==raw
