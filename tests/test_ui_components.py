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
from tools.import_dot_drive_batch import candidate_data

ROOT = Path(__file__).resolve().parents[1]


def open_navigation(page):
    # Desktop has a persistent project index; mobile moves navigation into its drawer.
    toggle = page.locator('#toggle-project-nav')
    if page.viewport_size['width'] <= 700 and toggle.is_visible() and toggle.get_attribute('aria-expanded') != 'true':
        toggle.click()
    more = page.locator('.global-more')
    if more.count() and not more.evaluate('n => n.open'):
        more.locator('summary').click()


def test_dot_study_queue_keeps_candidate_separate_from_taste(component_factory, client, library):
    asset = library.ingest_asset(image_bytes(83))
    source = {"编号": "P366", "Drive文件ID": "drive-fixture-123", "图片文件名": "P366.jpg",
              "主题": "合成测试摄影参考", "公开出处": "https://example.org/photo",
              "助手判断": "手位与背景线条供核对", "现场借鉴": "轻扶道具",
              "用户反馈": {"状态": "尚无对应用户反馈"}, "作者与来源使用限制": ["测试用"]}
    library.add_study_candidate(candidate_data(source, asset["id"], None))
    page = component_factory("view=study")
    expect(page.locator("#project-header h1")).to_have_text("待筛摄影参考")
    expect(page.locator("#main-image")).to_be_visible()
    expect(page.locator("#detail-panel")).to_contain_text("Dot 文案线索")
    expect(page.locator('[data-study-reason="composition"]')).to_have_attribute("aria-pressed", "false")
    page.locator('[data-study-reason="composition"]').click()
    expect(page.locator('[data-study-reason="composition"]')).to_have_attribute("aria-pressed", "true")
    page.locator('[data-study-reason="pose"]').click()
    expect(page.locator('[data-study-reason="pose"]')).to_have_attribute("aria-pressed", "true")
    open_navigation(page)
    page.locator('[data-view="inspiration"]').click()
    open_navigation(page)
    page.locator('[data-view="study"]').click()
    expect(page.locator('[data-study-reason="composition"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator('[data-study-reason="pose"]')).to_have_attribute("aria-pressed", "true")
    page.locator('[data-study-status="priority"]').click()
    expect(page.locator("#detail-panel")).to_contain_text("值得优先看")
    assert library.study_candidate("dot:P366")["status"] == "priority"
    assert library.study_candidate("dot:P366")["study_reasons"] == ["composition", "pose"]
    assert library.inspirations()["total"] == 0


@pytest.fixture
def fast_search_start(monkeypatch):
    from ref_lab import collection_stages
    monkeypatch.setattr(collection_stages, 'start_job', lambda lib, job_id: lib.job(job_id))


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
            # Match the active HTML resources exactly, not abandoned theme layers.
            for filename in ['styles.css','kana-editorial.css']:
                page.add_style_tag(content=(ROOT/'web'/filename).read_text(encoding='utf-8'))
            for node in page.locator('img[src^="/static/ui-art/"]').element_handles():
                name = node.get_attribute('src').split('/static/', 1)[1]
                asset = ROOT / 'web' / name
                if asset.is_file():
                    node.evaluate('(n,u)=>n.src=u', 'data:image/svg+xml;base64,' + base64.b64encode(asset.read_bytes()).decode())
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
                    if((!src?.startsWith('/api/assets/')&&!src?.startsWith('/api/jobs/'))||pending.get(img)===src)return;
                    pending.set(img,src);
                    const r=await __testRequest(src);
                    if(img.getAttribute('src')===src&&r.status===200)img.src=`data:${r.type};base64,${r.bytes}`;
                });
                new MutationObserver(replace).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src']});
            }''', fragment)
            page.add_script_tag(content=(ROOT/'web/library-browser.js').read_text(encoding='utf-8'))
            page.add_script_tag(content=(ROOT/'web/kana.js').read_text(encoding='utf-8'))
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


@pytest.mark.parametrize('has_project', [False, True])
@pytest.mark.parametrize('entry', ['studio', 'jobs'])
def test_search_uses_one_form_and_one_submit_without_compulsory_second_step(component_factory, library, fast_search_start, has_project, entry):
    project = library.create_project(ProjectInput(character='封面入口回归')) if has_project else None
    page = component_factory()
    if entry == 'studio':
        page.locator('#studio-collect').focus()
        page.keyboard.press('Enter')
    else:
        open_navigation(page)
        page.get_by_role('button', name='采集任务', exact=True).click()
        page.locator('#create-collection').click()
    expect(page.locator('#editor')).to_be_visible()
    character = page.locator('[name="character"]')
    expect(character).to_be_visible()
    expect(character).to_have_value('')
    assert page.locator('[name="project_id"]').count() == 0
    character.fill('自由输入的新角色')
    page.locator('[name="work"]').fill('回归作品')
    page.get_by_label('需要多少张', exact=True).fill('12')
    page.get_by_label('补充要求', exact=True).fill('想找回眸和坐姿')
    expect(page.locator('[name="costume"]')).not_to_be_visible()
    page.get_by_text('服装与拍摄条件（选填）', exact=True).click()
    page.locator('[name="costume"]').fill('自定服装')
    page.locator('[name="gear"]').fill('50mm 与一盏柔光')
    assert len(library.projects()) == int(has_project)
    assert library.jobs() == []
    assert page.get_by_role('button', name='下一步：设置搜图', exact=True).count() == 0
    page.get_by_role('button', name='开始搜图', exact=True).click()
    page.locator('#cq-grid').wait_for(state='attached')
    created = next(p for p in library.projects() if p['character'] == '自由输入的新角色')
    assert (created['work'], created['costume'], created['brief']) == ('回归作品', '自定服装', '想找回眸和坐姿')
    if project:
        assert library.project(project['id'])['character'] == '封面入口回归'
    assert len(library.jobs()) == 1
    assert library.jobs()[0]['project_id'] == created['id']
    assert library.jobs()[0]['target_count'] == 12
    assert '想找回眸和坐姿' in library.jobs()[0]['notes']
    assert '50mm 与一盏柔光' in library.jobs()[0]['notes']


@pytest.mark.parametrize('entry', ['studio', 'jobs'])
def test_search_with_only_character_reuses_one_compatible_project(component_factory, library, fast_search_start, entry):
    original = library.create_project(ProjectInput(character=' 安养寺姬芽 ', work='莲之空', costume='',
                                                     brief='只保留原来的要求'))
    page = component_factory()
    if entry == 'studio':
        page.locator('#studio-collect').click()
    else:
        open_navigation(page)
        page.get_by_role('button', name='采集任务', exact=True).click()
        page.locator('#create-collection').click()
    page.get_by_label('角色名 *', exact=True).fill('安养寺姬芽')
    page.get_by_label('补充要求', exact=True).fill('本轮只看坐姿')
    page.get_by_text('服装与拍摄条件（选填）', exact=True).click()
    page.get_by_label('设备／环境限制', exact=True).fill('50mm 与一盏柔光')
    page.get_by_role('button', name='开始搜图', exact=True).click()
    page.locator('#cq-grid').wait_for(state='attached')
    job = library.jobs()[0]
    assert job['notes'] == '本次补充要求：\n本轮只看坐姿\n\n本次设备／环境限制：\n50mm 与一盏柔光'
    assert job['project_id'] == original['id']
    assert len(library.projects()) == 1
    assert library.project(original['id'])['brief'] == '只保留原来的要求'
    assert library.project(original['id'])['gear'] == 'Sony A7M4；50mm f/1.8；24–240mm；Godox V100 一盏、灯架、圆形柔光附件。以 cosplay／日常、社交、现场可执行为主。'


def test_search_ambiguity_requires_explicit_project_choice(component_factory, library, fast_search_start):
    first = library.create_project(ProjectInput(character='安养寺姬芽', work='莲之空'))
    second = library.create_project(ProjectInput(character='安养寺姬芽', work='另一作品', costume='另一服装'))
    page = component_factory()
    page.locator('#studio-collect').click()
    page.get_by_label('角色名 *', exact=True).fill('安养寺姬芽')
    page.get_by_role('button', name='开始搜图', exact=True).click()
    expect(page.locator('#editor-title')).to_have_text('选择继续搜图的项目')
    expect(page.locator('#editor-content')).to_contain_text('原有筛选会保留')
    expect(page.locator('#editor-content')).to_contain_text(f"创建 {first['created_at'][:10]}")
    expect(page.locator('#editor-content')).to_contain_text(f"创建 {second['created_at'][:10]}")
    expect(page.locator('#editor-content')).not_to_contain_text(first['id'])
    picker = page.get_by_label('使用哪个项目', exact=True)
    expect(picker).to_have_value('')
    picker.select_option(second['id'])
    page.get_by_role('button', name='开始搜图', exact=True).click()
    page.locator('#cq-grid').wait_for(state='attached')
    assert library.jobs()[0]['project_id'] == second['id']
    assert len(library.projects()) == 2
    assert library.project(first['id'])['revision'] == first['revision']


def test_search_creates_explicitly_different_costume_without_merging(component_factory, library, fast_search_start):
    original = library.create_project(ProjectInput(character='安养寺姬芽', work='莲之空', costume='原服装', brief='原要求'))
    page = component_factory()
    page.locator('#studio-collect').click()
    page.get_by_label('角色名 *', exact=True).fill('安养寺姬芽')
    page.get_by_label('出自作品（选填）', exact=True).fill('莲之空')
    page.get_by_text('服装与拍摄条件（选填）', exact=True).click()
    page.get_by_label('服装／皮肤版本（选填）', exact=True).fill('新服装')
    page.get_by_role('button', name='开始搜图', exact=True).click()
    page.locator('#cq-grid').wait_for(state='attached')
    created = next(p for p in library.projects() if p['costume'] == '新服装')
    assert created['brief'] == ''
    assert library.jobs()[0]['project_id'] == created['id']
    assert library.project(original['id'])['brief'] == '原要求'
    assert original['id'] != created['id']


def test_project_delete_and_restore_are_reachable_and_preserve_notes(client, component_factory, library):
    project = library.create_project(ProjectInput(character='可恢复角色', work='回归作品'))
    note = client.post(f"/api/projects/{project['id']}/notes", json={'title': '保留笔记', 'body': '不能随项目删除'}).json()
    page = component_factory(f"view=references&project={project['id']}")
    page.evaluate("() => window.confirm = () => true")
    expect(page.locator('#archive-project')).to_be_visible()
    page.locator('#archive-project').click()
    expect(page.locator('#archived-projects')).to_be_visible()
    expect(page.locator('#toast')).to_contain_text('可恢复')
    assert all(p['id'] != project['id'] for p in library.projects())
    page.locator('#archived-projects').click()
    expect(page.locator('#editor-title')).to_have_text('已删除项目 · 可恢复')
    page.get_by_role('button', name='恢复项目', exact=True).click()
    restored = library.project(project['id'])
    assert restored['archived_at'] is None
    assert library.notes(project['id'])[0]['id'] == note['id']


def test_lifecycle_helper_matching_without_browser():
    import shutil
    import subprocess

    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for the production script helper test')
    script = r'''
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const start=source.indexOf('function projectField');
const end=source.indexOf('function projectEditor',start);
if(start<0||end<0)throw new Error('production lifecycle helpers missing');
const calls=[];
let projects=[];
let archived=[];
const modals=[],forms=[];
const progress={textContent:''};const element=()=>({handlers:{},hidden:false,open:false,classList:{toggle(){}},value:'',setAttribute(){},showModal(){this.open=true},close(){this.open=false},querySelector(selector){return selector==='#search-progress'?progress:null}});
const launched=[];
const context={console,setTimeout,clearTimeout,Date,Object,String};
context.state={projects,project:null,archivedProjects:archived,view:'references',selection:[],dirty:false,busy:false};
context.api=async(path,options={})=>{calls.push({path,method:options.method||'GET',body:options.body});if(path==='/api/projects'&&(!options.method||options.method==='GET'))return context.state.projects;if(path.endsWith('/jobs'))return {id:'job'};return {id:'new-id',character:options.body?.character}};
context.closeModal=()=>{};context.resetFilters=()=>{};context.loadProjects=async()=>{};context.openCandidateQueue=async(id,options)=>launched.push({id,job:options.job});context.safeCandidateFile=()=>{};context.toast=()=>{};
context.modal=(title,body)=>{modals.push({title,body});return element()};context.select=(label,name,choices,value)=>Object.values(choices).join(' ');context.formSubmit=(root,handler)=>forms.push(handler);
vm.createContext(context);
vm.runInContext(source.slice(start,end)+'\nglobalThis.match=compatibleProjects;globalThis.open=openSearchProject;',context);
(async()=>{
 const original={id:'old',character:' 安养寺姬芽 ',work:'莲之空',costume:'',brief:'保留',created_at:'2026-09-28T00:00:00Z',revision:2};
 const variant={id:'variant',character:'安养寺姬芽',work:'另一作品',costume:'另一服装',created_at:'2026-10-29T00:00:00Z',revision:1};
 context.state.projects=[original,variant];
 const byCharacter=context.match({character:'安养寺姬芽',work:'',costume:''});
 if(byCharacter.length!==2)throw new Error('character-only must list ambiguous variants');
 const exact=context.match({character:'安养寺姬芽',work:'莲之空',costume:''});
 if(exact.length!==1||exact[0].id!=='old')throw new Error('filled work must narrow matching');
 const unknown=context.match({character:'安养寺姬芽',work:'新作品',costume:''});
 if(unknown.length)throw new Error('explicit new work must not reuse old version');
 await context.open({character:'安养寺姬芽',work:'',costume:'',target_count:30});
 const picker=modals.at(-1);
 if(picker?.title!=='选择继续搜图的项目'||!picker.body.includes('2026-09-28')||!picker.body.includes('2026-10-29'))throw new Error('ambiguous projects did not show a dated choice');
 if(calls.some(c=>c.path==='/api/projects'&&c.method==='POST'))throw new Error('ambiguity created a project');
 await forms.at(-1)({project_id:'variant'});
 if(!calls.some(c=>c.path==='/api/projects/variant/jobs'&&c.method==='POST'))throw new Error('selected project did not start a job directly');
 context.state.projects=[original];
 await context.open({character:'安养寺姬芽',work:'',costume:'',brief:'新要求',target_count:30});
 if(calls.some(c=>c.path==='/api/projects'&&c.method==='POST'))throw new Error('unique compatible project was duplicated');
 if(!calls.some(c=>c.path==='/api/projects/old/jobs'&&c.method==='POST')||!launched.length)throw new Error('reuse did not start the same job flow');
 console.log('LIFECYCLE_HELPER_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run([node,'-e',script],cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    assert 'LIFECYCLE_HELPER_PASS' in result.stdout


def test_search_refreshes_projects_and_carries_current_notes_into_job_without_browser():
    import shutil
    import subprocess

    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for the production script helper test')
    script = r'''
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const start=source.indexOf('function projectField');
const end=source.indexOf('function projectEditor',start);
if(start<0||end<0)throw new Error('production search helpers missing');
const calls=[],modals=[],forms=[],launched=[];
const original={id:'old',character:'安养寺姬芽',work:'莲之空',costume:'',brief:'原项目要求',gear:'原设备',revision:2,created_at:'2026-09-28T00:00:00Z'};
const other={id:'other',character:'安养寺姬芽',work:'另一作品',costume:'另一服装',brief:'另一项目',gear:'另一设备',revision:1,created_at:'2026-10-01T00:00:00Z'};
const remote=[original,other];
const progress={textContent:''},formNode={querySelector:selector=>selector==='#search-progress'?progress:null};
const context={console,setTimeout,clearTimeout,Object,String};
context.state={projects:[],archivedProjects:[],project:null,view:'references',selection:[],dirty:false,busy:false,caps:{}};
context.api=async(path,options={})=>{
 calls.push({path,method:options.method||'GET',body:options.body});
 if(path==='/api/projects'&&(!options.method||options.method==='GET'))return remote.map(p=>({...p}));
 if(path==='/api/projects')return {id:'new'};
 if(path.endsWith('/jobs'))return {id:'job'};
 return {};
};
context.modal=(title,body)=>{modals.push({title,body});return formNode};context.formSubmit=(root,handler)=>forms.push(handler);
context.select=()=>'';context.openCandidateQueue=async(id,options)=>launched.push({id,job:options.job});context.safeCandidateFile=()=>{};
vm.createContext(context);
vm.runInContext(source.slice(start,end)+'\nglobalThis.open=openSearchProject;',context);
(async()=>{
 const data={character:'安养寺姬芽',work:'',costume:'',brief:'本轮只看坐姿',gear:'50mm 与一盏柔光',target_count:30};
 await context.open(data);
 const refresh=calls.findIndex(c=>c.path==='/api/projects'&&c.method==='GET');
 if(refresh<0)throw new Error('project list was not refreshed');
 const picker=forms.at(-1),opened=modals.at(-1);
 if(opened?.title!=='选择继续搜图的项目')throw new Error('latest project list was not used');
 await picker({project_id:'old'});
 const job=calls.find(c=>c.path==='/api/projects/old/jobs'&&c.method==='POST');
 if(!job||!job.body.notes.includes('本轮只看坐姿')||!job.body.notes.includes('50mm 与一盏柔光'))throw new Error('current notes missing from job request');
 if(job.body.target_count!==30||job.body.collection_mode!=='search'||Object.hasOwn(job.body,'goal_id')||Object.hasOwn(job.body,'search_aliases'))throw new Error('search submitted wrong protocol fields');
 if(calls.some(c=>c.path==='/api/projects/old'&&c.method==='PUT'))throw new Error('reused project was edited');
 if(original.brief!=='原项目要求'||original.gear!=='原设备')throw new Error('original project requirements changed');
 remote.push({id:'newly-added',character:'安养寺姬芽',work:'新作品',costume:'',created_at:'2026-10-29T00:00:00Z'});
 calls.length=0;modals.length=0;forms.length=0;launched.length=0;
 await context.open({...data,work:'新作品'});
 if(calls.some(c=>c.path==='/api/projects'&&c.method==='POST'))throw new Error('refreshed match created duplicate');
 if(!calls.some(c=>c.path==='/api/projects/newly-added/jobs'&&c.method==='POST')||launched[0]?.id!=='job')throw new Error('refreshed match did not start one job');
 console.log('SEARCH_NOTES_REFRESH_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run([node,'-e',script],cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    assert 'SEARCH_NOTES_REFRESH_PASS' in result.stdout


def test_search_refresh_failure_does_not_create_without_browser():
    import shutil
    import subprocess

    node=shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for the production script helper test')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const start=source.indexOf('function projectField'),end=source.indexOf('function projectEditor',start);
const calls=[];
const context={console,setTimeout,clearTimeout,Object,String};
context.state={projects:[{id:'stale',character:'安养寺姬芽'}],selection:[],view:'references'};
context.api=async(path,options={})=>{calls.push({path,method:options.method||'GET'});if(path==='/api/projects')throw new Error('refresh failed');return {}};
context.closeModal=()=>{};context.resetFilters=()=>{};context.loadProjects=async()=>{};context.collectionEditor=()=>{};context.toast=()=>{};
context.modal=()=>({});context.select=()=>'';context.formSubmit=()=>{};
vm.createContext(context);vm.runInContext(source.slice(start,end)+'\nglobalThis.open=openSearchProject;',context);
(async()=>{let error;try{await context.open({character:'安养寺姬芽',work:'',costume:'',brief:'要求',gear:''})}catch(e){error=e}if(!error||!error.message.includes('refresh failed'))throw Error('refresh error not surfaced');if(calls.some(c=>c.path==='/api/projects'&&c.method==='POST'))throw Error('created despite refresh failure');console.log('SEARCH_REFRESH_FAILURE_PASS')})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run([node,'-e',script],cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    assert 'SEARCH_REFRESH_FAILURE_PASS' in result.stdout


def test_archive_helper_sends_revision_and_opens_restore_entry_without_browser():
    import shutil
    import subprocess

    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for the production script helper test')
    script = r'''
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const start=source.indexOf('async function archiveProject');
const end=source.indexOf('function projectEditor',start);
if(start<0||end<0)throw new Error('production archive helpers missing');
const calls=[],modals=[];
const context={console,window:{confirm:()=>true}};
context.state={project:{id:'old',character:'角色',revision:7},selection:[],archivedProjects:[],view:'references',dirty:false,busy:false};
context.safeDiscard=()=>true;context.api=async(path,options={})=>{calls.push({path,method:options.method,body:options.body});return {}};
context.resetFilters=()=>{};context.loadProjects=async()=>{};context.toast=()=>{};context.esc=String;
context.modal=(title,body)=>{modals.push({title,body});return {}};context.listen=()=>{};context.closeModal=()=>{};
vm.createContext(context);
vm.runInContext(source.slice(start,end)+'\nglobalThis.archive=archiveProject;globalThis.dialog=archivedProjectsDialog;',context);
(async()=>{
 await context.archive({id:'old',character:'角色',revision:7});
 const request=calls.find(c=>c.path==='/api/projects/old'&&c.method==='DELETE');
 if(!request||request.body.expected_revision!==7)throw new Error('archive did not use expected revision');
 context.state.archivedProjects=[{id:'old',character:'角色',revision:8,archived_at:'2026-10-29T00:00:00Z'}];
 context.dialog();
 if(modals.at(-1)?.title!=='已删除项目 · 可恢复'||!modals.at(-1)?.body.includes('恢复项目'))throw new Error('restore entry unavailable');
 console.log('ARCHIVE_HELPER_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run([node,'-e',script],cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    assert 'ARCHIVE_HELPER_PASS' in result.stdout


def test_studio_reduced_motion_does_not_cancel_unrelated_effects_or_change_the_photo(ui):
    page, library, project = ui
    original = page.locator('#main-image').get_attribute('src')
    page.evaluate('''() => {
        const marker = document.createElement('span');
        document.body.append(marker);
        window.unrelatedEffect = marker.animate([{opacity:1},{opacity:.9}], {duration:60000});
    }''')
    page.locator('#studio-collect').hover()
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.workspace').evaluate("n => getComputedStyle(n,'::before').animationName") == 'none'
    assert page.evaluate('window.unrelatedEffect.playState') == 'running'
    expect(page.locator('#main-image')).to_have_attribute('src', original)
    assert library.jobs() == []
    page.evaluate('window.unrelatedEffect.cancel()')


def test_saved_decisions_have_distinct_truthful_stage_cues(component_factory, client, library, project):
    for seed in range(4):
        add_reference(client,project,seed)
    page=component_factory()
    page.context.tracing.start(screenshots=True,snapshots=True)
    page.evaluate('''() => {
        window.savedCues=[];
        const original=StudioMotion.commit;
        StudioMotion.commit=(choice,ref)=>{
            original(choice,ref);
            const effect=document.querySelector('.stage-effect');
            savedCues.push({choice,id:ref.id,frames:effect.getAnimations()[0].effect.getKeyframes()});
        };
    }''')
    for choice in ['keep','inspiration','maybe','reject']:
        original_id=page.evaluate('state.activeId')
        page.locator(f'[data-decision="{choice}"]').click()
        if choice=='reject':
            page.locator('#reject-skip-btn').click()
        idle(page)
        assert page.evaluate('savedCues.at(-1).id')==original_id
        if choice=='inspiration':
            assert library.inspirations()['total']==1
        else:
            assert library.reference(original_id)['decision']==choice
    cues=page.evaluate('savedCues')
    assert [cue['choice'] for cue in cues]==['keep','inspiration','maybe','reject']
    assert len({cue['frames'][-1]['transform'] for cue in cues})==4
    folder=Path(os.environ.get('LAB_TEST_ARTIFACTS','.local/test-artifacts'))
    folder.mkdir(parents=True,exist_ok=True)
    page.context.tracing.stop(path=str(folder/'semantic-decisions.zip'))


def test_reduced_saved_cue_keeps_truth_without_moving_or_duplicating_the_photo(ui):
    page,library,project=ui
    original_id=page.evaluate('state.activeId')
    page.emulate_media(reduced_motion='reduce')
    page.evaluate('''() => {
        const original=StudioMotion.commit;
        StudioMotion.commit=(choice,ref)=>{
            original(choice,ref);
            const effect=document.querySelector('.stage-effect');
            window.savedCue={text:effect.textContent,images:effect.querySelectorAll('img').length,animations:effect.getAnimations().length};
        };
    }''')
    choose(page,'maybe')
    assert library.reference(original_id)['decision']=='maybe'
    cue=page.evaluate('savedCue')
    assert '已标记待定' in cue['text']
    assert cue['images']==0 and cue['animations']==0


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
    expect(page.locator('#studio-take-counter')).to_have_text(page.locator('#stage-counter').inner_text())
    open_navigation(page)
    expect(page.locator('#project-search')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#toggle-project-nav')).to_be_focused()
    expect(page.locator('#project-navigation')).to_be_hidden()
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
    open_navigation(page)
    page.get_by_role('button',name='新建角色项目',exact=True).click()
    page.get_by_label('角色名 *',exact=True).fill('有马加奈')
    page.get_by_label('补充要求',exact=True).fill('日常人像和自然互动')
    page.get_by_role('button',name='建立项目',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    open_navigation(page)
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
    open_navigation(page)
    page.get_by_role('button',name='采集任务',exact=True).click()
    # The primary collection editor creates split Search/Review jobs; keep the old handoff covered.
    new_project=next(p for p in library.projects() if p['character']=='有马加奈')
    job=library.create_job(new_project['id'],JobInput(kind='collection',notes='中文、日文检索；优先手势清楚的独立图片'))
    page.evaluate('id => jobHandoff(id)',job['id'])
    page.locator('#download-task').wait_for()
    assert library.job(job['id'])['status']=='blocked'
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
        open_navigation(page)
        page.locator('#global-nav [data-view="inspiration"]').click()
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
    page.evaluate('''() => {
        window.savedCues=[];
        const original=StudioMotion.commit;
        StudioMotion.commit=(choice,ref)=>{savedCues.push(choice);original(choice,ref);};
    }''')
    current=page.evaluate('state.activeId')
    ref=library.reference(current)
    response=client.patch(f'/api/references/{current}',json={'expected_revision':ref['revision'],'decision':'reject'})
    assert response.status_code==200
    choose(page,'keep')
    assert page.evaluate('savedCues') == []
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
