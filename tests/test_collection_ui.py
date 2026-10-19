"""Actual Chromium UI, explicit TestClient bridge. Synthetic statuses, no live search."""
import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect
from ref_lab.models import JobInput
from test_ui_components import component_factory  # reuse the explicitly labelled bridge


def test_http200_blocked_stays_visible_with_recovery(component_factory, library, project, monkeypatch):
    monkeypatch.delenv('LAB_COLLECTION_COMMAND', raising=False)
    job = library.create_job(project['id'], JobInput(kind='collection'))
    page = component_factory()
    page.evaluate('id => jobHandoff(id)', job['id'])
    page.locator('#run-antigravity').click()
    expect(page.locator('#agent-run-status')).to_contain_text('未配置 LAB_COLLECTION_COMMAND')
    expect(page.locator('#toast')).to_contain_text('受阻')
    expect(page.locator('#editor')).to_be_visible()
    expect(page.locator('#run-antigravity')).to_be_enabled()
    expect(page.locator('#download-task')).to_be_visible()
    expect(page.locator('#import-task-result')).to_be_visible()
    assert library.job(job['id'])['status'] == 'blocked'
    assert '采集完成' not in page.locator('#toast').inner_text()
    folder = Path(os.environ.get('LAB_TEST_ARTIFACTS', '.local/test-artifacts'))
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder/'synthetic-collection-blocked.png'), full_page=True)


@pytest.mark.parametrize('status,expected,disabled', [('failed','执行失败',False),('cancelled','任务已取消',True),('running','任务仍在执行',True)])
def test_nonterminal_or_failure_response_never_announces_completion(component_factory, library, project, monkeypatch, status, expected, disabled):
    job = library.create_job(project['id'], JobInput(kind='collection'))
    # Only the returned status is synthetic; real HTTP handler and DOM are used.
    monkeypatch.setattr('ref_lab.agent_collection.run_collection_attempt', lambda lib, ident: {**lib.job(ident), 'status':status, 'detail':'synthetic transport status'})
    page = component_factory()
    page.evaluate('id => jobHandoff(id)', job['id'])
    page.locator('#run-antigravity').click()
    expect(page.locator('#toast')).to_contain_text(expected)
    expect(page.locator('#editor')).to_be_visible()
    assert page.locator('#run-antigravity').is_disabled() is disabled
    assert '采集完成' not in page.locator('#toast').inner_text()


def test_late_result_does_not_close_or_rewrite_another_dialog(component_factory, library, project):
    job = library.create_job(project['id'], JobInput(kind='collection'))
    page = component_factory()
    page.evaluate('id => jobHandoff(id)', job['id'])
    page.evaluate('''() => {
        const original = window.fetch;
        window.fetch = (path, options) => path.endsWith('/run-antigravity')
          ? new Promise(resolve => {window.finishSyntheticRun = () => resolve(new Response(JSON.stringify({status:'succeeded',detail:'synthetic receipt'}), {status:200,headers:{'Content-Type':'application/json'}}));})
          : original(path, options);
    }''')
    page.locator('#run-antigravity').click()
    page.evaluate("() => { modal('其他正在编辑的对话框', '<p id=other-dialog>保留这个内容</p>'); window.finishSyntheticRun(); }")
    expect(page.locator('#toast')).to_contain_text('候选包已导入')
    expect(page.locator('#editor')).to_be_visible()
    expect(page.locator('#editor-title')).to_have_text('其他正在编辑的对话框')
    expect(page.locator('#other-dialog')).to_have_text('保留这个内容')


def test_orphaned_running_job_offers_same_job_resume(component_factory, library, project, client):
    job = library.create_job(project['id'], JobInput(kind='collection', target_count=1))
    library.start_collection_attempt(job['id'], job['revision'], 'orphaned-attempt')

    response = client.get(f"/api/jobs/{job['id']}")
    assert response.status_code == 200 and response.json()['can_resume'] is True
    page = component_factory()
    page.evaluate('id => jobHandoff(id)', job['id'])
    expect(page.locator('#run-antigravity')).to_have_text('继续本次采集')
    expect(page.locator('#run-antigravity')).to_be_enabled()


def test_collection_editor_offers_two_modes_and_opens_live_candidate_queue(
        component_factory, library, project):
    page = component_factory()
    page.get_by_role('button', name='采集任务', exact=True).click()
    page.get_by_role('button', name='＋ 建立搜图任务', exact=True).click()
    mode = page.get_by_label('运行方式', exact=True)
    assert mode.locator('option').count() == 2
    assert '快速搜图' in mode.locator('option').nth(0).inner_text()
    assert '搜图 + AI 审核' in mode.locator('option').nth(1).inner_text()
    assert page.get_by_label('期望候选数量（质量优先，不凑数）', exact=True).input_value() == '4'
    mode.select_option('search_review')
    page.get_by_role('button', name='开始搜图', exact=True).click()
    page.locator('#cq-grid').wait_for(state='attached')
    assert library.jobs()[0]['collection_mode'] == 'search_review'
    expect(page.locator('#cq-status')).to_contain_text('搜索')


def test_candidate_queue_shows_acquired_originals_and_keeps_human_decision(
        component_factory, library, project, tmp_path, monkeypatch):
    import hashlib
    import json
    from PIL import Image
    from ref_lab import collection_queue
    from ref_lab.models import JobInput

    folder = tmp_path / 'candidate-run'
    (folder / 'images').mkdir(parents=True)
    rows = []
    for index in range(2):
        path = folder / 'images' / f'candidate-{index}.png'
        Image.new('RGB', (640, 960), (50 + index * 50, 90, 140)).save(path, format='PNG')
        rows.append({'asset_sha': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'original_path': str(path), 'page_url': f'https://example.org/post/{index}',
                     'image_url': f'https://example.org/image/{index}.png', 'width': 640, 'height': 960,
                     'search_query': 'synthetic quick search'})
    (folder / 'received.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf8')
    (folder / 'search-summary.json').write_text(json.dumps({
        'version': 1, 'status': 'completed', 'stop_reason': 'target_reached', 'target': 2,
        'counts': {'found': 2, 'duplicates': 0, 'errors': 0}, 'elapsed_seconds': 1.0,
        'model_calls': 0, 'tokens': 0}), encoding='utf8')
    review = {'identity': 'match', 'costume': 'not_required', 'confidence': 'high',
              'kind': 'cosplay_photo', 'reason': 'synthetic queue fixture',
              'reference_comparisons': []}
    (folder / 'review-audit.json').write_text(json.dumps({
        'version': 1, 'context_sha': 'a' * 64, 'items': {
            rows[0]['asset_sha']: {'asset_sha': rows[0]['asset_sha'], 'status': 'accepted',
                                   'accepted': True, 'decision': 'CONFIRMED', 'review': review},
            rows[1]['asset_sha']: {'asset_sha': rows[1]['asset_sha'], 'status': 'blocked',
                                   'accepted': False, 'decision': 'REVIEW_BLOCKED',
                                   'error': 'synthetic source assessment blocked'}}}), encoding='utf8')
    monkeypatch.setattr(collection_queue, 'run_directory', lambda job_id: folder)
    job = library.create_job(project['id'], JobInput(kind='collection', target_count=2, collection_mode='search'))
    page = component_factory()
    page.evaluate('id => openCandidateQueue(id,{autoStart:false})', job['id'])
    expect(page.locator('#cq-grid .candidate-card')).to_have_count(2)
    expect(page.locator('#cq-counts')).to_contain_text('2 已找到候选')
    expect(page.locator('#cq-counts')).to_contain_text('1 已通过')
    expect(page.locator('#cq-counts')).to_contain_text('1 审核受阻')
    expect(page.locator('#cq-status')).to_contain_text('搜索完成')
    page.locator(f'[data-sha="{rows[1]["asset_sha"]}"] [data-decision="keep"]').click()
    expect(page.locator('#cq-counts')).to_contain_text('2 已通过')
    expect(page.locator('#cq-counts')).to_contain_text('0 审核受阻')
    decisions = json.loads((folder / 'human-decisions.json').read_text('utf8'))['items']
    assert decisions[rows[1]['asset_sha']]['decision'] == 'keep'
    page.locator(f'[data-sha="{rows[1]["asset_sha"]}"] [data-decision="clear"]').click()
    expect(page.locator('#cq-counts')).to_contain_text('1 审核受阻')
    assert rows[1]['asset_sha'] not in json.loads((folder / 'human-decisions.json').read_text('utf8'))['items']
