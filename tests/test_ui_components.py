"""Real Chromium DOM + explicit TestClient bridge; NOT HTTP/cookie E2E.

Fixtures are synthetic pixels. Live HTTP and offline ZIPs are separately tested
in test_browser.py. The bridge is a test harness, never application code.
"""
from __future__ import annotations
import base64
import os
import re
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import expect
from browser_assertions import wait_until
from conftest import add_reference, card_data, review_data, image_bytes
from ref_lab.models import ProjectInput, JobInput, AnalysisResult

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def component_factory(client, library):
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as engine:
        executable = os.environ.get('LAB_CHROMIUM') or shutil.which('chromium')
        if not executable and not Path(engine.chromium.executable_path).exists():
            pytest.skip('Install Chromium to run browser component tests')
        browser = engine.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
        errors = []
        def mount(fragment=''):
            page = browser.new_page(viewport={'width':1440,'height':1100})
            page.set_default_timeout(10000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            def request(_source, path, method='GET', body=None, headers=None, multipart=None):
                if multipart is not None:
                    files = []
                    for item in multipart:
                        if 'filename' in item:
                            files.append((item['name'], (item['filename'], base64.b64decode(item['bytes']), item['type'])))
                        else:
                            files.append((item['name'], (None, item['value'])))
                    response = client.request(method, path, files=files, headers=headers)
                else:
                    response = client.request(method, path, content=body, headers=headers)
                return {'status':response.status_code, 'bytes':base64.b64encode(response.content).decode(),
                        'type':response.headers.get('content-type', 'application/octet-stream')}
            page.expose_binding('__testRequest', request)
            markup = re.sub(r'<link[^>]*>|<script[^>]*>.*?</script>', '', (ROOT/'web/index.html').read_text(encoding='utf-8'))
            page.set_content(markup)
            page.add_style_tag(content=(ROOT/'web/styles.css').read_text(encoding='utf-8'))
            page.evaluate('''fragment => {
                if(fragment)location.hash=fragment;
                window.fetch = async(path, options={}) => {
                    let body=options.body||null, multipart=null;
                    if(body instanceof FormData){
                        multipart=[];
                        for(const [name,value] of body.entries()){
                            if(value instanceof File){
                                let raw='';for(const byte of new Uint8Array(await value.arrayBuffer()))raw+=String.fromCharCode(byte);
                                multipart.push({name,filename:value.name,type:value.type,bytes:btoa(raw)});
                            }else multipart.push({name,value});
                        }body=null;
                    }
                    const r=await __testRequest(path,options.method||'GET',body,Object.fromEntries(options.headers||[]),multipart);
                    return new Response(Uint8Array.from(atob(r.bytes),c=>c.charCodeAt(0)),{status:r.status,headers:{'Content-Type':r.type}});
                };
                const pending=new WeakMap();
                const replace=()=>document.querySelectorAll('img').forEach(async img=>{
                    const src=img.getAttribute('src');
                    if(!src?.startsWith('/api/assets/')||pending.get(img)===src)return;
                    pending.set(img,src);
                    const r=await __testRequest(src);
                    if(img.getAttribute('src')===src&&r.status===200)img.src=`data:${r.type};base64,${r.bytes}`;
                });
                new MutationObserver(replace).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src']});
            }''', fragment)
            page.add_script_tag(content=(ROOT/'web/library-browser.js').read_text(encoding='utf-8'))
            page.add_script_tag(content=(ROOT/'web/app.js').read_text(encoding='utf-8'))
            page.locator('#application').wait_for(state='visible')
            page.locator('#library-grid' if 'view=library' in fragment else '#filmstrip').wait_for(state='attached')
            return page
        yield mount
        browser.close()
        assert not errors, errors


@pytest.fixture
def ui(component_factory, client, library, project):
    for i in range(3): add_reference(client, project, i)
    return component_factory(), library, project


def idle(page):
    wait_until(page, '!state.busy')


def advanced(page, title='审美笔记与借鉴点（选填）'):
    summary=page.locator('#detail-panel summary').filter(has_text=title).first
    if not summary.evaluate("n => n.parentElement.open"):
        summary.click()


def screenshot(page, name):
    folder=Path(os.environ.get('LAB_TEST_ARTIFACTS','.local/test-artifacts'))
    folder.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(folder/name),full_page=True)


def choose(page, key):
    page.locator(f'[data-decision="{key}"]').click()
    idle(page)


def test_ui_selection_preference_filters_and_responsive_layout(ui):
    page, library, project=ui
    advanced(page)
    page.get_by_label('喜欢什么／准备借鉴什么').fill('只借鉴动作，不借鉴服装')
    choose(page,'keep')
    assert library.references(project['id'],decision='keep')['items'][0]['preference']=='只借鉴动作，不借鉴服装'
    page.get_by_label('选择状态',exact=True).select_option('keep')
    expect(page.locator('#page-count')).to_have_text('1–1 / 1')
    screenshot(page,'desktop-component-synthetic.png')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(page,'mobile-component-synthetic.png')
    page.get_by_role('button',name='现场卡',exact=True).click()
    page.get_by_text('还没有已确认的现场卡',exact=True).wait_for()


def test_ui_agent_draft_then_explicit_acceptance(ui):
    page, library, project=ui
    page.locator('#auto-advance').uncheck()
    choose(page,'keep')
    page.get_by_role('button',name='制作现场卡',exact=True).click()
    page.locator('#download-task').wait_for()
    job=library.jobs(project['id'])[0]
    ref=library.references(project['id'],decision='keep')['items'][0]
    assert job['reference_ids']==[ref['id']]
    assert library.stats(project['id'])['ready']==0
    library.apply_analysis(ref['id'], AnalysisResult(review=review_data(ref['asset_sha']),card=card_data()), ref['revision'], 'synthetic-test-only', job['id'])
    page.locator('#editor-close').click()
    page.get_by_role('button',name='角色精选',exact=True).click()
    page.get_by_role('button',name='检查草稿并确认',exact=True).click()
    assert library.stats(project['id'])['ready']==0
    page.get_by_label('来源／权利说明',exact=True).select_option('owned')
    page.get_by_label('自有作品或来源说明',exact=True).fill('Generated synthetic fixture; not real visual analysis')
    page.get_by_label('我已核对图片、口令、安全与来源；不是仅依据搜索标题',exact=True).check()
    page.locator('#accept-card').click()
    page.locator('#editor').wait_for(state='hidden')
    expect(page.locator('.next-step')).to_contain_text('这张卡已由你确认')
    assert library.stats(project['id'])['ready']==1
    screenshot(page,'field-card-component-synthetic.png')


def test_ui_new_character_editable_note_and_blocked_job(ui):
    page, library, project=ui
    page.get_by_role('button',name='新建角色项目',exact=True).click()
    page.get_by_label('角色名 *',exact=True).fill('有马加奈')
    page.get_by_label('补充要求',exact=True).fill('日常人像和自然互动')
    page.get_by_role('button',name='建立项目',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    page.get_by_role('button',name='摄影笔记',exact=True).click()
    page.get_by_role('button',name='＋ 写摄影笔记',exact=True).click()
    page.get_by_label('笔记标题 *',exact=True).fill('引导笔记')
    page.get_by_label('正文（支持保留 Markdown）',exact=True).fill('# 观察\n<script>window.evil=1</script>\n先沟通。')
    page.get_by_role('button',name='保存笔记',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    page.locator('[data-note]').first.click()
    assert page.evaluate('window.evil') is None
    page.get_by_role('button',name='编辑笔记',exact=True).click()
    page.get_by_label('正文（支持保留 Markdown）',exact=True).fill('# 更新\n保留有效的引导。')
    page.get_by_role('button',name='保存笔记',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    expect(page.locator('[data-note]')).to_contain_text('保留有效的引导')
    page.get_by_role('button',name='采集任务',exact=True).click()
    page.get_by_role('button',name='＋ 建立采集任务',exact=True).click()
    page.get_by_label('本轮自由要求').fill('中文、日文检索；优先手势清楚的独立图片')
    page.get_by_role('button',name='建立采集任务',exact=True).click()
    page.locator('#download-task').wait_for()
    assert library.jobs()[0]['status']=='blocked'
    expect(page.locator('#editor')).to_contain_text('Codex / Antigravity')


@pytest.mark.parametrize('auto', [False, True])
def test_filmstrip_identity_scroll_keys_reject_and_recovery(component_factory, client, library, project, auto):
    for i in range(72): add_reference(client, project, i)
    page=component_factory()
    exercise_stable_strip(page, library, project, auto)


def exercise_stable_strip(page, library, project, auto):
    page.locator('#auto-advance').set_checked(auto)
    target=page.evaluate('''() => {
        const strip=document.querySelector('#filmstrip');strip.scrollLeft=2500;
        window.originalStrip=strip;window.oldNodes=new Map([...strip.children].map(n=>[n.dataset.ref,n]));
        const box=strip.getBoundingClientRect();
        const visible=[...strip.children].filter(n=>{const b=n.getBoundingClientRect();return b.left>box.left+70&&b.right<box.right-90});
        window.beforeClick=strip.scrollLeft;return visible[0].dataset.ref;
    }''')
    page.locator(f'#filmstrip [data-ref="{target}"]').click()
    assert page.evaluate("originalStrip===document.querySelector('#filmstrip') && originalStrip.scrollLeft===beforeClick")
    assert page.evaluate("[...originalStrip.children].every(n=>oldNodes.get(n.dataset.ref)===n)")
    before=page.evaluate('originalStrip.scrollLeft')
    page.locator('#next-image').click()
    page.locator('#previous-image').click()
    assert page.evaluate("document.querySelector('#filmstrip [aria-current=true]').dataset.ref")==target
    assert page.evaluate('originalStrip.scrollLeft')==before
    for key in ['k','m']:
        chosen=page.evaluate("document.querySelector('#filmstrip [aria-current=true]').dataset.ref")
        # Focus a non-input before pressing shortcuts; no hidden bypass or forced click.
        page.locator('#filmstrip [aria-current=true]').focus()
        page.keyboard.press(key)
        idle(page)
        saved = library.reference(chosen)
        assert saved['decision'] == ({'k':'keep','m':'maybe'}[key])
        assert page.evaluate("originalStrip===document.querySelector('#filmstrip')")
        assert page.evaluate('originalStrip.scrollLeft')>1500
    rejected=page.evaluate("document.querySelector('#filmstrip [aria-current=true]').dataset.ref")
    page.keyboard.press('x')
    expect(page.locator('#reject-dialog')).to_be_visible()
    expect(page.locator('#reject-reason-input')).to_be_focused()
    page.keyboard.press('Enter');idle(page)
    expect(page.locator(f'#filmstrip [data-ref="{rejected}"]')).to_have_count(0)
    assert library.reference(rejected)['decision']=='reject'
    assert page.evaluate("originalStrip===document.querySelector('#filmstrip')")
    assert page.evaluate('originalStrip.scrollLeft')>1500
    assert page.evaluate("[...originalStrip.children].filter(n=>oldNodes.has(n.dataset.ref)).every(n=>oldNodes.get(n.dataset.ref)===n)")
    box=page.locator('#filmstrip [aria-current=true]').bounding_box()
    strip=page.locator('#filmstrip').bounding_box()
    assert box['x']>=strip['x']-1 and box['x']+box['width']<=strip['x']+strip['width']+1
    page.get_by_role('button',name='已淘汰 / 恢复',exact=True).click()
    page.get_by_role('button',name='恢复这张图片',exact=True).click();idle(page)
    assert library.reference(rejected)['decision']!='reject'
    page.get_by_text('没有已淘汰图片',exact=True).wait_for()


def test_pagination_auto_advance_and_refresh_focus(component_factory, client, library, project):
    for i in range(65): add_reference(client, project, i)
    page=component_factory()
    page.locator('#filmstrip button').last.click()
    page.locator('#filmstrip [aria-current=true]').focus();page.keyboard.press('k');idle(page)
    expect(page.locator('#page-count')).to_have_text('61–65 / 65')
    first_id=page.evaluate('state.activeId')
    page.locator('#previous-image').click()
    expect(page.locator('#page-count')).to_have_text('1–60 / 65')
    assert page.evaluate('state.activeId===state.refs.at(-1).id')
    page.locator('#next-image').click()
    expect(page.locator('#page-count')).to_have_text('61–65 / 65')
    assert page.evaluate('state.activeId')==first_id
    page.locator('#auto-advance').uncheck();choose(page,'maybe')
    old_hash=page.evaluate('location.hash')
    page.close()
    reopened=component_factory(old_hash)
    expect(reopened.locator('#page-count')).to_have_text('61–65 / 65')
    assert reopened.evaluate('state.activeId')==first_id
    wait_until(reopened, 'document.querySelector("#main-image").naturalWidth>0')
    expect(reopened.locator('#main-image')).to_be_visible()
    assert library.reference(first_id)['decision']=='maybe'
    expect(reopened.locator('[data-decision=maybe]')).to_have_class('chosen')


def test_global_library_zero_projects_upload_and_multi_role_use(component_factory, client, library):
    page=component_factory()
    expect(page.locator('#project-header')).to_contain_text('我的审美库')
    page.get_by_role('button',name='＋ 收藏独立图片',exact=True).click()
    page.locator('#import-files').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':image_bytes(777)})
    page.get_by_role('button',name='开始导入',exact=True).click()
    page.locator('#close-receipt').click()
    assert library.projects()==[]
    assert library.inspirations()['total']==1
    first=library.create_project(ProjectInput(character='第一个项目'))
    second=library.create_project(ProjectInput(character='第二个项目'))
    fragment=page.evaluate('location.hash');page.close();page=component_factory(fragment)
    for project in (first,second):
        page.get_by_role('button',name='引用到拍摄项目',exact=True).click()
        page.locator('#editor select[name=project_id]').select_option(project['id'])
        page.locator('#editor button[type=submit]').click()
        page.locator('#editor').wait_for(state='hidden')
        page.get_by_role('button',name='♡ 我的审美库',exact=True).click()
        expect(page.locator('#detail-panel')).to_contain_text(project['character'])
    left=library.references(first['id'])['items'][0];right=library.references(second['id'])['items'][0]
    assert left['asset_sha']==right['asset_sha']
    assert left['review'] is None and right['card'] is None
    page.get_by_role('button',name='移出审美库',exact=True).click();idle(page)
    assert library.inspirations()['total']==0
    assert library.references(first['id'])['total']==1
    page.get_by_role('button',name='已移除收藏',exact=True).click()
    page.get_by_role('button',name='恢复收藏',exact=True).click();idle(page)
    assert library.inspirations()['total']==1


def test_stale_edit_conflict_does_not_claim_success_or_advance(ui, client):
    page,library,project=ui
    current=page.evaluate('state.activeId')
    ref=library.reference(current)
    response=client.patch(f'/api/references/{current}',json={'expected_revision':ref['revision'],'decision':'reject'})
    assert response.status_code==200
    choose(page,'keep')
    assert library.reference(current)['decision']=='reject'
    assert page.evaluate('state.activeId')==current
    expect(page.locator('#toast')).to_contain_text('修改')


def test_image_load_recovers_after_transient_error(ui):
    page,_,_=ui
    wait_until(page, 'document.querySelector("#main-image").naturalWidth>0')
    page.locator('#main-image').evaluate("img=>{img.hidden=true;document.querySelector('#missing-image').hidden=false;img.dispatchEvent(new Event('load'));}")
    expect(page.locator('#main-image')).to_be_visible()
    expect(page.locator('#missing-image')).to_be_hidden()


def test_browser_wait_does_not_require_unsafe_eval(component_factory):
    page = component_factory()
    # The real site sends this in its HTTP header. Exercise a false first poll
    # under the same eval restriction even in the component-only environment.
    page.evaluate('''() => {
        const policy = document.createElement('meta');
        policy.httpEquiv = 'Content-Security-Policy';
        policy.content = "script-src 'self'";
        document.head.appendChild(policy);
        window.testWaitReady = false;
        setTimeout(() => { window.testWaitReady = true; }, 150);
    }''')
    wait_until(page, 'window.testWaitReady')
    assert page.evaluate('window.testWaitReady') is True


def test_ui_batch_selection_copy_and_contact_board_entry(component_factory, client, library, project):
    source = add_reference(client, project, 91)
    target = client.post("/api/projects", json={"character": "转移目标角色"}).json()
    page = component_factory(f"view=references&project={project['id']}")

    advanced(page, "跨项目复用与模特沟通")
    page.get_by_role("button", name="加入批量选择", exact=True).click()
    expect(page.locator("#selection-actions")).to_have_text("已选 1 · 批量/沟通板")
    assert page.locator(f'#filmstrip [data-ref="{source["id"]}"]').evaluate("n => n.classList.contains('batch-selected')")

    page.locator("#selection-actions").click()
    page.locator("#selection-transfer").click()
    page.get_by_label("目标项目", exact=True).select_option(target["id"])
    page.get_by_label("操作", exact=True).select_option("copy")
    page.get_by_label("目标项目初始状态", exact=True).select_option("pending")
    page.get_by_role("button", name="执行", exact=True).click()
    page.locator("#editor").wait_for(state="hidden")
    idle(page)

    copied = library.references(target["id"])["items"]
    assert len(copied) == 1
    assert copied[0]["asset_sha"] == source["asset_sha"]
    assert copied[0]["decision"] == "pending"
    assert copied[0]["review"] is None and copied[0]["card"] is None
    assert library.reference(source["id"]).get("detached_at") is None

    page.locator("#selection-actions").click()
    page.locator("#selection-board").click()
    expect(page.locator("#editor")).to_contain_text("每页最多 4 张")
    expect(page.locator("[data-board-note]")).to_have_count(1)


def test_evidence_and_explicit_feedback_ui(component_factory, client, library, project):
    ref = add_reference(client, project, 200, title='轮廓光 低机位 动态')
    if ref.get('preflight_filtered'):
        client.post('/api/references/'+ref['id']+'/restore-preflight', json={'expected_revision':ref['revision']})
    page = component_factory()
    page.locator(f'#filmstrip [data-ref="{ref["id"]}"]').click()
    expect(page.locator('.tag-photo')).to_have_count(0)
    page.locator('.evidence-origin summary').click()
    expect(page.locator('.evidence-origin')).to_contain_text('来源标题与搜索词只用于发现')
    page.locator('#filmstrip [aria-current=true]').focus()
    page.keyboard.press('x')
    expect(page.locator('#reject-dialog')).to_be_visible()
    page.locator('#reject-reason-input').fill('我不喜欢这样的影调')
    page.locator('#reject-aesthetic').check()
    page.locator('#reject-confirm-btn').click()
    idle(page)
    saved = library.reference(ref['id'])
    assert saved['is_aesthetic_negative'] is True
    session = library.current_screening_session(project['id'])
    assert session['actions'][-1]['asset_sha'] == ref['asset_sha']
    page.locator('#optimize-skill-btn').click()
    expect(page.locator('#editor-title')).to_have_text('人工淘汰理由汇总')
    expect(page.locator('#editor-content')).to_contain_text('未更新 Skill')
    page.locator('#close-opt-dialog').click()
    expect(page.locator('#editor')).not_to_be_visible()


def test_finish_session_persists_only_explicitly_confirmed_feedback(component_factory,client,library,project):
    ref=add_reference(client,project,200)
    page=component_factory()
    page.locator('#filmstrip [aria-current=true]').focus();page.keyboard.press('k');idle(page)
    before=library.aesthetic_profile()
    page.locator('#finish-screening-btn').click()
    expect(page.locator('#session-confirm-form')).to_be_visible()
    expect(page.locator('input[name=hypothesis]')).not_to_be_checked()
    expect(page.locator('input[name=apply_choice][value=false]')).to_be_checked()
    page.locator('input[name=hypothesis]').check()
    page.locator('input[name=apply_choice][value=true]').check()
    page.locator('#session-confirm-form button').click()
    expect(page.locator('#editor')).not_to_be_visible()
    profile=library.aesthetic_profile()
    assert profile['dimensions']==before['dimensions']
    assert profile['project_use_exemplars'][0]['asset_sha']==ref['asset_sha']
    assert profile['positive_exemplars']==[]


def test_archive_failure_preserves_choice_and_is_visible(ui, monkeypatch):
    page, library, project = ui
    monkeypatch.setattr("ref_lab.archiver.export_asset_as_jpeg", lambda *_: False)
    page.locator('#auto-advance').uncheck()
    ident = page.locator('#filmstrip [aria-current=true]').get_attribute('data-ref')
    choose(page, 'keep')
    assert library.reference(ident)['decision'] == 'keep'
    expect(page.locator('#archive-error')).to_be_visible()
    expect(page.locator('#archive-error')).to_contain_text('选择已保存')
    expect(page.locator('#toast')).to_contain_text('归档未完成')
    expect(page.locator('#toast')).not_to_contain_text('已自动归位')
