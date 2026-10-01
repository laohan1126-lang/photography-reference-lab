"""Synthetic native-process/transport regressions, NOT live search or vision evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

from ref_lab.agent_collection import run_collection_attempt
from ref_lab.imports import import_candidates
from ref_lab.models import CollectionReport, JobInput, CandidateInput
from ref_lab.service import Problem
from conftest import image_bytes
from test_personal_library import candidate_zip


def new_job(library, project):
    return library.create_job(project['id'], JobInput(kind='collection', notes='合成回归，不是真实搜图'))


def adapter(monkeypatch, tmp_path, code, *extra):
    script = tmp_path / 'synthetic adapter.py'
    script.write_text(code, encoding='utf-8')
    monkeypatch.setenv('LAB_COLLECTION_COMMAND', json.dumps([sys.executable, str(script), '{task_file}', '{result_file}', *map(str, extra)]))
    monkeypatch.setenv('LAB_COLLECTION_TIMEOUT_SECONDS', '3')


def receipt(library, job):
    with library.db.read() as con:
        rows = con.execute("SELECT data FROM events WHERE entity_id=? AND action='collection.attempt_finished' ORDER BY id", (job['id'],)).fetchall()
    return json.loads(rows[-1][0])


@pytest.mark.parametrize('configuration,code', [
    ('', 'adapter_not_configured'), ('not json', 'invalid_configuration'),
    ('"shell text"', 'invalid_configuration'), ('[null]', 'invalid_configuration'),
    (json.dumps([sys.executable, 'no placeholders']), 'missing_placeholders'),
    (json.dumps(['surely-no-such-adapter-128971', '{task_dir}', '{result_file}']), 'executable_missing'),
])
def test_missing_or_invalid_adapter_never_spawns(library, project, monkeypatch, configuration, code):
    job = new_job(library, project)
    monkeypatch.setenv('LAB_COLLECTION_COMMAND', configuration)
    def forbidden(*args, **kwargs):
        raise AssertionError('No command/browser/fallback may start without an adapter')
    monkeypatch.setattr('ref_lab.agent_collection.subprocess.Popen', forbidden)
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'blocked'
    assert result['imported_ids'] == []
    assert 'active_attempt_id' not in result
    assert receipt(library, job)['code'] == code


def test_real_process_returns_valid_package_not_human_facts(library, project, monkeypatch, tmp_path):
    job = new_job(library, project)
    package = tmp_path / 'input.zip'
    package.write_bytes(candidate_zip(job))
    adapter(monkeypatch, tmp_path, '''import os, sys, pathlib, shutil
assert 'LAB_ACCESS_TOKEN' not in os.environ
assert 'LAB_COLLECTION_COMMAND' not in os.environ
assert pathlib.Path(os.environ['LAB_DATA_DIR']).parent == pathlib.Path.cwd()
assert 'acquisition.query_strategy' in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
assert pathlib.Path('job.json').is_file()
shutil.copyfile(sys.argv[3], sys.argv[2])
''', package)
    monkeypatch.setenv('LAB_ACCESS_TOKEN', 'synthetic-secret-not-forwarded')
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'succeeded'
    assert len(result['last_receipt_reference_ids']) == 1
    ref = library.reference(result['imported_ids'][0])
    assert ref['decision'] == 'pending' and ref['review'] is None and not ref['field_ready']
    assert not ref['source']['source_confirmed']
    evidence = receipt(library, job)
    assert evidence['code'] == 'result_imported' and evidence['returncode'] == 0
    assert evidence['created'] == 1
    assert not list((library.settings.data_dir / 'agent-runs').iterdir())
    assert not list((library.settings.data_dir / 'exports').iterdir())


@pytest.mark.parametrize('code,expected_status,expected_code', [
    ("pass", 'blocked', 'result_missing'),
    ("import sys; print('DO_NOT_LEAK_SECRET'); sys.exit(7)", 'failed', 'process_failed'),
    ("import pathlib,sys; pathlib.Path(sys.argv[2]).write_text('not a zip')", 'blocked', 'adapter_or_result_error'),
    ("import time; time.sleep(30)", 'blocked', 'process_timeout'),
])
def test_real_process_errors_are_not_success(library, project, monkeypatch, tmp_path, code, expected_status, expected_code):
    job = new_job(library, project)
    adapter(monkeypatch, tmp_path, code)
    if expected_code == 'process_timeout': monkeypatch.setenv('LAB_COLLECTION_TIMEOUT_SECONDS', '0.2')
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == expected_status
    assert receipt(library, job)['code'] == expected_code
    with library.db.read() as con:
        all_events = str(con.execute('SELECT data FROM events').fetchall())
    assert 'DO_NOT_LEAK_SECRET' not in result['detail'] + all_events
    assert not list((library.settings.data_dir / 'agent-runs').iterdir())


def test_blocked_result_preserves_usable_partial_assets(library, project, monkeypatch, tmp_path):
    job = new_job(library, project)
    package = tmp_path / 'partial.zip'
    package.write_bytes(candidate_zip(job, execution_report={'producer':'synthetic', 'status':'blocked', 'summary':'登录受阻', 'source_checks':[], 'query_log':[], 'gaps':['login']}))
    adapter(monkeypatch, tmp_path, 'import shutil,sys; shutil.copyfile(sys.argv[3],sys.argv[2])', package)
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'blocked' and len(result['imported_ids']) == 1
    assert '登录受阻' in result['detail']
    assert library.reference(result['imported_ids'][0])['decision'] == 'pending'


def test_empty_retry_cannot_borrow_historical_imports(library, project):
    job = new_job(library, project)
    blocked = {'producer':'synthetic', 'status':'blocked', 'summary':'partial', 'source_checks':[], 'query_log':[], 'gaps':[]}
    first = import_candidates(library, project['id'], candidate_zip(job, execution_report=blocked), job['id'])
    ident = first['reference_ids'][0]
    latest = library.job(job['id'])
    library.transition_job(job['id'], 'running', latest['revision'], 'retry')
    result = import_candidates(library, project['id'], candidate_zip(job, batch_id='empty-retry', candidates=[]), job['id'])
    assert result['job']['status'] == 'blocked'
    assert result['job']['last_receipt_reference_ids'] == []
    assert result['job']['imported_ids'] == [ident]
    assert library.reference(ident)['asset'] is not None


def test_standalone_report_is_not_current_import_evidence(library, project):
    job = new_job(library, project)
    asset = library.ingest_asset(image_bytes())
    library.add_candidate(project['id'], CandidateInput(asset_sha=asset['id'], job_id=job['id']))
    result = library.record_collection_report(job['id'], CollectionReport(producer='synthetic', status='completed', summary='no receipt'))
    assert result['status'] == 'blocked' and result['last_receipt_reference_ids'] == []


def test_valid_package_reimport_remains_idempotent(library, project):
    job = new_job(library, project)
    package = candidate_zip(job)
    first = import_candidates(library, project['id'], package, job['id'])
    second = import_candidates(library, project['id'], package, job['id'])
    assert first['created'] == 1 and second['created'] == 0 and second['existing'] == 1
    assert first['job'] == second['job']


def test_foreign_result_rejected_before_any_asset_import(library, project, monkeypatch, tmp_path):
    job = new_job(library, project)
    package = tmp_path / 'foreign.zip'; package.write_bytes(candidate_zip({'id':'not-this-job'}))
    adapter(monkeypatch, tmp_path, 'import shutil,sys; shutil.copyfile(sys.argv[3],sys.argv[2])', package)
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'blocked' and not result['imported_ids']
    assert receipt(library, job)['code'] == 'wrong_job'
    with library.db.read() as con: assert con.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 0


def test_new_attempt_and_cancellation_reject_stale_writes(library, project):
    job = new_job(library, project)
    first = library.start_collection_attempt(job['id'], job['revision'], 'old')
    with pytest.raises(Problem): library.start_collection_attempt(job['id'], first['revision'], 'duplicate')
    paused = library.transition_job(job['id'], 'blocked', first['revision'], 'pause')
    newest = library.start_collection_attempt(job['id'], paused['revision'], 'new')
    with pytest.raises(Problem): import_candidates(library, project['id'], candidate_zip(job), job['id'], attempt_id='old')
    with library.db.read() as con: assert con.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 0
    result = library.finish_collection_attempt(job['id'], 'old', 'failed', 'stale', {'code':'synthetic'})
    assert result == newest and result['active_attempt_id'] == 'new'
    cancelled = library.transition_job(job['id'], 'cancelled', newest['revision'], 'user cancelled')
    final = library.finish_collection_attempt(job['id'], 'new', 'blocked', 'do not overwrite', {})
    assert final['status'] == 'cancelled' and final['detail'] == cancelled['detail']


def test_real_process_is_stopped_on_cancel(library, project, monkeypatch, tmp_path):
    job = new_job(library, project)
    started = tmp_path / 'started'; marker = tmp_path / 'must-not-exist'
    adapter(monkeypatch, tmp_path, '''import pathlib,sys,time
pathlib.Path(sys.argv[3]).write_text('started')
time.sleep(1.5)
pathlib.Path(sys.argv[4]).write_text('worker outlived cancellation')
''', started, marker)
    results, errors = [], []
    def run():
        try: results.append(run_collection_attempt(library, job['id']))
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=run); thread.start()
    deadline = time.monotonic() + 5
    while not started.exists() and time.monotonic() < deadline: time.sleep(.02)
    assert started.exists()
    latest = library.job(job['id'])
    library.transition_job(job['id'], 'cancelled', latest['revision'], 'explicit cancel')
    thread.join(timeout=5)
    assert not thread.is_alive() and not errors
    assert results[0]['status'] == 'cancelled'
    assert receipt(library, job)['code'] == 'attempt_superseded'
    time.sleep(1.6)
    assert not marker.exists()


def test_http_200_blocked_is_truthful(client, library, project, monkeypatch):
    monkeypatch.delenv('LAB_COLLECTION_COMMAND', raising=False)
    job = new_job(library, project)
    response = client.post(f"/api/jobs/{job['id']}/run-antigravity")
    assert response.status_code == 200 and response.json()['status'] == 'blocked'
    assert client.get('/api/capabilities').json()['collection_adapter_configured'] is False


def test_legacy_visible_capture_cannot_reuse_previous_counts(library, project, monkeypatch):
    from types import SimpleNamespace
    from ref_lab.collector import collect_job
    job = new_job(library, project)
    asset = library.ingest_asset(image_bytes())
    library.add_candidate(project['id'], CandidateInput(asset_sha=asset['id'], job_id=job['id']))
    page = SimpleNamespace(locator=lambda selector: SimpleNamespace(count=lambda: 0))
    browser = SimpleNamespace(contexts=[SimpleNamespace(pages=[page])])
    class PlaywrightContext:
        def __enter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=lambda *a, **kw: browser))
        def __exit__(self, *args): return False
    monkeypatch.setattr('playwright.sync_api.sync_playwright', PlaywrightContext)
    monkeypatch.setattr('ref_lab.collector.capture_page', lambda *a, **kw: {'created':0, 'existing':0, 'ignored':0})
    result = collect_job(library, job['id'], 'http://127.0.0.1:9222')
    assert result['status'] == 'blocked' and len(result['imported_ids']) == 1


@pytest.mark.parametrize('value', ['nan','inf','0','3601','bad'])
def test_invalid_timeout_blocks_before_spawning(library, project, monkeypatch, tmp_path, value):
    job = new_job(library, project)
    adapter(monkeypatch, tmp_path, "raise AssertionError('must not execute')")
    monkeypatch.setenv('LAB_COLLECTION_TIMEOUT_SECONDS', value)
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'blocked' and receipt(library, job)['code'] == 'invalid_timeout'


def test_default_collection_timeout_survives_a_real_browserskill_pass():
    """A live BrowserSkill run needs >600s; the default must not kill it mid-flight."""
    from ref_lab.agent_collection import timeout_seconds

    previous = os.environ.pop("LAB_COLLECTION_TIMEOUT_SECONDS", None)
    try:
        assert timeout_seconds() >= 1800
    finally:
        if previous is not None:
            os.environ["LAB_COLLECTION_TIMEOUT_SECONDS"] = previous


def test_collage_splitting_expands_candidates():
    import io
    from PIL import Image, ImageDraw
    from tools.collect_adapter import process_and_expand_image

    # 1. Single image (solid color) should not be split
    single_img = Image.new("RGB", (640, 480), color=(120, 150, 180))
    buf = io.BytesIO()
    single_img.save(buf, format="JPEG")
    single_bytes = buf.getvalue()

    seen_shas = set()
    seen_dhashes = []
    base_meta = {"title": "单张参考图", "source": {"obtained_as": "platform_variant"}}

    items = process_and_expand_image(single_bytes, "jpg", base_meta, seen_shas, seen_dhashes)
    assert len(items) == 1
    assert items[0][2]["title"] == "单张参考图"
    assert items[0][2]["source"]["obtained_as"] == "platform_variant"

    # 2. 2x2 grid image with distinct colors and visible dividers
    grid_img = Image.new("RGB", (640, 480), color=(255, 255, 255))
    draw = ImageDraw.Draw(grid_img)
    # Cell 1
    draw.rectangle([0, 0, 318, 238], fill=(220, 50, 50))
    # Cell 2
    draw.rectangle([322, 0, 640, 238], fill=(50, 220, 50))
    # Cell 3
    draw.rectangle([0, 242, 318, 480], fill=(50, 50, 220))
    # Cell 4
    draw.rectangle([322, 242, 640, 480], fill=(220, 220, 50))

    grid_buf = io.BytesIO()
    grid_img.save(grid_buf, format="JPEG")
    grid_bytes = grid_buf.getvalue()

    grid_seen_shas = set()
    grid_seen_dhashes = []
    grid_meta = {"title": "动作拼图参考", "source": {"obtained_as": "platform_variant"}}

    split_items = process_and_expand_image(grid_bytes, "jpg", grid_meta, grid_seen_shas, grid_seen_dhashes)
    assert len(split_items) >= 2
    from ref_lab.models import PackCandidate
    for idx, item in enumerate(split_items):
        cand_meta = dict(item[2])
        cand_meta["id"] = f"cand-{idx+1:03d}"
        cand_meta["file"] = f"images/{item[0]}"
        assert "【动作#" in cand_meta["title"]
        assert cand_meta["source"]["obtained_as"] == "platform_variant"
        # Must be 100% strictly valid PackCandidate model
        validated = PackCandidate.model_validate(cand_meta)
        assert validated.id == f"cand-{idx+1:03d}"


def test_xhs_gallery_slides_extraction_and_packaging():
    import json
    from unittest.mock import MagicMock
    from ref_lab.models import PackCandidate
    from tools.collect_adapter import download_gallery_images, fetch_xhs_detail_metadata

    # 1. Test mock download_gallery_images
    mock_run = MagicMock()
    fake_b64 = "data:image/jpeg;base64," + "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    mock_run.return_value.stdout = json.dumps({
        "ok": True,
        "value": [
            {"url": "http://example.com/slide1.jpg", "data": fake_b64},
            {"url": "http://example.com/slide2.jpg", "data": fake_b64},
            {"url": "http://example.com/slide3.jpg", "data": fake_b64},
        ]
    })

    import subprocess
    orig_run = subprocess.run
    try:
        subprocess.run = mock_run
        items = download_gallery_images("bsk", "sess-123", ["u1", "u2", "u3"], {})
        assert len(items) == 3
        assert items[0]["url"] == "http://example.com/slide1.jpg"

        # 2. Test candidate model compliance with gallery pagination tags
        total = len(items)
        candidates = []
        for idx, it in enumerate(items):
            cand_dict = {
                "id": f"cand-{idx+1:03d}",
                "file": f"images/test_{idx+1}.jpg",
                "title": f"双一 正片参考 (P{idx+1}/{total})",
                "source": {
                    "page_url": "https://www.xiaohongshu.com/search_result/6904288b0000000004004513?xsec_token=123",
                    "image_url": it["url"],
                    "author": "测试COS",
                    "title": f"双一 正片参考 (P{idx+1}/{total})",
                    "search_query": "双一 cos",
                    "rights": "unknown",
                    "source_confirmed": False,
                    "obtained_as": "platform_variant",
                },
                "discovery_intent": "exact_character",
                "discovery_reason": f"通过 BrowserSkill 检索「双一 cos」在小红书图集发现 (P{idx+1}/{total})",
                "discovery_url": "https://www.xiaohongshu.com/search_result?keyword=双一",
                "notes": "诅咒你！双一cos正片",
            }
            validated = PackCandidate.model_validate(cand_dict)
            assert validated.id == f"cand-{idx+1:03d}"
            assert f"P{idx+1}/{total}" in validated.title
            candidates.append(validated)

        assert len(candidates) == 3
    finally:
        subprocess.run = orig_run
