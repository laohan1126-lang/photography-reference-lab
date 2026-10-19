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


def new_job(library, project, target_count=80, preferred_sources=None):
    return library.create_job(project['id'], JobInput(
        kind='collection', notes='合成回归，不是真实搜图', target_count=target_count,
        preferred_sources=preferred_sources or ['xiaohongshu', 'pinterest']))


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
    job = new_job(library, project, target_count=1, preferred_sources=['pinterest'])
    package = tmp_path / 'input.zip'
    package.write_bytes(candidate_zip(job, execution_report={
        'producer':'synthetic', 'status':'completed', 'summary':'complete fixture',
        'source_checks':[{'source':'pinterest','status':'usable'}],
        'query_log':[{'source':'pinterest','query':'synthetic','kept':1}], 'gaps':[]}))
    adapter(monkeypatch, tmp_path, '''import os, sys, pathlib, shutil
assert 'LAB_ACCESS_TOKEN' not in os.environ
assert 'LAB_COLLECTION_COMMAND' not in os.environ
assert pathlib.Path(os.environ['LAB_DATA_DIR']).parent == pathlib.Path.cwd()
assert pathlib.Path(os.environ['LAB_COLLECTION_HISTORY_DIR']).name == 'assets'
assert 'acquisition.query_strategy' in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
assert pathlib.Path('job.json').is_file()
shutil.copyfile(sys.argv[3], sys.argv[2])
''', package)
    monkeypatch.setenv('LAB_ACCESS_TOKEN', 'synthetic-secret-not-forwarded')
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'blocked' and result['collection_outcome'] == 'partial'
    assert len(result['last_receipt_reference_ids']) == 1
    assert any('冻结计划语言覆盖' in gap for gap in result['execution_report']['gaps'])
    ref = library.reference(result['imported_ids'][0])
    assert ref['decision'] == 'pending' and ref['review'] is None and not ref['field_ready']
    assert not ref['source']['source_confirmed']
    evidence = receipt(library, job)
    assert evidence['code'] == 'result_imported' and evidence['returncode'] == 0
    assert evidence['created'] == 1
    run_dir = library.settings.data_dir / 'agent-runs' / job['id']
    assert (run_dir / 'task' / 'job.json').is_file()
    assert (run_dir / 'result.zip').is_file()
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
    assert (library.settings.data_dir / 'agent-runs' / job['id'] / 'task' / 'job.json').is_file()


def test_blocked_result_preserves_usable_partial_assets(library, project, monkeypatch, tmp_path):
    job = new_job(library, project)
    package = tmp_path / 'partial.zip'
    package.write_bytes(candidate_zip(job, execution_report={'producer':'synthetic', 'status':'blocked', 'summary':'登录受阻', 'source_checks':[], 'query_log':[], 'gaps':['login']}))
    adapter(monkeypatch, tmp_path, 'import shutil,sys; shutil.copyfile(sys.argv[3],sys.argv[2])', package)
    result = run_collection_attempt(library, job['id'])
    assert result['status'] == 'blocked' and result['collection_outcome'] == 'partial'
    assert len(result['imported_ids']) == 1
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
    assert result['collection_outcome'] == 'blocked' and result['execution_report']['status'] == 'blocked'


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
        assert timeout_seconds(30)==3000 and timeout_seconds(100)==3600
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


def test_exited_adapter_does_not_leave_running_descendant(library, project, monkeypatch, tmp_path):
    job = new_job(library, project)
    marker = tmp_path / "descendant-must-not-exist"
    child_code = "import pathlib,sys,time; time.sleep(1.5); pathlib.Path(sys.argv[1]).write_text('orphan')"
    adapter(monkeypatch, tmp_path,
            "import subprocess,sys; subprocess.Popen([sys.executable, '-c', sys.argv[3], sys.argv[4]])",
            child_code, marker)
    result = run_collection_attempt(library, job["id"])
    assert result["status"] == "blocked" and receipt(library, job)["code"] == "result_missing"
    time.sleep(1.6)
    assert not marker.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object transport')
def test_windows_adapter_has_no_taskkill_path_dependency(monkeypatch):
    from ref_lab.agent_collection import configured_command
    executable = sys.executable
    command = [executable, '{task_file}', '{result_file}']
    monkeypatch.setenv('LAB_COLLECTION_COMMAND', json.dumps(command))
    monkeypatch.setattr('ref_lab.agent_collection.shutil.which', lambda value: executable if value == executable else None)
    assert configured_command() == command



def test_completed_collection_report_requires_target_and_matching_query_coverage(library, project):
    job = library.create_job(project['id'], JobInput(kind='collection', target_count=2))
    job = library.start_collection_attempt(job['id'], job['revision'], 'coverage-attempt')
    asset = library.ingest_asset(image_bytes())
    inserted = library.add_candidate(project['id'], CandidateInput(asset_sha=asset['id'], job_id=job['id']), attempt_id='coverage-attempt')
    report = CollectionReport(
        producer='synthetic', status='completed', summary='adapter said complete',
        source_checks=[{'source':'pinterest','status':'usable'}],
        query_log=[], gaps=[])

    saved = library.record_collection_report(job['id'], report, current_reference_ids=[inserted['reference']['id']], attempt_id='coverage-attempt')

    assert saved['status'] == 'blocked'
    assert saved['collection_outcome'] == 'partial'
    assert saved['execution_report']['status'] == 'blocked'
    assert any('1/2' in gap for gap in saved['execution_report']['gaps'])
    assert any('查询' in gap for gap in saved['execution_report']['gaps'])


def test_collection_cannot_bypass_report_gate_with_manual_succeeded_transition(library, project):
    job = new_job(library, project)
    job = library.transition_job(job['id'], 'running', job['revision'], 'manual collection')
    asset = library.ingest_asset(image_bytes())
    library.add_candidate(project['id'], CandidateInput(asset_sha=asset['id'], job_id=job['id']))
    latest = library.job(job['id'])

    with pytest.raises(Problem):
        library.transition_job(job['id'], 'succeeded', latest['revision'], 'one candidate is not completion')


def _coverage_snapshot(job, *, languages=('zh', 'en', 'ja'), usable_sources=None,
                       usable_languages=None, reported_languages=None, outcome='complete'):
    sources = sorted(job.get('preferred_sources', []))
    usable_sources = sorted(usable_sources if usable_sources is not None else sources)
    languages = sorted(languages)
    usable_languages = sorted(usable_languages if usable_languages is not None else languages)
    reported_languages = sorted(reported_languages if reported_languages is not None else usable_languages)
    return {
        'job_id': job['id'], 'binding_sha256': 'a' * 64, 'plan_sha256': 'b' * 64,
        'manifest_sha256': 'c' * 64, 'planned_sources': sources,
        'collector_outcome': outcome,
        'required_languages': languages, 'observed_languages': usable_languages,
        'usable_languages': usable_languages, 'reported_languages': reported_languages,
        'usable_sources': usable_sources, 'reported_sources': usable_sources,
    }


def _report_job_with_candidate(library, project, *, sources, target=1):
    job = library.create_job(project['id'], JobInput(
        kind='collection', target_count=target, preferred_sources=sources))
    job = library.start_collection_attempt(job['id'], job['revision'], 'coverage-attempt')
    asset = library.ingest_asset(image_bytes(88))
    inserted = library.add_candidate(project['id'], CandidateInput(
        asset_sha=asset['id'], job_id=job['id']), attempt_id='coverage-attempt')
    return job, inserted['reference']['id']


@pytest.mark.parametrize(('gaps', 'expected_status', 'expected_outcome'), [
    (['自动停止原因：soft_target_reached'], 'succeeded', 'complete'),
    (['实际候选核验缺口'], 'blocked', 'partial'),
])
def test_soft_target_stop_notice_is_not_a_missing_collection_requirement(
        library, project, gaps, expected_status, expected_outcome):
    job, ident = _report_job_with_candidate(library, project, sources=['pinterest'])
    report = CollectionReport(
        producer='synthetic', status='completed', summary='frozen plan covered',
        source_checks=[{'source': 'pinterest', 'status': 'usable'}],
        query_log=[{'source': 'pinterest', 'query': 'plan-step-zh-en-ja', 'kept': 1}],
        gaps=gaps)

    saved = library.record_collection_report(
        job['id'], report, current_reference_ids=[ident], attempt_id='coverage-attempt',
        collector_coverage=_coverage_snapshot(job))

    assert saved['status'] == expected_status
    assert saved['collection_outcome'] == expected_outcome
    assert saved['execution_report']['gaps'] == gaps


def test_collection_report_must_cover_each_job_source_and_frozen_plan_language(library, project):
    job, ident = _report_job_with_candidate(
        library, project, sources=['xiaohongshu', 'pinterest'])
    report = CollectionReport(
        producer='synthetic', status='completed', summary='Pinterest-only report',
        source_checks=[{'source': 'pinterest', 'status': 'usable'}],
        query_log=[{'source': 'pinterest', 'query': 'plan-step-en', 'kept': 1}],
        gaps=['自动停止原因：soft_target_reached'])

    saved = library.record_collection_report(
        job['id'], report, current_reference_ids=[ident], attempt_id='coverage-attempt',
        collector_coverage=_coverage_snapshot(
            job, languages=('zh', 'en', 'ja'), usable_sources=['pinterest']))

    assert saved['status'] == 'blocked'
    assert saved['collection_outcome'] == 'partial'
    assert any('preferred_sources' in gap or '来源' in gap for gap in saved['execution_report']['gaps'])


def test_report_without_bound_collector_plan_cannot_claim_language_complete(library, project):
    job, ident = _report_job_with_candidate(library, project, sources=['pinterest'])
    report = CollectionReport(
        producer='manual-package', status='completed', summary='language plan unavailable',
        source_checks=[{'source': 'pinterest', 'status': 'usable'}],
        query_log=[{'source': 'pinterest', 'query': 'self-consistent query', 'kept': 1}], gaps=[])

    saved = library.record_collection_report(
        job['id'], report, current_reference_ids=[ident], attempt_id='coverage-attempt')

    assert saved['status'] == 'blocked'
    assert saved['collection_outcome'] == 'partial'
    assert any('语言' in gap or '计划' in gap for gap in saved['execution_report']['gaps'])


def test_each_language_in_frozen_collector_plan_must_be_usable_and_reported(library, project):
    job, ident = _report_job_with_candidate(library, project, sources=['pinterest'])
    report = CollectionReport(
        producer='synthetic', status='completed', summary='two of three languages',
        source_checks=[{'source': 'pinterest', 'status': 'usable'}],
        query_log=[{'source': 'pinterest', 'query': 'plan-step-en', 'kept': 1},
                   {'source': 'pinterest', 'query': 'plan-step-zh', 'kept': 0}],
        gaps=['自动停止原因：soft_target_reached'])

    saved = library.record_collection_report(
        job['id'], report, current_reference_ids=[ident], attempt_id='coverage-attempt',
        collector_coverage=_coverage_snapshot(
            job, languages=('zh', 'en', 'ja'), usable_languages=('zh', 'en'),
            reported_languages=('zh', 'en'), outcome='partial'))

    assert saved['status'] == 'blocked'
    assert saved['collection_outcome'] == 'partial'
    assert any('语言' in gap for gap in saved['execution_report']['gaps'])


def test_bound_controller_blocked_outcome_is_not_relabelled_partial(library, project):
    job, ident = _report_job_with_candidate(library, project, sources=['pinterest'])
    report = CollectionReport(
        producer='verified-collection:synthetic', status='blocked', summary='执行受阻',
        source_checks=[{'source': 'pinterest', 'status': 'usable'}],
        query_log=[{'source': 'pinterest', 'query': 'plan-step-zh', 'kept': 1}],
        gaps=['视觉Agent发生不可恢复错误'])

    saved = library.record_collection_report(
        job['id'], report, current_reference_ids=[ident], attempt_id='coverage-attempt',
        collector_coverage=_coverage_snapshot(
            job, languages=('zh', 'en'), usable_languages=('zh',),
            reported_languages=('zh',), outcome='blocked'))

    assert saved['status'] == 'blocked'
    assert saved['collection_outcome'] == 'blocked'
