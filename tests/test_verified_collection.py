import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from ref_lab.verified_collection import (NamePlan,CollectionVision,accepted,query_steps,
                                         parse_agent_stream,AgentUnavailable,scope_sha)
from tools import collect_verified as worker


PROJECT={'character':'测试角色甲','costume':'','work':'Example'}


def result(path,project=PROJECT,**changes):
    values=dict(asset_sha=hashlib.sha256(path.read_bytes()).hexdigest(),context_sha=scope_sha(project),
                kind='cosplay_photo',identity='match',costume='not_required',confidence='medium',photography_usable='yes',
                kind_evidence=['连续真人摄影'],identity_evidence=['独立角色造型组合'],costume_evidence=[],
                photography_evidence=['手与脸的关系可以借鉴'],reason='实际可见依据')
    return CollectionVision(**{**values,**changes})


def test_planner_respects_source_priority_and_varies_photo_intent_without_default_costume():
    plan=NamePlan(names=['测试角色甲','Example Person','テスト甲'],
        name_records=[{'name':'测试角色甲','language':'zh','source':'synthetic trusted record'}])
    steps=query_steps(PROJECT,plan,['xiaohongshu','pinterest'])
    assert [s['source'] for s in steps[:2]]==['xiaohongshu','pinterest']
    assert steps[1]['query']=='Example Person cosplay photography'
    assert {s['language'] for s in steps[:3]}=={'zh','en','ja'}
    assert any('テスト甲' in s['query'] for s in steps)
    assert len(steps)<=8 and all('制服' not in s['query'] for s in steps)
    assert {s['alias_origin'] for s in steps}=={'agent_discovery_hypothesis'}


def test_requested_source_and_costume_are_not_silently_changed():
    p={**PROJECT,'costume':'礼服A'}
    steps=query_steps(p,NamePlan(names=['Example Person'],costume_names=['Ceremony A']),['pinterest'])
    assert steps and all(s['source']=='pinterest' for s in steps)
    assert all('礼服A' in s['query'] or 'Ceremony A' in s['query'] for s in steps)


@pytest.mark.parametrize('changes',[{'identity':'uncertain'},{'identity':'mismatch'},{'kind':'generated'},
                                    {'kind':'collage'},{'confidence':'low'},{'identity_evidence':['']},
                                    {'context_sha':'a'*64},{'photography_usable':'no'},{'photography_usable':'uncertain'}])
def test_uncertain_wrong_or_unbound_cannot_enter_main_flow(tmp_path,changes):
    path=tmp_path/'image.png';path.write_bytes(b'original')
    assert not accepted(result(path,**changes),PROJECT)


def test_costume_and_no_costume_requirement_are_separate(tmp_path):
    path=tmp_path/'image.png';path.write_bytes(b'original');p={**PROJECT,'costume':'礼服A'}
    assert accepted(result(path),PROJECT)
    assert not accepted(result(path,p),p)
    assert accepted(result(path,p,costume='match',costume_evidence=['版型细节']),p)
    assert not accepted(result(path,p,costume='mismatch',costume_evidence=['不同版型']),p)


def test_identity_reference_and_requested_costume_evidence_are_not_conflated(tmp_path):
    path=tmp_path/'target.png';path.write_bytes(b'fixture-only')
    refs=[{'asset_sha':'c'*64}]
    comparison={'reference_sha':'c'*64,'assessment':'supports','scope':'identity',
                'supporting_features':['角色发色与轮廓组合','眼部与头饰组合'],'conflicting_features':[]}
    v=result(path,reference_comparisons=[comparison])
    assert accepted(v,PROJECT,references=refs)
    requested={**PROJECT,'costume':'指定服装'}
    v=result(path,requested,costume='match',costume_evidence=['所见版型'],reference_comparisons=[comparison])
    assert not accepted(v,requested,references=refs)
    comparison={**comparison,'scope':'both'}
    v=result(path,requested,costume='match',costume_evidence=['所见版型'],reference_comparisons=[comparison])
    assert accepted(v,requested,references=refs)
    assert not accepted(result(path,reference_comparisons=[comparison],photography_evidence=[]),PROJECT,references=refs)


def test_visual_time_budget_accounts_for_actual_image_count():
    from ref_lab.verified_collection import call_time_budget
    assert call_time_budget(0,1000)==120
    assert call_time_budget(5,1000)==240
    assert call_time_budget(5,80)==65


def test_success_without_actual_image_open_or_with_denial_is_not_vision(tmp_path):
    path=tmp_path/'image.png';path.write_bytes(b'original');value=result(path)
    final={'event':'result','result':{'status':'SUCCESS','response':value.model_dump_json()}}
    with pytest.raises(AgentUnavailable):parse_agent_stream(json.dumps(final),CollectionVision,path)
    read={'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(path.resolve())}}}}
    stream=json.dumps(read)+'\n'+json.dumps(final)
    assert parse_agent_stream(stream,CollectionVision,path).asset_sha==value.asset_sha
    final['result']['denied_actions']=['view_file']
    with pytest.raises(AgentUnavailable):parse_agent_stream(json.dumps(read)+'\n'+json.dumps(final),CollectionVision,path)


class FakeBrowser:
    def __init__(self,rows,rewrite=False):self.rows=rows;self.started=False;self.closed=False;self.sources=[];self.rewrite=rewrite
    def start(self):self.started=True
    def close(self):self.closed=True
    def search(self,step):
        from urllib.parse import quote
        self.sources.append(step['source'])
        key='q' if step['source']=='pinterest' else 'keyword'
        text='這是我們針對 other 找到的內容' if self.rewrite else ''
        return {'url':'https://example.org/?'+key+'='+quote(step['query']),'search':step['query'],
                'visibleMain':text,'cards':[{'page':'https://example.org/'+step['source']}]}
    def receive(self,card,step):return self.rows


class FakeAgent:
    producer='synthetic-test-only'
    def __init__(self,states=None,unavailable=False):self.states=iter(states or []);self.unavailable=unavailable;self.calls=0;self.references=[];self.prepared=False
    def plan(self,p):
        if self.unavailable:raise AgentUnavailable('视觉Agent需要登录')
        return NamePlan(names=[p['character'],'Example Person'])
    def prepare(self,p,plan):
        self.prepared=True
        self.references=[{'asset_sha':'c'*64,'page_url':'https://example.org/synthetic-reference'}]
    def review(self,path,p):
        self.calls+=1
        assert self.prepared
        return result(path,p,identity=next(self.states,'match'),reference_comparisons=[{'reference_sha':'c'*64,'assessment':'supports','supporting_features':['Synthetic garment detail','Synthetic accessory detail'],'conflicting_features':[]}])


def row(tmp_path,name='image.png',content=b'original'):
    path=tmp_path/'images'/name;path.parent.mkdir(exist_ok=True);path.write_bytes(content)
    return {'asset_sha':hashlib.sha256(content).hexdigest(),'original_path':str(path),
            'page_url':'https://example.org/post','image_url':'https://example.org/image.png'}


def job():return {'id':'synthetic-job','project_snapshot':PROJECT,'target_count':4,'preferred_sources':['xiaohongshu','pinterest']}


def test_unavailable_agent_never_starts_search_or_exports_unreviewed(tmp_path):
    browser=FakeBrowser([row(tmp_path)])
    manifest,images=worker.collect(job(),FakeAgent(unavailable=True),browser,tmp_path)
    assert manifest['schema_version']==3 and not manifest['candidates'] and not images
    assert manifest['execution_report']['status']=='blocked' and not browser.started and browser.closed


def test_wrong_images_not_counted_and_next_source_is_attempted(tmp_path):
    a=row(tmp_path,'a.png',b'A');b=row(tmp_path,'b.png',b'B')
    browser=FakeBrowser([a]);browser.receive=lambda card,step:[a] if step['source']=='xiaohongshu' else [b]
    agent=FakeAgent(states=['mismatch','match'])
    manifest,images=worker.collect(job(),agent,browser,tmp_path)
    assert browser.sources[:2]==['xiaohongshu','pinterest']
    assert len(manifest['candidates'])==len(images)==1
    assert manifest['candidates'][0]['id']=='verified-'+b['asset_sha'][:20]
    assert manifest['candidates'][0]['preflight']['identity_prediction']=='match'
    assert all('decision' not in c and 'review' not in c for c in manifest['candidates'])
    assert browser.closed


def test_visible_rewrite_cannot_reach_image_download_or_vision(tmp_path):
    browser=FakeBrowser([row(tmp_path)],rewrite=True);agent=FakeAgent()
    manifest,images=worker.collect(job(),agent,browser,tmp_path)
    assert not manifest['candidates'] and not images and agent.calls==0
    assert all(q['stop_reason']=='REVIEW_QUERY_REWRITE' for q in manifest['execution_report']['query_log'])


def test_launcher_and_exported_task_point_to_real_verified_entry():
    from ref_lab.acquisition import agent_instructions
    root=Path(__file__).resolve().parents[1]
    assert 'tools\\collect_verified.py' in (root/'scripts/launch.ps1').read_text('utf8')
    text=agent_instructions({'id':'task','kind':'collection'})
    assert 'tools/collect_verified.py' in text and 'schema3' in text


def test_schema3_verified_package_imports_only_matches_as_pending(library,tmp_path):
    import io
    import zipfile
    from PIL import Image
    from ref_lab.models import ProjectInput,JobInput
    from ref_lab.imports import import_candidates
    project=library.create_project(ProjectInput(**PROJECT))
    task=library.create_job(project['id'],JobInput(kind='collection',target_count=2))
    rows=[]
    for i in range(2):
        image=Image.new('RGB',(600,900),(80+i*30,150,100));out=io.BytesIO();image.save(out,'PNG')
        rows.append(row(tmp_path,f'fixture-{i}.png',out.getvalue()))
    browser=FakeBrowser(rows)
    agent=FakeAgent(states=['mismatch','match'])
    manifest,images=worker.collect(task,agent,browser,tmp_path)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        for name,data in images.items():archive.writestr('images/'+name,data)
    receipt=import_candidates(library,project['id'],stream.getvalue(),task['id'])
    assert receipt['created']==1 and not receipt['errors']
    ref=library.reference(receipt['reference_ids'][0])
    assert ref['decision']=='pending' and ref['review'] is None and ref['card'] is None
    assert ref['preflight_status']=='passed' and ref['preflight_current_context'] is True


def test_login_block_on_one_source_continues_other_source(tmp_path):
    data=row(tmp_path)
    browser=FakeBrowser([data])
    def receive(card,step):
        if step['source']=='xiaohongshu':raise worker.SourceBlocked('login')
        return [data]
    browser.receive=receive
    manifest,images=worker.collect(job(),FakeAgent(),browser,tmp_path)
    assert len(manifest['candidates'])==1
    checks={x['source']:x for x in manifest['execution_report']['source_checks']}
    assert checks['xiaohongshu']['status']=='blocked'
    assert checks['pinterest']['status']=='usable'


def test_missing_primary_references_preserves_photos_but_never_exports_them(tmp_path):
    browser=FakeBrowser([row(tmp_path)]);agent=FakeAgent()
    def blocked(*args):
        agent.prepared=True
        raise AgentUnavailable('No reliable primary reference')
    agent.prepare=blocked
    manifest,images=worker.collect(job(),agent,browser,tmp_path)
    assert browser.started and browser.sources and not images and not manifest['candidates']
    received=json.loads((tmp_path/'received.json').read_text('utf8'))
    assert len(received)==1 and Path(received[0]['original_path']).read_bytes()==b'original'
    audit=json.loads((tmp_path/'visual-audit.json').read_text('utf8'))
    assert audit[0]['decision']=='NEEDS_EVIDENCE' and not audit[0]['accepted']
    assert manifest['execution_report']['status']=='blocked'


def test_visual_execution_failure_does_not_abort_other_photo_discovery(tmp_path):
    a=row(tmp_path,'a.png',b'A');b=row(tmp_path,'b.png',b'B');browser=FakeBrowser([a])
    browser.receive=lambda card,step:[a] if step['source']=='xiaohongshu' else [b]
    agent=FakeAgent()
    original=agent.review
    def fail(path,project):
        if path==Path(a['original_path']):agent.calls+=1;raise AgentUnavailable('Synthetic per-image failure')
        return original(path,project)
    agent.review=fail
    manifest,images=worker.collect(job(),agent,browser,tmp_path)
    assert len(json.loads((tmp_path/'received.json').read_text('utf8')))==2
    assert browser.sources[:2]==['xiaohongshu','pinterest'] and agent.calls==2
    audit=json.loads((tmp_path/'visual-audit.json').read_text('utf8'))
    assert len(audit)==2 and not audit[0]['accepted'] and audit[0]['decision']=='NEEDS_EVIDENCE' and audit[1]['accepted']
    assert len(images)==len(manifest['candidates'])==1 and manifest['execution_report']['status']=='blocked'


def test_reference_collision_never_becomes_a_photo_candidate(tmp_path):
    image=row(tmp_path);browser=FakeBrowser([image]);agent=FakeAgent()
    def prepare(*args):
        agent.prepared=True;agent.references=[{'asset_sha':image['asset_sha'],'page_url':'https://example.org/reference'}]
    agent.prepare=prepare
    manifest,images=worker.collect(job(),agent,browser,tmp_path)
    assert not images and not manifest['candidates'] and agent.calls==0
    assert json.loads((tmp_path/'counts.json').read_text('utf8'))['reference_collisions']==1


def test_explicit_thirty_photo_request_is_not_silently_capped_at_twelve(tmp_path):
    rows=[row(tmp_path,f'{i}.png',f'original{i}'.encode()) for i in range(36)]
    class Many(FakeBrowser):
        def search(self,step):
            snapshot=super().search(step)
            snapshot['cards']=[{'page':f'https://example.org/{step["query"]}/{i}'} for i in range(8)]
            return snapshot
        def receive(self,card,step):
            chunk=self.rows[:3];self.rows=self.rows[3:];return chunk
    agent=FakeAgent();task={**job(),'target_count':30}
    manifest,images=worker.collect(task,agent,Many(rows),tmp_path)
    assert len(images)==len(manifest['candidates'])==30
    assert agent.candidate_limit==60 and agent.calls==30
