"""Discovery evidence may save acquisition, never grant visual admission."""
import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from ref_lab.collection_history import ImageHistory
from ref_lab.verified_collection import NamePlan, query_steps
from tools import collect_verified as worker
from test_collection_autonomy import photo, row
from test_verified_collection import FakeAgent, FakeBrowser, job, PROJECT


def cover(path):
    buffer=io.BytesIO()
    with Image.open(path) as im:im.resize((270,360),Image.Resampling.LANCZOS).save(buffer,format='PNG')
    return buffer.getvalue()


def stream(monkeypatch,raw):
    requests=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_bytes(self):yield raw
    def fetch(method,url,**kwargs):requests.append(url);return Response()
    monkeypatch.setattr(worker.httpx,'stream',fetch)
    return requests


def pin():
    return {'page':'https://www.pinterest.com/pin/1234/',
            'cover_url':'https://i.pinimg.com/236x/exact-observed.png',
            'cover_width':270,'cover_height':360,'text':''}


def test_observed_cover_can_exclude_old_pin_without_polluting_original_history(tmp_path,monkeypatch):
    old=photo(tmp_path/'old',121);history=ImageHistory([old]);raw=cover(old)
    requested=stream(monkeypatch,raw);browser=worker.Browser(tmp_path)
    found=browser.check_duplicate(pin(),history)
    assert found['duplicate_of']==hashlib.sha256(old.read_bytes()).hexdigest()
    assert found['asset_role']=='discovery_preview' and found['preview_sha256']==hashlib.sha256(raw).hexdigest()
    assert Path(found['preview_path']).read_bytes()==raw
    assert requested==[pin()['cover_url']] and len(history.records)==1
    assert not (tmp_path/'images').exists()


def test_changed_cover_same_pin_is_not_blindly_skipped(tmp_path,monkeypatch):
    old=photo(tmp_path/'old',122);changed=photo(tmp_path/'new',123);history=ImageHistory([old])
    stream(monkeypatch,cover(changed))
    assert worker.Browser(tmp_path).check_duplicate(pin(),history) is None
    assert len(history.records)==1


def test_density_corrected_natural_size_is_not_the_downloaded_pixel_size(tmp_path,monkeypatch):
    old=photo(tmp_path/'old',125);buffer=io.BytesIO()
    with Image.open(old) as im:im.resize((540,720),Image.Resampling.LANCZOS).save(buffer,format='PNG')
    stream(monkeypatch,buffer.getvalue())
    found=worker.Browser(tmp_path).check_duplicate(pin(),ImageHistory([old]))
    assert found and found['duplicate_of']==row(old)['asset_sha']


@pytest.mark.parametrize('url',['https://pinimg.com.attacker.invalid/cover.png','https://user:secret@i.pinimg.com/cover.png','http://i.pinimg.com/cover.png'])
def test_cover_urls_must_be_observed_https_cdn_without_credentials(tmp_path,monkeypatch,url):
    monkeypatch.setattr(worker.httpx,'stream',lambda *a,**k:pytest.fail('Unsafe cover must not be fetched'))
    assert worker.Browser(tmp_path).check_duplicate({**pin(),'cover_url':url},ImageHistory([])) is None


def test_album_cover_never_excludes_whole_xhs_note(tmp_path,monkeypatch):
    monkeypatch.setattr(worker.httpx,'stream',lambda *a,**k:pytest.fail('No album skip'))
    card={**pin(),'page':'https://www.xiaohongshu.com/explore/'+'a'*24}
    assert worker.Browser(tmp_path).check_duplicate(card,ImageHistory([])) is None


def test_preview_fetch_or_decode_failure_still_allows_real_detail(tmp_path,monkeypatch):
    stream(monkeypatch,b'not an image')
    assert worker.Browser(tmp_path).check_duplicate(pin(),ImageHistory([])) is None


def test_metadata_prioritizes_photographic_intent_but_retains_unknown_and_art():
    cards=[{'text':'fanart illustration','page':'art'}, {'text':'其中包含以下圖片：','page':'unknown'},
           {'text':'cosplay photography','page':'photo'}]
    assert [c['page'] for c in sorted(cards,key=worker.discovery_rank)]==['photo','unknown','art']
    assert len(cards)==3
    assert worker.discovery_rank({'text':None})==1


def test_target_role_text_precedes_generic_cosplay_without_excluding_unknown():
    cards=[{'text':'Unrelated cosplay photography','page':'generic'},
           {'text':'Example Person yukata','page':'target'}, {'text':'','page':'unknown'},
           {'text':'Example Person cosplay photography','page':'target-photo'}]
    ordered=sorted(cards,key=lambda c:worker.discovery_rank(c,['Example Person']))
    assert [c['page'] for c in ordered]==['target-photo','target','generic','unknown']


def test_visible_pin_dom_records_actual_cover_and_local_text(tmp_path):
    import base64
    from playwright.sync_api import sync_playwright
    image='data:image/png;base64,'+base64.b64encode(cover(photo(tmp_path,126))).decode()
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.set_content('<input placeholder="Search" value="frozen query"><a href="https://www.pinterest.com/pin/1234/"><div data-grid-item><span>Cosplay photography</span><img alt="generic" src="'+image+'"></div></a>')
            page.wait_for_function('document.images[0].naturalWidth===270')
            snapshot=page.evaluate(worker.SEARCH_JS)
            card=snapshot['cards'][0]
            assert card['cover_url']==image and card['cover_width']==270 and card['cover_height']==360
            assert 'Cosplay photography' in card['text']
            assert snapshot['search']=='frozen query' and worker.discovery_rank(card)==0
            page.evaluate("() => {const frame=document.createElement('iframe');frame.src='about:blank#captcha';frame.style='display:none;width:300px;height:200px';document.body.append(frame)}")
            assert page.evaluate(worker.SEARCH_JS)['challenge'] is False
            page.evaluate("() => {document.querySelector('iframe').style='position:fixed;top:0;left:0;width:300px;height:200px'}")
            assert page.evaluate(worker.SEARCH_JS)['challenge'] is True
        finally:browser.close()


def test_photo_query_plan_changes_intent_instead_of_only_reversing_name():
    plan=NamePlan(names=[PROJECT['character'],'Example Person','Person Example','テスト甲'])
    steps=query_steps(PROJECT,plan,['xiaohongshu','pinterest'])
    pins=[s['query'] for s in steps if s['source']=='pinterest']
    assert len(steps)==8 and len(pins)==4
    assert any('photography' in q for q in pins) and any('photoshoot' in q for q in pins)
    assert any('テスト甲' in q or PROJECT['character'] in q for q in pins)


def test_sources_get_early_coverage_and_keep_distinct_native_photo_intents():
    steps=query_steps(PROJECT,NamePlan(names=[PROJECT['character'],'Example Person','テスト甲']),['xiaohongshu','pinterest'])
    assert [s['source'] for s in steps[:2]]==['xiaohongshu','pinterest']
    assert {s['language'] for s in steps[:3]}=={'zh','en','ja'}
    native=[s for s in steps if s['source']=='xiaohongshu']
    assert len(native)==sum(s['source']=='pinterest' for s in steps)==4
    assert any(PROJECT['character'] in s['query'] for s in native)
    assert len({s['query'] for s in native})==4
    assert steps[0]['query'].endswith('cos 摄影')


def test_native_latest_control_ignores_hidden_names_and_verifies_selection():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.set_content('''<span>筛选</span><div class="tag-container">
              <div class="tags" aria-hidden="true" style="opacity:.00001">最新</div>
              <div class="tags active">综合</div><div class="tags"><span>最新</span></div>
            </div>''')
            controls=page.evaluate(worker.XHS_SORT_JS)
            assert controls['selected'] is False
            assert page.locator(controls['trigger']).inner_text()=='筛选'
            latest=page.locator(controls['latest'])
            assert latest.get_attribute('aria-hidden') is None
            latest.evaluate("e=>{document.querySelector('.tags.active').classList.remove('active');e.classList.add('active')}")
            assert page.evaluate(worker.XHS_SORT_JS)['selected'] is True
            latest.evaluate("e=>e.style.display='none'")
            assert page.evaluate(worker.XHS_SORT_JS)['latest'] is None
        finally:browser.close()


def test_browser_search_selects_native_comprehensive_by_default_and_latest_on_request(tmp_path):
    class Native(worker.Browser):
        def __init__(self):
            super().__init__(tmp_path)
            self.session='own';self.actions=[];self.active=[];self.ready=False
        def command(self,*args,**kw):
            self.actions.append(args)
            if args[0]=='evaluate':
                assert self.ready,'SPA controls are unavailable before the first search snapshot'
                return json.dumps({'ok':True,'value':{
                    'trigger':'span.filter','comprehensive':'.real-comprehensive',
                    'latest':'.real-latest','dismiss':'input.search',
                    'active':self.active,'selected':'最新' in self.active,
                    'selected_comprehensive':'综合' in self.active}})
            if args[0]=='click':
                selector=args[args.index('--selector')+1]
                self.active=['综合'] if 'comprehensive' in selector else ['最新']
            return '{}'
        def snapshot(self):
            self.ready=True
            return {'cards':[{'page':'new'}],'sort_latest':'最新' in self.active}
    browser=Native()
    snapshot=browser.search({'source':'xiaohongshu','query':'Example cos'},sort='relevance')
    assert snapshot['sort_state']=='comprehensive'
    assert any('comprehensive' in str(a) for a in browser.actions if a[0]=='click')
    latest=Native()
    snapshot2=latest.search({'source':'xiaohongshu','query':'Example cos'},sort='latest')
    assert snapshot2['sort_state']=='latest'
    assert any('latest' in str(a) for a in latest.actions if a[0]=='click')


def test_failed_note_open_does_not_navigate_back_out_of_valid_search(tmp_path):
    class Missed(worker.Browser):
        def __init__(self):super().__init__(tmp_path);self.session='own';self.actions=[]
        def command(self,*args,**kw):self.actions.append(args);return '{}'
        def snapshot(self):return {'url':'https://www.xiaohongshu.com/search_result?keyword=Example'}
    browser=Missed()
    with pytest.raises(ValueError):browser.receive({'page':'https://www.xiaohongshu.com/explore/'+'a'*24},{'source':'xiaohongshu'})
    assert [a[0] for a in browser.actions]==['click']


def test_high_confidence_negative_still_supplements_under_original_quality_contract(tmp_path):
    from ref_lab.verified_collection import AntigravityCollectionAgent
    from test_verified_collection import result
    path=photo(tmp_path,129);agent=AntigravityCollectionAgent(tmp_path)
    agent.research=object()
    agent.references=[{'asset_sha':'a'*64,'page_url':'https://example.org/official-a'},
                      {'asset_sha':'b'*64,'page_url':'https://example.org/official-b'}]
    comparisons=[{'reference_sha':r['asset_sha'],'assessment':'contradicts','scope':'identity',
                  'supporting_features':[],'conflicting_features':['Different eyes','Different hair']}
                 for r in agent.references]
    value=result(path,identity='mismatch',confidence='high',reference_comparisons=comparisons)
    assert agent.needs_supplement(value,PROJECT)
    assert agent.needs_supplement(value.model_copy(update={'identity':'uncertain'}),PROJECT)
    assert agent.needs_supplement(value.model_copy(update={'confidence':'medium'}),PROJECT)
    assert agent.needs_supplement(value.model_copy(update={'reference_comparisons':value.reference_comparisons[:1]}),PROJECT)
    agent.references[1]['page_url']=agent.references[0]['page_url']
    assert agent.needs_supplement(value,PROJECT)


def test_actual_source_gates_have_an_explicit_blocked_stop_reason(tmp_path):
    class Gated(FakeBrowser):
        def search(self,step):return {**super().search(step),'challenge':True}
    agent=FakeAgent();manifest,_=worker.collect(job(),agent,Gated([]),tmp_path)
    counts=json.loads((tmp_path/'counts.json').read_text('utf8'))
    assert counts['stop_reason']=='sources_blocked' and counts['accepted']==0
    assert manifest['execution_report']['status']=='blocked' and agent.calls==0


@pytest.mark.skipif(__import__('os').name!='nt',reason='Windows command-line transport bound')
def test_long_prompt_uses_exact_private_stdin_message_and_keeps_image_parser(tmp_path,monkeypatch):
    from ref_lab.verified_collection import AntigravityCollectionAgent
    from test_collection_resume import fake_processes,terminal
    calls=fake_processes(monkeypatch,[(0,terminal('SUCCESS',{'names':['Synthetic']}),'')])
    prompt='完整来源证据 '+('原始正文 '*8000)+' END'
    value=AntigravityCollectionAgent(tmp_path,model='synthetic').run(prompt,NamePlan)
    assert value.names==['Synthetic'] and len(calls)==1
    command=calls[0]
    assert '--stdin-file' in command and '-p=' in command and '--input-format' in command
    path=Path(command[command.index('--stdin-file')+1])
    message=json.loads(path.read_text('utf8'))
    assert message=={'event':'user','message':{'role':'user','content':prompt}}
    assert command[command.index('--input-format')+1]=='stream-json'
    assert len(__import__('subprocess').list2cmdline(command).encode('utf-16-le'))//2<32767


@pytest.mark.skipif(__import__('os').name!='nt',reason='Windows Job Object supervisor')
def test_supervisor_passes_owned_stdin_and_refuses_external_input(tmp_path):
    import subprocess,sys
    from ref_lab import windows_adapter_runner
    raw=('完整中文输入\n'*5000).encode('utf8')
    path=tmp_path/'stdin.jsonl';path.write_bytes(raw)
    code='import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
    args=[sys._base_executable,str(Path(windows_adapter_runner.__file__).resolve()),'--stdin-file',str(path),sys._base_executable,'-c',code]
    result=subprocess.run(args,cwd=tmp_path,capture_output=True,timeout=15)
    assert result.returncode==0 and result.stdout.decode().strip()==hashlib.sha256(raw).hexdigest()
    inside=tmp_path/'different-cwd';inside.mkdir()
    denied=subprocess.run(args,cwd=inside,capture_output=True,timeout=15)
    assert denied.returncode==126 and not denied.stdout


def test_daily_quota_endpoint_name_does_not_prove_exhausted_credits():
    from ref_lab.verified_collection import diagnose_cli
    from test_collection_resume import terminal
    log='applyAuthResult: ready\nCache(retrieveUserQuotaSummary): Post "https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary": context canceled'
    assert diagnose_cli(terminal('ERROR'),log=log)['category']!='quota_exhausted'
    assert diagnose_cli(terminal('ERROR'),stderr='daily quota exhausted')['category']=='quota_exhausted'
    error=json.dumps({'event':'result','result':{'status':'ERROR','error':'Error: empty prompt'}})
    assert diagnose_cli(error,log='authentication required')['category']=='cli_input_error'


@pytest.mark.parametrize('all_old_first_window',[False,True])
def test_cover_duplicates_do_not_consume_detail_sample_or_starve_new_candidates(tmp_path,monkeypatch,all_old_first_window):
    old=photo(tmp_path/'images',130);new=photo(tmp_path/'images',131)
    class Browser(FakeBrowser):
        opened=[];more_calls=0
        def search(self,step):
            snapshot=super().search(step)
            snapshot['cards']=[{'page':'https://example.org/old'}]+([] if all_old_first_window else [{'page':'https://example.org/new'}])
            return snapshot
        def more(self,step):
            self.more_calls+=1;snapshot=super().search(step);snapshot['cards']=[{'page':'https://example.org/new'}];return snapshot
        def check_duplicate(self,card,history):
            return {'duplicate_of':row(old)['asset_sha'],'asset_role':'discovery_preview','preview_sha256':'f'*64} if card['page'].endswith('old') else None
        def receive(self,card,step):self.opened.append(card['page']);return [row(new)]
    monkeypatch.setattr(worker,'SAMPLE_PER_QUERY',1)
    browser=Browser([]);agent=FakeAgent()
    manifest,_=worker.collect({**job(),'target_count':1},agent,browser,tmp_path,history=ImageHistory([old]))
    assert browser.opened==['https://example.org/new'] and agent.calls==1
    assert len(manifest['candidates'])==1 and browser.more_calls==int(all_old_first_window)
    counts=json.loads((tmp_path/'counts.json').read_text('utf8'))
    assert counts['detail_pages']==1 and counts['preview_duplicates']==1
    assert counts['stop_reason']=='soft_target_reached'
