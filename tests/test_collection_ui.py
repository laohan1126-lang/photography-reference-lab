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
    monkeypatch.setattr('ref_lab.collector.run_browser_collection_job', lambda lib, ident: {**lib.job(ident), 'status':status, 'detail':'synthetic transport status'})
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
