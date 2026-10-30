"""Chromium and helper regressions for the one-form search experience."""
from __future__ import annotations

from playwright.sync_api import expect

from test_ui_components import component_factory  # noqa: F401 - pytest fixture


def test_real_api_requires_explicit_search_mode_before_start(
        client, project, monkeypatch):
    from ref_lab import collection_stages
    monkeypatch.setattr(collection_stages, 'start_job', lambda lib, job_id: lib.job(job_id))

    defaulted = client.post(f"/api/projects/{project['id']}/jobs", json={
        'kind':'collection', 'target_count':8, 'notes':'契约回归'
    })
    assert defaulted.status_code == 201
    assert defaulted.json()['collection_mode'] == 'verified'
    rejected = client.post(f"/api/jobs/{defaulted.json()['id']}/start")
    assert rejected.status_code == 409

    search = client.post(f"/api/projects/{project['id']}/jobs", json={
        'kind':'collection', 'target_count':8, 'notes':'契约回归', 'collection_mode':'search'
    })
    assert search.status_code == 201
    assert search.json()['collection_mode'] == 'search'
    started = client.post(f"/api/jobs/{search.json()['id']}/start")
    assert started.status_code == 200
    assert started.json()['collection_mode'] == 'search'


def test_slow_request_shows_progress_and_candidate_placeholder_before_network(
        component_factory, library, monkeypatch):
    from ref_lab import collection_stages
    monkeypatch.setattr(collection_stages, 'start_job', lambda lib, job_id: lib.job(job_id))
    page = component_factory()
    page.locator('#studio-collect').click()
    page.get_by_label('角色名 *', exact=True).fill('慢响应角色')
    page.get_by_label('出自作品（选填）', exact=True).fill('回归作品')
    page.get_by_label('需要多少张', exact=True).fill('8')
    page.get_by_label('补充要求', exact=True).fill('舞台光与站姿')
    page.evaluate('''() => {
        const inner = window.fetch;
        window.__slowProjectsStarted = performance.now();
        window.fetch = (path, options={}) => path === '/api/projects' && (!options.method || options.method === 'GET')
          ? new Promise(resolve => setTimeout(() => resolve(inner(path, options)), 1500))
          : inner(path, options);
    }''')
    with page.expect_popup() as popup_info:
        immediate = page.evaluate('''() => {
            const form = document.querySelector('#editor form');
            const started = performance.now();
            form.requestSubmit();
            const status = document.querySelector('#search-progress');
            return {elapsed: performance.now() - started, hidden: status.hidden, text: status.textContent};
        }''')
    popup = popup_info.value
    assert immediate['hidden'] is False
    assert immediate['elapsed'] < 200
    assert '正在确认项目' in immediate['text']
    expect(popup.locator('body')).to_contain_text('候选窗口已打开')
    page.locator('#cq-grid').wait_for(state='attached')
    jobs = library.jobs()
    assert len(jobs) == 1
    assert jobs[0]['target_count'] == 8
    assert jobs[0]['collection_mode'] == 'search'
    expect(page.locator('#cq-status')).to_contain_text('准备')


def test_search_failure_states_retry_and_budget_actions_are_distinct(component_factory):
    page = component_factory()

    def render(job):
        page.evaluate('''job => {
            candidateQueueDialog('failure-job', job);
            renderCandidateQueue('failure-job', {job, counts:{}, search:{}, review:{}, items:[]}, 'project');
        }''', job)

    base = {'id':'failure-job','project_id':'project','status':'blocked','preparation_state':'failed',
            'search_state':'blocked','review_state':'idle','can_retry_search':True,
            'search_budget_exhausted':False}
    render({**base, 'last_error':'browser start failed: connection refused'})
    expect(page.locator('#cq-status')).to_contain_text('浏览器连接失败')
    expect(page.locator('#cq-retry-search')).to_be_visible()
    expect(page.locator('#cq-continue-search')).to_be_hidden()

    render({**base, 'last_error':'navigation timeout'})
    expect(page.locator('#cq-status')).to_contain_text('页面导航失败')

    render({**base, 'last_error':'session creation timed out waiting for extension'})
    expect(page.locator('#cq-status')).to_contain_text('无法创建采集窗口')
    expect(page.locator('#cq-continue-search')).to_be_hidden()

    render({**base, 'last_error':'Browser read Page.getFrameTree timed out: renderer is not answering'})
    expect(page.locator('#cq-status')).to_contain_text('浏览器控制暂时无响应')
    expect(page.locator('#cq-continue-search')).to_be_hidden()

    assert page.evaluate("searchFailureText({last_error:'required history baseline is missing'})") == ''

    render({**base, 'manual_action':'login_required', 'last_error':'login required'})
    expect(page.locator('#cq-status')).to_contain_text('要求登录')

    render({**base, 'last_error':'no_result'})
    expect(page.locator('#cq-status')).to_contain_text('没有找到可保存的结果')

    render({**base, 'can_retry_search':False, 'search_budget_exhausted':True})
    expect(page.locator('#cq-retry-search')).to_be_hidden()
    expect(page.locator('#cq-continue-search')).to_be_visible()
    expect(page.locator('#cq-continue-search')).to_have_text('预算耗尽 · 追加时间')


def test_name_lookup_progress_and_ambiguity_are_visible_without_manual_alias_form(component_factory):
    page = component_factory()
    def render(lookup):
        page.evaluate('''lookup => {
            const job={id:'name-job',preparation_state:'ready',search_state:'running',review_state:'idle'};
            candidateQueueDialog('name-job',job);
            renderCandidateQueue('name-job',{job,counts:{},search:{},review:{},items:[],name_lookup:lookup},'project');
        }''', lookup)
    render({'state':'running'})
    expect(page.locator('#cq-name-lookup')).to_contain_text('当前搜索继续进行')
    render({'state':'resolved','resolution':{'names':[{'kind':'character','name':'Nico Yazawa'}]}})
    expect(page.locator('#cq-name-lookup')).to_contain_text('Nico Yazawa')
    render({'state':'ambiguous'})
    expect(page.locator('#cq-name-lookup')).to_contain_text('请确认作品或角色全名')
    expect(page.locator('[name="search_aliases"]')).to_have_count(0)


def test_jobs_view_uses_summary_pagination_and_requests_detail_only_from_actions(component_factory):
    page = component_factory()
    page.evaluate('''() => {
        window.fetch = async path => {
            window.__summaryPath = path;
            return new Response(JSON.stringify({
                items:[
                    {id:'job-a',project_id:'p',kind:'collection',status:'blocked',is_split_mode:true,
                     project_snapshot:{character:'甲'},target_count:2,search_state:'failed',review_state:'idle',
                     can_retry_search:true,search_budget_exhausted:false,created_at:'2026-10-29T00:00:00Z'},
                    {id:'job-b',project_id:'p',kind:'collection',status:'blocked',is_split_mode:true,
                     project_snapshot:{character:'乙'},target_count:3,search_state:'failed',review_state:'idle',
                     can_retry_search:false,search_budget_exhausted:true,created_at:'2026-10-28T00:00:00Z'}
                ], total:22, limit:20, offset:0
            }), {status:200, headers:{'Content-Type':'application/json'}});
        };
    }''')
    page.evaluate('() => renderJobs()')
    assert page.evaluate('() => window.__summaryPath') == '/api/jobs?summary=true&limit=20&offset=0'
    expect(page.get_by_role('button', name='重试本次搜索（不增加预算）', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='预算耗尽 · 追加时间', exact=True)).to_be_visible()
    expect(page.locator('.pagination')).to_contain_text('1–2 / 22')
    expect(page.locator('#jobs-next')).to_be_enabled()
