"""Program regressions; synthetic pixels never prove photographic accuracy."""
import json
from pathlib import Path
import pytest
from ref_lab import collage
from ref_lab.collection_counts import compute
from ref_lab.collection_history import ImageHistory
from ref_lab.verified_collection import deterministic_plan
from tests.test_collage_split import _collage, _textured, _write_original
from tools.collect_verified import Browser, restore_history_index
from ref_lab.search_relevance import associate_detail, exploration_count
from ref_lab.photo_types import verified_photo
from ref_lab.models import JobInput


def test_named_unknown_type_is_only_a_candidate(tmp_path):
    row = _write_original(tmp_path, _textured((800, 600), 1, (70, 80, 90)))
    row['relevance'] = {'tier': 'target_named'}
    record = collage.process_original(tmp_path, row)
    counts = compute(tmp_path, [row], {row['asset_sha']: record})
    assert counts['found'] == 1
    assert counts['usable_named'] == counts['usable_independent'] == 0


def test_search_final_receipt_keeps_canonical_counts_and_closes_once(tmp_path):
    from ref_lab.collection_checkpoint import load_checkpoint
    from tests.photo_type_fixture import synthetic_type
    from tests.test_search_continue_recovery import Agent
    from tools import collect_verified as worker
    row=_write_original(tmp_path,_textured((800,600),11,(100,90,130)))
    row['relevance']={'tier':'target_named'}
    synthetic_type(tmp_path,row);types=json.loads((tmp_path/'photo-types.json').read_text())
    types['calls']=[{'asset_sha':row['asset_sha'],'tokens':7}]
    (tmp_path/'photo-types.json').write_text(json.dumps(types),'utf8')
    collage.process_original(tmp_path,row)
    job={'id':'final-receipt','project_snapshot':{'character':'角色甲','work':'','costume':'','brief':''},
         'target_count':1,'preferred_sources':['pinterest'],'notes':''}
    state=load_checkpoint(tmp_path,job,'synthetic');state['received']=[row]
    (tmp_path/'collector-state.json').write_text(json.dumps(state),'utf8')
    (tmp_path/'received.json').write_text(json.dumps([row]),'utf8')
    closed=[]
    class NoSearch:
        def start(self):pass
        def close(self):closed.append(True)
        def search(self,*args):raise AssertionError('Already reached target')
    summary,_=worker.collect(job,Agent(),NoSearch(),tmp_path,search_only=True)
    assert len(closed)==1
    counts=json.loads((tmp_path/'counts.json').read_text())
    assert counts['usable_named']==summary['counts']['usable_named']==1
    assert counts['goal_shas']==[row['asset_sha']]
    assert counts['model_calls']==1 and counts['tokens']==7
    assert json.loads((tmp_path/'collector-state.json').read_text())['phase']=='finished'


def test_name_association_survives_text_type_hint_but_still_requires_photo_read(tmp_path):
    from ref_lab.search_relevance import classify_card
    from tests.photo_type_fixture import synthetic_type
    row=_write_original(tmp_path,_textured((800,600),7,(80,90,110)))
    row['relevance']=classify_card({'text':'角色甲 cos 棚拍，公式人台照'},names=['角色甲'])
    assert row['relevance']['tier']=='non_photo' and row['relevance']['name_hits']==['角色甲']
    record=collage.process_original(tmp_path,row)
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==0
    synthetic_type(tmp_path,row)
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==1


@pytest.mark.parametrize('uncertain',[False,True])
def test_current_photo_cover_repeat_adds_name_without_new_download(tmp_path,uncertain):
    from ref_lab.collection_checkpoint import load_checkpoint
    from tests.photo_type_fixture import synthetic_type
    from tests.test_search_continue_recovery import Agent
    from tools import collect_verified as worker
    row=_write_original(tmp_path,_textured((800,600),9,(90,110,140)))
    row['relevance']={'tier':'unconfirmed'}
    before=Path(row['original_path']).read_bytes();synthetic_type(tmp_path,row)
    collage.process_original(tmp_path,row)
    job={'id':'cover-name','project_snapshot':{'character':'角色甲','work':'作品甲','costume':'','brief':''},
         'target_count':1,'preferred_sources':['pinterest'],'notes':''}
    state=load_checkpoint(tmp_path,job,'synthetic');state['received']=[row]
    (tmp_path/'collector-state.json').write_text(json.dumps(state),'utf8')
    (tmp_path/'received.json').write_text(json.dumps([row]),'utf8')
    class RepeatedBrowser:
        def start(self):pass
        def close(self):pass
        def search(self,step):
            from urllib.parse import quote
            return {'url':'https://www.pinterest.com/search/pins/?q='+quote(step['query']),
                'search':step['query'],'cards':[{'page':'https://www.pinterest.com/pin/999/','text':'角色甲 cosplay'}]}
        def check_duplicate(self,*args):return {'duplicate_of':row['asset_sha'],'reason':'visible_cover_matches_history',
                                                **({'state':'needs_review'} if uncertain else {})}
        def receive(self,*args):raise AssertionError('Current repeat must reuse original bytes')
    history=ImageHistory([])
    summary,_=worker.collect(job,Agent(),RepeatedBrowser(),tmp_path,search_only=True,history=history)
    assert summary['counts']['found']==1 and summary['counts']['usable_named']==(0 if uncertain else 1)
    assert Path(row['original_path']).read_bytes()==before
    saved=json.loads((tmp_path/'received.json').read_text())[0]
    if uncertain:
        assert saved['relevance']['tier']=='unconfirmed'
    else:
        assert saved['discovery_evidence_history'][0]['tier']=='unconfirmed'
        assert saved['discovery_evidence_history'][-1]['image_match']['duplicate_of']==row['asset_sha']


def test_successful_new_search_clears_previous_return_failure(tmp_path):
    browser = Browser(tmp_path)
    browser.return_failed = True
    browser.session = 'synthetic'
    browser.command = lambda *a, **k: '{}'
    browser.snapshot = lambda: {'cards': [{'page': 'https://www.pinterest.com/pin/1/'}]}
    browser.search({'source': 'pinterest', 'query': 'You Watanabe cosplay'})
    assert browser.return_failed is False


def test_history_back_is_never_repeated_after_unknown_effect(tmp_path, monkeypatch):
    from tools import collect_verified as worker
    calls=[]
    class Failed:
        returncode=1
        stdout=''
        stderr='error: the browser did not become ready for native input'
    def run(*args, **kwargs):
        calls.append(args)
        return Failed()
    monkeypatch.setattr(worker.subprocess,'run',run)
    monkeypatch.setattr(worker.time,'sleep',lambda *a:None)
    browser=Browser(tmp_path);browser.bsk='synthetic';browser.session='synthetic'
    with pytest.raises(ValueError):browser.command('navigate-back','--session','synthetic')
    assert len(calls)==1
    assert json.loads((tmp_path/'browser-errors.json').read_text())[0]['code']=='native_input_not_ready'


def test_success_exit_without_search_page_stops_old_card_clicks(tmp_path, monkeypatch):
    from tools import collect_verified as worker
    page='https://www.xiaohongshu.com/explore/'+'a'*24
    browser=Browser(tmp_path);browser.session='synthetic';browser.bsk='synthetic'
    browser.command=lambda *a,**kw:'{}'
    browser._probe_detail=lambda:{'url':page}
    browser.snapshot=lambda:{'url':page,'cards':[]}
    monkeypatch.setattr(worker,'capture_note',lambda *a,**kw:[])
    browser.receive({'page':page},{'source':'xiaohongshu'})
    assert browser.return_failed is True


def test_stopping_attempt_keeps_elapsed_and_can_replenish(library, project, client, monkeypatch, tmp_path):
    from ref_lab import service, collection_queue
    rows=[_write_original(tmp_path,_textured((800,600),seed,(80,100,130)),name=f'{seed}.png') for seed in (81,82)]
    (tmp_path/'received.json').write_text(json.dumps(rows),'utf8')
    monkeypatch.setattr(collection_queue,'run_directory',lambda _:tmp_path)
    job=library.create_job(project['id'],JobInput(kind='collection',collection_mode='search',target_count=15))
    started=service.time.time()
    monkeypatch.setattr(service.time,'time',lambda:started)
    running=library.start_collection_attempt(job['id'],job['revision'],'synthetic-attempt',timeout=900)
    library.update_search_stage(job['id'],'synthetic-attempt','running',{'counts':{'found':2}},'synthetic pending')
    monkeypatch.setattr(service.time,'time',lambda:started+123.)
    stopped=library.cancel_search_stage(job['id'])
    assert stopped['search_elapsed_seconds']==pytest.approx(job.get('search_elapsed_seconds',0)+123)
    assert client.get(f"/api/jobs/{job['id']}").json()['can_start_review'] is True
    resumed=library.replenish_search(job['id'],900)
    assert resumed['target_count']==15 and resumed['search_elapsed_seconds']==stopped['search_elapsed_seconds']
    assert resumed['search_timeout_seconds']==1800


def test_terminal_search_time_includes_parent_preparation(library, project, monkeypatch):
    from ref_lab import service
    job=library.create_job(project['id'],JobInput(kind='collection',collection_mode='search',target_count=15))
    started=service.time.time();monkeypatch.setattr(service.time,'time',lambda:started)
    library.start_collection_attempt(job['id'],job['revision'],'timing-attempt',timeout=900)
    monkeypatch.setattr(service.time,'time',lambda:started+123.)
    finished=library.update_search_stage(job['id'],'timing-attempt','partial',
        {'counts':{'found':1},'elapsed_seconds':1},'synthetic child timer excludes setup')
    assert finished['search_elapsed_seconds']==pytest.approx(job.get('search_elapsed_seconds',0)+123)
    assert finished['collection_elapsed_seconds']==finished['search_elapsed_seconds']


def test_interrupted_checkpoint_recovers_elapsed_from_frozen_job(tmp_path):
    import time
    from tools import collect_verified as worker
    from tests.test_search_continue_recovery import Agent,Browser,_job
    job={**_job(extra=0,target=1),'search_elapsed_seconds':120.,
         'search_attempt_started_at':time.time()-20}
    summary,_=worker.collect(job,Agent(),Browser(tmp_path),tmp_path,search_only=True)
    assert summary['cumulative_elapsed_seconds']>=140


def test_frozen_goal_history_seeds_sha_after_current_index_is_ready(tmp_path, monkeypatch):
    import hashlib,threading
    from tools import collect_verified as worker
    root=tmp_path/'root';folder=root/'.local/collection-runs/job/current';folder.mkdir(parents=True)
    baseline_dir=root/'.local/goals/goal';baseline_dir.mkdir(parents=True)
    fp={'asset_sha':'a'*64,'path':str(root/'old.jpg'),'ratio':1.,'dhash':'0'*16,'sample':'0'*384,'pixels':'0'*(128*128*3*2)}
    from ref_lab.collection_history import DEDUP_SCOPE_VERSION, FINGERPRINT_ALGORITHM_VERSION
    baseline={'goal_id':'goal','fingerprint_algorithm_version':FINGERPRINT_ALGORITHM_VERSION,
              'project_id':'proj-a','dedup_scope_version':DEDUP_SCOPE_VERSION,
              'items':[{'path':str(root/f'copy-{i}.jpg'),'sha':'a'*64,'fingerprint':fp} for i in range(3)]}
    raw=json.dumps(baseline).encode();(baseline_dir/'baseline.json').write_bytes(raw)
    (folder/'baseline.json').write_bytes(raw)
    (folder/'goal.json').write_text(json.dumps({'goal_id':'goal','project_id':'proj-a',
                                                'dedup_scope_version':DEDUP_SCOPE_VERSION,
                                                'baseline_sha':hashlib.sha256(raw).hexdigest(),'baseline_shas':['a'*64]}))
    monkeypatch.setattr(worker,'ROOT',root)
    monkeypatch.setattr(worker.subprocess,'check_output',lambda *a,**k:'.git')
    class _EmptyScope:
        paths=[];library_keepers={};project_run_dirs=[];unattributed_runs=[];report={}
    monkeypatch.setattr(worker,'_validated_history_scope',lambda *a,**k:_EmptyScope())
    class History:
        def __init__(self,paths,**kwargs):
            assert not paths,'Frozen same-SHA copies must not be statted again before every attempt'
            assert kwargs['lazy'] is False
            self.ready=True;self.errors=[]
            self._lock=threading.RLock();self.known_shas=set();self.records={}
    monkeypatch.setattr(worker,'ImageHistory',History)
    history=worker._history_for_search(folder,'proj-a')
    assert history.known_shas=={'a'*64} and history.records=={'a'*64:fp}


def test_trusted_names_preserve_original_and_languages():
    plan = deterministic_plan({'character': '渡边曜', 'work': 'Love Live! Sunshine!!'})
    records = {r['name']: r for r in plan.name_records}
    assert {'渡边曜', '渡辺曜', '渡辺 曜', 'You Watanabe', 'Watanabe You'} <= records.keys()
    assert records['渡边曜']['language'] == 'zh'
    assert records['渡辺曜']['language'] == 'ja'


def test_refined_photography_intents_use_new_queries_without_new_names():
    from ref_lab.verified_collection import query_steps
    project={'character':'渡边曜','work':'Love Live! Sunshine!!'}
    plan=deterministic_plan(project)
    old=query_steps(project,plan,['xiaohongshu','pinterest'])
    new=query_steps(project,plan,['xiaohongshu','pinterest'],intent_offset=2)
    assert len(new)==len(old)==8
    assert not ({(s['source'],s['query']) for s in old}&{(s['source'],s['query']) for s in new})
    assert {s['used_name'] for s in new}<={r['name'] for r in plan.name_records}
    assert {s['language'] for s in new}=={'zh','ja','en'}


def test_continue_consumes_content_feedback_and_preserves_plan_history(tmp_path):
    from ref_lab.collection_checkpoint import load_checkpoint
    from ref_lab.verified_collection import query_steps
    from tools import collect_verified as worker
    from tests.test_search_continue_recovery import Agent
    project={'character':'渡边曜','work':'Love Live! Sunshine!!','costume':'','brief':''}
    job={'id':'feedback-resume','project_snapshot':project,'target_count':15,'notes':'',
         'preferred_sources':['xiaohongshu','pinterest'],'search_resume_generation':2}
    plan=deterministic_plan(project);old=query_steps(project,plan,job['preferred_sources'])
    state=load_checkpoint(tmp_path,job,'synthetic')
    state.update(plan=plan.model_dump(),steps=old,search_resume_generation=1,
        searches={'0':{**old[0],'done':False,'feedback':{'reason':'history_duplicate_high'}}},
        queries=[{'source':old[0]['source'],'query':old[0]['query'],'kept':0,'stop_reason':'old_duplicate_high'}])
    (tmp_path/'collector-state.json').write_text(json.dumps(state),'utf8')
    executed=[]
    class EmptyBrowser:
        def start(self):pass
        def close(self):pass
        def search(self,step):
            executed.append(step)
            return {'url':'https://example.org/search','search':step['query'],'cards':[]}
    summary,_=worker.collect(job,Agent(),EmptyBrowser(),tmp_path,search_only=True)
    saved=json.loads((tmp_path/'collector-state.json').read_text())
    assert executed and executed[0]['intent']!=old[0]['intent']
    assert saved['query_plan_history'][0]['steps']==old
    assert saved['search_attempt_history'][0]['queries'][0]['stop_reason']=='old_duplicate_high'
    assert summary['target']==15 and not summary['target_reached']


def test_legacy_default_chinese_bucket_is_not_trusted_language():
    legacy={'aliases':{'zh':['渡辺曜'],'ja':[],'en':[]},'reference_provenance':'用户项目输入',
            'uncertainties':['暂无官方人设对比数据，需人工核对']}
    plan=deterministic_plan({'character':'渡辺曜'},identity_context=legacy)
    records={r['name']:r for r in plan.name_records}
    assert records['渡辺曜']['language']=='ja'
    legacy['aliases']['zh']=['田中未知']
    unknown=deterministic_plan({'character':'田中未知'},identity_context=legacy)
    assert unknown.name_records[0]['language']=='unknown'


def test_resume_upgrades_legacy_language_plan_and_preserves_old_queries(tmp_path):
    from ref_lab.collection_checkpoint import load_checkpoint
    from tools import collect_verified as worker
    from tests.test_search_continue_recovery import Agent
    project={'character':'渡辺曜','work':'Love Live! Sunshine!!','costume':'','brief':''}
    legacy={'aliases':{'zh':['渡辺曜'],'ja':[],'en':[]},'reference_provenance':'用户项目输入',
            'uncertainties':['暂无官方人设对比数据，需人工核对']}
    job={'id':'language-resume','project_snapshot':project,'identity_context':legacy,
         'target_count':15,'preferred_sources':['xiaohongshu'],'notes':''}
    state=load_checkpoint(tmp_path,job,'synthetic')
    old_query='渡辺曜 Love Live! Sunshine!! cos 摄影'
    state.update(plan={'names':['渡辺曜'],'name_records':[{'name':'渡辺曜','language':'zh','source':'project_character'}]},
        steps=[{'source':'xiaohongshu','query':old_query,'language':'zh'}],
        searches={'0':{'source':'xiaohongshu','query':old_query,'done':True}},
        queries=[{'source':'xiaohongshu','query':old_query,'kept':0,'stop_reason':'old_failure'}])
    (tmp_path/'collector-state.json').write_text(json.dumps(state),'utf8')
    executed=[]
    class EmptyBrowser:
        def start(self):pass
        def close(self):pass
        def search(self,step):
            executed.append(step)
            return {'url':'https://www.xiaohongshu.com/search_result','search':step['query'],'cards':[]}
    worker.collect(job,Agent(),EmptyBrowser(),tmp_path,search_only=True)
    saved=json.loads((tmp_path/'collector-state.json').read_text())
    assert executed[0]['used_name']=='渡边曜' and executed[0]['language']=='zh'
    assert saved['name_plan_history'][0]['plan']['name_records'][0]['language']=='zh'
    assert any(q['query']==old_query for q in saved['queries'])


def test_resume_keeps_shared_tile_business_identity(tmp_path):
    a = _write_original(tmp_path, _collage(2, 1, tile=(800, 600),
        bases=[(28, 30, 34), (222, 220, 214)]), name='a.png')
    a['relevance'] = {'tier': 'unconfirmed'}
    first = collage.process_original(tmp_path, a)
    history = ImageHistory([])
    try:
        restore_history_index(history, tmp_path, [a])
        b = _write_original(tmp_path, _collage(2, 1, tile=(800, 600),
            bases=[(28, 30, 34), (52, 150, 196)]), name='b.png')
        b['relevance'] = {'tier': 'target_named'}
        history.consider(Path(b['original_path']))
        second = collage.process_original(tmp_path, b, history=history,
            known_shas={a['asset_sha'], b['asset_sha']})
        assert second['children'][0]['status'] == collage.DUPLICATE_RUN
        assert first['children'][0]['child_sha'] == second['children'][0]['child_sha']
        counts=compute(tmp_path,[a,b],collage.DerivedStore(tmp_path).items())
        assert counts['independent_candidates']==3
        assert counts['named_candidates']==2
    finally:
        history.close()


def test_author_detail_promotes_but_query_and_comments_do_not():
    card={'text':'ATP曜！','page':'https://www.xiaohongshu.com/explore/1'}
    row={'author_detail':{'title':'ATP曜！','description':'#渡边曜 cos正片'},
         'source_text':'comments and page context'}
    result=associate_detail(card,row,names=['渡边曜'])
    assert result['tier']=='target_named'
    assert result['card']['relevance']['tier']=='unconfirmed'
    assert result['detail']['evidence']['description']=='#渡边曜 cos正片'
    assert associate_detail(card,{'source_text':'评论 渡边曜','search_query':'渡边曜'},names=['渡边曜'])['tier']=='unconfirmed'


def test_three_images_from_one_post_use_one_exploration_slot():
    rows=[{'asset_sha':str(n)*64,'page_url':'https://www.xiaohongshu.com/explore/1',
           'relevance':{'tier':'unconfirmed'}} for n in range(3)]
    assert exploration_count(rows)==1
    for row in rows:row['relevance']={'tier':'target_named'}
    assert exploration_count(rows)==0


def test_replenish_keeps_target_and_cumulative_history(library, project):
    job=library.create_job(project['id'],JobInput(kind='collection',collection_mode='search',target_count=15))
    running=library.start_collection_attempt(job['id'],job['revision'],'synthetic-attempt',timeout=900)
    library.update_search_stage(job['id'],'synthetic-attempt','partial',
        {'status':'partial','counts':{'found':3},'elapsed_seconds':100},'synthetic partial')
    resumed=library.replenish_search(job['id'],900)
    assert resumed['target_count']==15
    assert resumed.get('search_extra_target',0)==0
    assert resumed['search_elapsed_seconds']==100
    assert resumed['search_timeout_seconds']==1800
    assert resumed['search_resume_generation']==1


def test_goal_count_requires_intact_type_receipt_and_new_parent(tmp_path):
    from tests.photo_type_fixture import synthetic_type
    row=_write_original(tmp_path,_textured((800,600),3,(90,110,140)))
    row['acquired_at']=10
    record=collage.process_original(tmp_path,row)
    synthetic_type(tmp_path,row)
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==1
    (tmp_path/'goal.json').write_text(json.dumps({'started_at':0,'baseline_shas':[row['asset_sha']]}),'utf8')
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==0
    (tmp_path/'goal.json').write_text(json.dumps({'started_at':0,'baseline_shas':[]}),'utf8')
    stream=next((tmp_path/'type-evidence').glob('*.jsonl'));stream.write_text('changed','utf8')
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==0


@pytest.mark.parametrize('text_type_hint',[False,True])
def test_goal_result_page_uses_the_same_set(client, library, project, tmp_path, monkeypatch, text_type_hint):
    from ref_lab import collection_queue
    from tests.photo_type_fixture import synthetic_type
    row=_write_original(tmp_path,_textured((800,600),5,(100,120,140)))
    row['acquired_at']=10
    if text_type_hint:
        row['relevance']={'tier':'non_photo','name_hits':['角色甲']}
    collage.process_original(tmp_path,row)
    synthetic_type(tmp_path,row)
    (tmp_path/'received.json').write_text(json.dumps([row]),'utf8')
    monkeypatch.setattr(collection_queue,'run_directory',lambda _:tmp_path)
    job=library.create_job(project['id'],JobInput(kind='collection',collection_mode='search',target_count=15))
    original=library.job
    monkeypatch.setattr(library,'job',lambda ident:{**original(ident),'goal_id':'synthetic-page-test'})
    response=client.get(f'/api/jobs/{job["id"]}/goal-results')
    assert response.status_code==200
    assert '1/15' in response.text and row['asset_sha'] in response.text
    item=collection_queue.snapshot(job['id'])['items'][0]
    assert item['name_associated'] and item['goal_name_evidence']
    shown=client.get(f'/api/jobs/{job["id"]}').json()
    assert shown['search_counts']['usable_named']==1


@pytest.mark.parametrize('sha',[
    '65eab0eaf37270c07cd83964b763a6a1edb7006b9c1b18f4e386bb44c853fca0',
    '31ab617b368f4fbabba7d5dfc2e5cbd2939c76591d89c736a22472ab208c89a2'])
def test_audited_anime_kind_never_enters_photo_set(sha):
    # Kind filtering contract only. Actual originals are read in private live evidence.
    item={'asset_sha':sha,'status':'succeeded','producer':'synthetic-contract',
          'result_status':'SUCCESS','read_evidence':{'tool':'view_file','state':'DONE',
          'asset_sha':sha,'preview_sha':'0'*64},
          'result':{'asset_sha':sha,'kind':'illustration','evidence':'synthetic routing fixture'}}
    assert not verified_photo(item,sha)
    item['result']['kind']='portrait_photo'
    assert verified_photo(item,sha)
    item['read_evidence']['state']='FAILED'
    assert not verified_photo(item,sha)


def test_reviewed_photo_variant_counts_once_without_changing_originals(tmp_path):
    from tests.photo_type_fixture import synthetic_type
    rows=[_write_original(tmp_path,_textured((800,600),seed,(70,90,120)),name=f"{seed}.png") for seed in (31,32)]
    records={}
    for row in rows:
        row['relevance']={'tier':'target_named'}
        synthetic_type(tmp_path,row)
        records[row['asset_sha']]=collage.process_original(tmp_path,row)
    before=[Path(row['original_path']).read_bytes() for row in rows]
    assert compute(tmp_path,rows,records)['usable_named']==2
    audit={'items':{rows[1]['asset_sha']:{'asset_sha':rows[1]['asset_sha'],'status':'duplicate',
        'duplicate_of':rows[0]['asset_sha'],'producer':'synthetic-review',
        'evidence':'Program fixture: reviewed crop of the same photo.'}}}
    (tmp_path/'photo-audit.json').write_text(json.dumps(audit),'utf8')
    result=compute(tmp_path,rows,records)
    assert result['usable_named']==result['usable_independent']==1
    assert result['photo_duplicates']==1 and result['goal_shas']==[rows[0]['asset_sha']]
    assert [Path(row['original_path']).read_bytes() for row in rows]==before
