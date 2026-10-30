'''F6: the recovery allowance is what is left of the cumulative budget.

A recovery that already spent 40 s of the 60 s budget leaves 20 s for the next
one; a fresh 60 s window per attempt would let the total run far past the
declared limit. Normal collection time between two recoveries is not charged
to the recovery budget, and a recovery is only successful when the page it
returns to is really the original search page.

Synthetic browser only: no live page, no platform, no model.
'''
from __future__ import annotations

import time

import pytest

from tools import collect_verified as worker


def _browser(folder):
    folder.mkdir(parents=True, exist_ok=True)
    browser = worker.Browser(folder)
    browser.bsk = 'synthetic-bsk'
    browser.browser_id = 'synthetic-browser'
    browser.deadline = time.monotonic() + 10000.0
    browser.session = 'synthetic-session'
    browser.snapshot = lambda: {'url': 'about:blank', 'cards': []}
    return browser


def _search_page(query, cards=3):
    return {'url': 'https://www.xiaohongshu.com/search_result?keyword=' + query,
            'search': query,
            'cards': [{'page': 'https://example.invalid/' + str(index)} for index in range(cards)],
            'login_required': False, 'challenge': False}


def test_recovery_window_is_capped_by_the_remaining_budget(tmp_path, monkeypatch):
    browser = _browser(tmp_path / 'run')
    browser.recovery_seconds_used = 40.0
    observed = {}

    def rebuild():
        observed['deadline'] = browser.deadline
        return True

    monkeypatch.setattr(browser, '_rebuild_session', rebuild)
    started = time.monotonic()
    assert browser.recover() is True
    window = observed['deadline'] - started
    assert window <= 20.5, 'the window was %.3fs; only 20s of the 60s budget were left' % window
    assert window >= 19.0, 'the window was %.3fs; the remaining budget was not used' % window


def test_unused_recovery_budget_is_kept_for_the_next_attempt(tmp_path, monkeypatch):
    browser = _browser(tmp_path / 'run')
    browser.recovery_seconds_used = 10.0
    observed = {}

    def rebuild():
        observed['deadline'] = browser.deadline
        return True

    monkeypatch.setattr(browser, '_rebuild_session', rebuild)
    started = time.monotonic()
    assert browser.recover() is True
    window = observed['deadline'] - started
    assert 49.0 <= window <= 50.5, 'the window was %.3fs; 50s were still unused' % window


def test_no_recovery_starts_when_the_budget_is_spent(tmp_path, monkeypatch):
    browser = _browser(tmp_path / 'run')
    browser.recovery_seconds_used = browser.recovery_budget_seconds

    def rebuild():
        raise AssertionError('recovery started although the budget was spent')

    monkeypatch.setattr(browser, '_rebuild_session', rebuild)
    assert browser.can_recover() is False
    assert browser.recover() is False


def test_normal_work_between_recoveries_is_not_charged(tmp_path, monkeypatch):
    browser = _browser(tmp_path / 'run')
    clock = [100.0]
    monkeypatch.setattr(worker.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(worker.time, 'time', lambda: clock[0])

    def rebuild():
        clock[0] += 3.0
        return True

    monkeypatch.setattr(browser, '_rebuild_session', rebuild)
    assert browser.recover() is True
    assert browser.recovery_seconds_used == pytest.approx(3.0)
    clock[0] += 100.0            # ordinary collection work
    assert browser.can_recover() is True
    assert browser.recover() is True
    assert browser.recovery_seconds_used == pytest.approx(6.0)


def test_a_correct_page_after_a_command_timeout_is_recovered(tmp_path, monkeypatch):
    browser = _browser(tmp_path / 'run')
    browser.return_failed = True
    browser.return_error = 'navigate-back command timeout'
    query = '西木野真姬'
    step = {'source': 'xiaohongshu', 'query': query}
    monkeypatch.setattr(browser, 'snapshot', lambda: _search_page(query))

    def rebuild():
        raise AssertionError('the page was already correct; the session must not be rebuilt')

    monkeypatch.setattr(browser, '_rebuild_session', rebuild)
    assert browser.recover(step, reason='return') is True
    assert browser.return_failed is False
    assert not browser.return_error


def test_a_wrong_page_is_not_reported_as_recovered(tmp_path, monkeypatch):
    browser = _browser(tmp_path / 'run')
    browser.return_failed = True
    browser.return_error = 'navigate-back command timeout'
    step = {'source': 'xiaohongshu', 'query': '西木野真姬'}
    monkeypatch.setattr(browser, 'snapshot', lambda: {
        'url': 'https://www.xiaohongshu.com/explore/' + 'a' * 24, 'search': '',
        'cards': [], 'login_required': False, 'challenge': False})

    def command(*args, **kwargs):
        raise worker.BrowserInfrastructureError('navigate failed', action='navigate',
                                                code='command_timeout')

    monkeypatch.setattr(browser, 'command', command)
    monkeypatch.setattr(browser, '_rebuild_session', lambda: False)
    assert browser.recover(step, reason='return') is False
    assert browser.return_failed is True, 'a failed recovery must not clear the stale error'


def test_job_deadline_and_subsecond_command_timeout_are_never_extended(tmp_path,monkeypatch):
    import subprocess
    browser=_browser(tmp_path/'run');clock=[100.0]
    monkeypatch.setattr(worker.time,'monotonic',lambda:clock[0])
    browser.deadline=100.2;browser.recovery_seconds_used=40
    observed=[]
    def run(*args,**kwargs):
        observed.append(kwargs['timeout'])
        return subprocess.CompletedProcess(args,0,stdout='[]',stderr='')
    monkeypatch.setattr(worker.subprocess,'run',run)
    def rebuild():
        assert browser.deadline==100.2
        browser.command('browsers','--json',timeout=10)
        return True
    monkeypatch.setattr(browser,'_rebuild_session',rebuild)
    assert browser.recover()
    assert 0 < observed[0] <= .201
    browser.recovery_active=True
    browser.close()
    assert browser.deadline==100.2
    assert all(timeout<=.201 for timeout in observed)


def test_final_cleanup_grace_only_cancels_owned_session_and_records_elapsed(tmp_path,monkeypatch):
    import json,subprocess
    browser=_browser(tmp_path/'run');clock=[100.0]
    browser.deadline=99.;browser.start_request='owned-request';browser.session='owned-session'
    browser.recovery_seconds_used=40.
    monkeypatch.setattr(worker.time,'monotonic',lambda:clock[0])
    seen=[]
    def run(argv,**kwargs):
        seen.append((argv,kwargs['timeout']))
        assert argv[1:]==['session','request','owned-request','--cancel','--json'] or argv[1:]==['session','stop','owned-session']
        clock[0]+=2.
        return subprocess.CompletedProcess(argv,0,stdout='{"state":"closed"}',stderr='')
    monkeypatch.setattr(worker.subprocess,'run',run)
    browser.close()
    assert [timeout for _,timeout in seen]==[10.,8.]
    assert browser.deadline==99. and browser.recovery_seconds_used==40.
    receipt=json.loads((browser.folder/'browser-session.json').read_text('utf8'))
    assert receipt['state']=='closed'
    assert receipt['cleanup']=={'elapsed_seconds':4.,'grace_allowed':True,'grace_seconds':4.}
    with pytest.raises(worker.AgentCallFailed):browser.command('navigate','https://example.invalid/')
    assert len(seen)==2,'cleanup grace cannot fund later acquisition'


def test_cleanup_cannot_issue_navigation_inside_its_grace(tmp_path,monkeypatch):
    browser=_browser(tmp_path/'run');browser._cleanup_active=True
    monkeypatch.setattr(worker.subprocess,'run',lambda *a,**k:pytest.fail('acquisition ran during cleanup'))
    with pytest.raises(worker.AgentCallFailed,match='cleanup_operation_not_allowed'):
        browser.command('navigate','https://example.invalid/')


def test_rebuilt_wrong_page_keeps_the_original_return_failure(tmp_path,monkeypatch):
    browser=_browser(tmp_path/'run');browser.return_failed=True
    old_error=browser.return_error='original timeout'
    monkeypatch.setattr(browser,'_rebuild_session',lambda:True)
    monkeypatch.setattr(browser,'command',lambda *a,**k:'{}')
    monkeypatch.setattr(browser,'snapshot',lambda:_search_page('wrong query'))
    assert not browser.recover({'source':'xiaohongshu','query':'original query'})
    assert browser.return_failed and browser.return_error==old_error
