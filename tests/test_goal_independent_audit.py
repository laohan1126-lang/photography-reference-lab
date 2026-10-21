"""Regression boundaries missed by the photo15 acceptance; no live model calls."""
import hashlib
import io
import json
import threading
from pathlib import Path

import pytest
from PIL import Image

from ref_lab import classification, agent_collection, collage
from ref_lab.collection_counts import compute
from tests.test_search_continue_recovery import Agent, Browser, _job
from tests.test_collage_split import _textured, _write_original
from tools import collect_verified as collector


def test_goal_type_worker_uses_the_selected_model(tmp_path, monkeypatch):
    from ref_lab import photo_types
    selected = []
    class TypeWorker:
        blocked = False
        def __init__(self, *args, **kwargs): selected.append(kwargs.get('model'))
        def enqueue(self, record): pass
        def close(self, **kwargs): pass
    class EmptyBrowser:
        def start(self): pass
        def close(self): pass
        def search(self, step): return {'cards': []}
    monkeypatch.setattr(photo_types, 'PhotoTypeWorker', TypeWorker)
    (tmp_path/'goal.json').write_text(json.dumps({'started_at': 0, 'baseline_shas': []}), 'utf8')
    collector.collect(_job(extra=0, target=1), Agent(), EmptyBrowser(), tmp_path, search_only=True)
    assert selected == [Agent.model]


def test_plain_search_reaches_candidate_target_without_type_receipts(tmp_path, monkeypatch):
    monkeypatch.setattr('tests.photo_type_fixture.synthetic_type', lambda *a, **kw: None)
    summary, _ = collector.collect(_job(extra=0, target=1), Agent(), Browser(tmp_path),
                                   tmp_path, search_only=True)
    assert summary['target_reached'] and summary['status'] == 'completed'
    assert summary['counts']['target_metric'] == 'named_candidates'
    assert summary['counts']['target_progress'] >= 1
    assert summary['counts']['usable_named'] == 0
    assert summary['usable_independent_named'] == 0
    assert summary['model_calls'] == 0


def test_goal_target_stays_unreached_without_real_photo_evidence(tmp_path):
    row = _write_original(tmp_path, _textured((800, 600), 3, (80, 90, 110)))
    row.update(relevance={'tier': 'target_named'}, acquired_at=2)
    record = collage.process_original(tmp_path, row)
    (tmp_path/'goal.json').write_text(json.dumps({'started_at': 1, 'baseline_shas': []}), 'utf8')
    counts = compute(tmp_path, [row], {row['asset_sha']: record})
    assert counts['named_candidates'] == 1
    assert counts['target_metric'] == 'usable_named' and counts['target_progress'] == 0


def test_plain_search_receipt_import_and_api_agree(client, library, tmp_path, monkeypatch):
    from ref_lab import collection_queue
    monkeypatch.setattr('tests.photo_type_fixture.synthetic_type', lambda *a, **kw: None)
    monkeypatch.setattr(collection_queue, 'run_directory', lambda ident: tmp_path)
    project = client.post('/api/projects', json={'character': '西木野真姬', 'work': 'Love Live!'}).json()
    response = client.post(f"/api/projects/{project['id']}/jobs", json={
        'kind': 'collection', 'collection_mode': 'search', 'target_count': 1})
    assert response.status_code == 201
    job = response.json()
    running = library.start_collection_attempt(job['id'], job['revision'], 'audit-attempt', timeout=900)
    summary, _ = collector.collect(running, Agent(), Browser(tmp_path), tmp_path, search_only=True)
    library.update_search_stage(job['id'], 'audit-attempt', summary['status'], summary, 'isolated acquisition fixture')
    library.import_search_candidates(job['id'])
    snapshot = client.get(f"/api/jobs/{job['id']}/candidates").json()
    assert snapshot['job']['search_state'] == 'completed'
    assert snapshot['counts']['target_progress'] == summary['counts']['target_progress']
    assert snapshot['counts']['usable_named'] == 0
    assert snapshot['job']['imported_ids']
    image = client.get(snapshot['items'][0]['original_url'])
    assert image.status_code == 200
    assert hashlib.sha256(image.content).hexdigest() == snapshot['items'][0]['asset_sha']


@pytest.mark.parametrize('failure', ['exit', 'cancel'])
def test_failed_classification_keeps_native_stream_and_reported_usage(tmp_path, monkeypatch, failure):
    image = io.BytesIO()
    Image.new('RGB', (80, 80), 'blue').save(image, 'PNG')
    raw = image.getvalue(); sha = hashlib.sha256(raw).hexdigest()
    stop = threading.Event()
    monkeypatch.setattr(classification, 'find_antigravity_cli', lambda: 'synthetic-cli')
    monkeypatch.setattr(classification, 'antigravity_environment', lambda: {})
    monkeypatch.setattr(agent_collection, 'stop_process_tree', lambda process: None)
    stream = json.dumps({'event': 'result', 'result': {'status': 'ERROR',
                        'usage': {'total_tokens': 17}}})+'\n'

    def launch(command, **kwargs):
        kwargs['stdout'].write(stream); kwargs['stdout'].flush()
        class Process:
            returncode = 1 if failure == 'exit' else None
            def poll(self):
                if failure == 'cancel': stop.set()
                return self.returncode
        return Process()

    monkeypatch.setattr(classification.subprocess, 'Popen', launch)
    analyzer = classification.AntigravityClassifier(evidence_dir=tmp_path/'streams')
    with pytest.raises((classification.ClassificationUnavailable, InterruptedError)):
        analyzer.classify(raw, sha, stop)
    receipt = analyzer.last_receipt
    assert Path(receipt['stream_path']).read_text('utf8') == stream
    assert receipt['stream_sha'] == hashlib.sha256(stream.encode()).hexdigest()
    assert receipt['tokens'] == 17 and receipt['result_status'] == 'ERROR'
    assert receipt['status'] != 'succeeded' and 'read_evidence' not in receipt
