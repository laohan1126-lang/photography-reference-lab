'''A4: the repeat evidence merge also works in the verified (one-pass) mode.

The verified mode intercepts the same repeated bytes early, so the new name
evidence of the repeat belongs to the photo it already holds. The merge only
folds discovery evidence into the received row: it grants no Review acceptance
and never touches the visual evidence. A platform warning keeps a photo out of
the accepted package, also when the photo was accepted before the warning
appeared on a repeat.

Synthetic pixels and a synthetic agent only.
'''
from __future__ import annotations

import json
import time

import pytest

from tools import collect_verified as worker
from tests.test_verified_collection import PROJECT, FakeAgent, FakeBrowser, job, row


@pytest.fixture(autouse=True)
def _no_production_data(monkeypatch):
    monkeypatch.delenv('LAB_DATA_DIR', raising=False)
    monkeypatch.delenv('LAB_COLLECTION_HISTORY_DIR', raising=False)


def test_the_verified_mode_merges_the_evidence_of_a_repeat(tmp_path):
    original = row(tmp_path, 'a.png', b'A')
    seen = {'count': 0}

    def receive(card, step):
        seen['count'] += 1
        if seen['count'] == 1:
            return [dict(original)]
        return [{**original, 'duplicate': True, 'reason': 'same_bytes_known',
                 'source_text': '测试角色甲 cos 摄影',
                 'author_detail': {'title': '测试角色甲 cos 摄影'}}]

    browser = FakeBrowser([])
    browser.receive = receive
    manifest, images = worker.collect(job(), FakeAgent(), browser, tmp_path)
    received = json.loads((tmp_path / 'received.json').read_text(encoding='utf8'))
    assert len(received) == 1, 'the repeat is not a second photo'
    trail = received[0].get('discovery_evidence_history')
    assert trail, 'the repeat evidence was not merged in the verified mode'
    assert received[0]['relevance']['tier'] == 'target_named'
    for candidate in manifest['candidates']:
        assert candidate['preflight']['identity_prediction'] == 'match', \
            'the merge must not overwrite the visual evidence'


def test_a_warned_photo_is_not_accepted_in_the_verified_package(tmp_path):
    import hashlib
    path = tmp_path / 'images' / 'warned.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'warned-original-bytes')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    received = [{'asset_sha': sha, 'original_path': str(path),
                 'page_url': 'https://example.org/post',
                 'image_url': 'https://example.org/image.png',
                 'relevance': {'tier': 'target_named', 'source_warnings': ['含 AI 生成内容']}}]
    review = {'asset_sha': sha, 'context_sha': worker.scope_sha(PROJECT), 'kind': 'cosplay_photo',
              'identity': 'match', 'costume': 'not_required', 'confidence': 'medium',
              'photography_usable': 'yes', 'kind_evidence': ['合成证据'],
              'identity_evidence': ['合成证据'], 'costume_evidence': [],
              'photography_evidence': ['合成证据'], 'reason': '合成评审回执'}
    items = {sha: {'asset_sha': sha, 'status': 'accepted', 'accepted': True,
                   'decision': 'CONFIRMED', 'review': review, 'references': [],
                   'attempts': 1, 'completed_at': time.time()}}
    state = {'batch_id': 'synthetic-batch', 'queries': [], 'checks': {}}
    manifest, images, summary = worker._review_package(
        job(), PROJECT, tmp_path, state, received, items, {},
        status='completed', stop_reason='synthetic', started=time.monotonic(), agent=FakeAgent())
    assert not manifest['candidates'], 'a warned photo is not a qualified photo'
    assert not images
    assert summary['counts']['accepted'] == 0
    assert summary['counts']['blocked'] == 1


def test_late_warning_excludes_legacy_output_without_changing_visual_receipt(tmp_path):
    original=row(tmp_path,'legacy.png',b'original-A');browser=FakeBrowser([])
    calls=[]
    def receive(card,step):
        calls.append(step['source'])
        if len(calls)==1:return [dict(original)]
        return [{**original,'duplicate':True,'reason':'same_bytes_known','source_text':'含 AI 生成内容'}]
    browser.receive=receive
    manifest,images=worker.collect(job(),FakeAgent(),browser,tmp_path)
    audit=json.loads((tmp_path/'visual-audit.json').read_text('utf8'))
    assert audit[0]['accepted'] and audit[0]['review']['identity']=='match'
    assert len(calls)>=2
    assert not manifest['candidates'] and not images
    assert (tmp_path/'images/legacy.png').read_bytes()==b'original-A'


@pytest.mark.parametrize('failure',[ValueError('corrupt keeper'),worker.HistoryIntegrityBlocked('missing bytes')])
def test_history_entry_has_a_named_integrity_failure(tmp_path,monkeypatch,failure):
    def broken(*args,**kwargs):raise failure
    monkeypatch.setattr(worker,'collect_history_scope',broken)
    with pytest.raises(worker.HistoryIntegrityBlocked) as error:
        worker._validated_history_scope(tmp_path,tmp_path/'current','proj-a')
    assert error.value.category=='history_integrity_blocked'


def test_goal_creation_returns_named_conflict_before_starting_collection(library,monkeypatch):
    from ref_lab import collection_history
    from ref_lab.service import Problem
    from ref_lab.models import ProjectInput,JobInput
    def broken(*args,**kwargs):raise collection_history.HistoryIntegrityBlocked('synthetic missing keeper')
    monkeypatch.setattr(collection_history,'collect_history_scope',broken)
    project=library.create_project(ProjectInput(character='synthetic'))
    with pytest.raises(Problem) as error:
        library.create_job(project['id'],JobInput(kind='collection',collection_mode='search'))
    assert error.value.status==409 and error.value.details['code']=='history_integrity_blocked'
    assert library.jobs(project['id'])==[]
