"""Shared controller recovery boundaries, without network/model execution."""
import json

import pytest

from tools import collect_verified as worker
from test_verified_collection import FakeAgent, FakeBrowser, job, row


def test_authentication_recovery_reenters_same_job(tmp_path):
    task={**job(),'target_count':1}
    blocked,_=worker.collect(task,FakeAgent(unavailable=True),FakeBrowser([]),tmp_path)
    state=json.loads((tmp_path/'collector-state.json').read_text('utf8'))
    agent=FakeAgent()
    resumed,_=worker.collect(task,agent,FakeBrowser([row(tmp_path)]),tmp_path)
    assert blocked['execution_report']['status']=='blocked'
    assert resumed['execution_report']['status']=='completed' and agent.calls==1
    assert resumed['batch_id']==state['batch_id']


def test_breadth_continuation_returns_to_its_query_before_scrolling(tmp_path):
    class Browser(FakeBrowser):
        def search(self,step):
            self.current=step['query']
            return super().search(step)
        def more(self,step):
            assert self.current==step['query'],'Scrolled another query'
            return super().search(step)
    first=row(tmp_path)
    browser=Browser([first])
    manifest,_=worker.collect(job(),FakeAgent(),browser,tmp_path)
    assert any(q['stop_reason']!='bounded_breadth_next_query' for q in manifest['execution_report']['query_log'])
    # A failed assertion in the browser must not be swallowed as an exhausted plan.


def test_resume_navigation_honors_current_login_gate(tmp_path):
    task={**job(),'target_count':1}
    worker.collect(task,FakeAgent(unavailable=True),FakeBrowser([]),tmp_path)
    state=json.loads((tmp_path/'collector-state.json').read_text('utf8'))
    state.pop('final_manifest',None)
    state['steps']=[{'source':'pinterest','query':'Test cosplay','language':'en'}]
    state['searches']={'0':{'source':'pinterest','query':'Test cosplay','language':'en','window':0,'observed':True,
        'usable':True,'done':False,'snapshot':{'url':'https://www.pinterest.com/search/pins/?q=Test%20cosplay',
            'search':'Test cosplay','visibleMain':'Test cosplay','cards':[{'page':'https://example.org/post'}]}}}
    worker.save(tmp_path/'collector-state.json',state)
    class Gated(FakeBrowser):
        def search(self,step):return {**super().search(step),'login_required':True}
        def receive(self,*args):pytest.fail('Old snapshot bypassed the current login gate')
    agent=FakeAgent()
    manifest,_=worker.collect(task,agent,Gated([]),tmp_path)
    assert not manifest['candidates'] and not agent.calls


def test_legacy_resume_preserves_missing_language_coverage(tmp_path,monkeypatch):
    from test_collection_resume import resume_fixture
    source,state,task,_,_,_,_=resume_fixture(tmp_path,monkeypatch)
    manifest=json.loads((source/'manifest.json').read_text('utf8'))
    manifest['execution_report'].update(source_checks=[{'source':s,'status':'usable','detail':'visible'} for s in ['xiaohongshu','pinterest']],
        query_log=[{'source':'xiaohongshu','query':'测试摄影','kept':1,'stop_reason':'done'},
                   {'source':'pinterest','query':'Example Person cosplay','kept':1,'stop_reason':'done'}],
        gaps=['检索语言覆盖未满足：ja'])
    worker.save(source/'manifest.json',manifest)
    output,_=worker.resume_collection(task,source,state)
    assert output['execution_report']['status']=='blocked'
    assert '检索语言覆盖未满足：ja' in output['execution_report']['gaps']


@pytest.mark.parametrize('tamper',[False,True])
def test_legacy_without_new_binding_requires_original_bound_receipt(tmp_path,monkeypatch,tamper):
    from pathlib import Path
    from ref_lab import verified_collection as vision
    from test_collection_resume import resume_fixture, fake_processes, terminal
    source,state,task,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    info=json.loads((source/'run-info.json').read_text('utf8'));info.pop('binding')
    worker.save(source/'run-info.json',info)
    refs=json.loads((source/'reference-research/report.json').read_text('utf8'))['references']
    reads=[{'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(Path(p).resolve())}}}}
           for p in [rows[0]['original_path'],refs[0]['path']]]
    fake_processes(monkeypatch,[(0,'\n'.join([*[json.dumps(r) for r in reads],terminal('SUCCESS',complete['review'])]),'')])
    agent=vision.AntigravityCollectionAgent(source,model='synthetic')
    agent._review_once(Path(rows[0]['original_path']),{**task['project_snapshot'],'notes':''},references=refs)
    if tamper:
        records=json.loads((source/'visual-audit.json').read_text('utf8'))
        records[0]['review']['reason']='Altered completed judgment'
        worker.save(source/'visual-audit.json',records)
        with pytest.raises(worker.AgentUnavailable):worker.resume_collection(task,source,state)
        assert not calls
    else:
        output,_=worker.resume_collection(task,source,state)
        assert len(output['candidates'])==3 and calls==['1.png','2.png']


def test_explicit_imported_partial_continues_and_preserves_previous_zip(tmp_path,monkeypatch):
    import hashlib,io,sys,zipfile
    from conftest import image_bytes
    from ref_lab.collection_timing import CollectionTiming
    task={**job(),'target_count':2}
    folder=tmp_path/'.local/collection-runs'/task['id']/'current';folder.mkdir(parents=True)
    class Agent(FakeAgent):model='synthetic'
    class Browser(FakeBrowser):
        gated=True
        def search(self,step):
            value=super().search(step)
            value['cards']=[{'page':'https://example.org/old' if self.gated else 'https://example.org/new'}]
            if self.gated and step['source']=='pinterest':value['login_required']=True
            return value
    old_bytes=image_bytes(1)
    original=row(folder,'old.png',old_bytes);browser=Browser([original])
    manifest,images=worker.collect(task,Agent(),browser,folder)
    worker.save(folder/'run-info.json',{'job_id':task['id'],'model':'synthetic'})
    output=tmp_path/'result.zip';stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        for name,raw in images.items():archive.writestr('images/'+name,raw)
    prior=stream.getvalue();output.write_bytes(prior);receipt_sha=hashlib.sha256(prior).hexdigest()
    browser=Browser([row(folder,'new.png',image_bytes(60))]);browser.gated=False
    agent=Agent();agent.timing=CollectionTiming(folder)
    monkeypatch.setattr(worker,'ROOT',tmp_path)
    monkeypatch.setattr(worker,'load_job_info',lambda path:(task,None))
    monkeypatch.setattr(worker,'AntigravityCollectionAgent',lambda *a,**kw:agent)
    monkeypatch.setattr(worker,'Browser',lambda *a:browser)
    monkeypatch.setattr(worker.subprocess,'check_output',lambda *a,**kw:str(tmp_path/'.git'))
    monkeypatch.setenv('LAB_COLLECTION_RECOVERY_MODE','continue_imported_partial')
    monkeypatch.setenv('LAB_COLLECTION_IMPORTED_RESULT_SHA256',receipt_sha)
    monkeypatch.setattr(sys,'argv',['collector',str(tmp_path/'job.json'),str(output),'--vision-workers','1'])
    worker.main()
    with zipfile.ZipFile(output) as archive:
        delivered=json.loads(archive.read('manifest.json'))
        assert len(delivered['candidates'])==2 and delivered['execution_report']['status']=='completed'
        assert archive.read('images/old.png')==old_bytes
    assert agent.calls==1
    assert output.with_name('result-'+receipt_sha+'.zip').read_bytes()==prior
    # Reusing the old imported receipt cannot silently overwrite a newer result.
    with pytest.raises(ValueError,match='SHA changed'):worker.main()
    monkeypatch.delenv('LAB_COLLECTION_RECOVERY_MODE')
    monkeypatch.delenv('LAB_COLLECTION_IMPORTED_RESULT_SHA256')
    with zipfile.ZipFile(output) as archive:
        files={name:archive.read(name) for name in archive.namelist()}
    files['images/old.png']=image_bytes(3)
    with zipfile.ZipFile(output,'w') as archive:
        for name,raw in files.items():archive.writestr(name,raw)
    with pytest.raises(ValueError,match='original'):worker.main()
    assert agent.calls==1


def test_api_runner_imports_real_controller_state_contract(client,library,project,tmp_path,monkeypatch):
    import hashlib,sys
    from pathlib import Path
    from conftest import image_bytes
    from ref_lab.models import JobInput
    from ref_lab.verified_collection import AntigravityCollectionAgent,NamePlan
    from test_verified_collection import result
    task=library.create_job(project['id'],JobInput(kind='collection',target_count=1))
    class Agent(AntigravityCollectionAgent):
        def plan(self,project):return NamePlan(names=[project['character'],'Example Person','テスト甲'],
            name_records=[{'name':project['character'],'language':'zh','source':'synthetic trusted record'}])
        def prepare(self,project,plan):
            path=self.folder/'reference-images/ref.png';path.parent.mkdir(exist_ok=True)
            path.write_bytes(image_bytes(70,(320,480)))
            self.references=[{'asset_sha':hashlib.sha256(path.read_bytes()).hexdigest(),
                'path':str(path.resolve()),'page_url':'https://example.org/official','label':'Synthetic identity reference',
                'authority':'official_publisher'}]
        def _review_once(self,path,project,*,references=None):
            self.candidate_calls+=1;self.vision_cli_calls+=1
            return result(path,project,reference_comparisons=[{'reference_sha':self.references[0]['asset_sha'],
                'assessment':'supports','scope':'identity','supporting_features':['Synthetic trait1','Synthetic trait2'],
                'conflicting_features':[]}])
    class Browser(FakeBrowser):
        def __init__(self,folder):super().__init__([row(folder,'photo.png',image_bytes(1))])
    monkeypatch.setattr(worker,'AntigravityCollectionAgent',Agent)
    monkeypatch.setattr(worker,'Browser',Browser)
    monkeypatch.setattr(worker,'historical_paths',lambda *a,**kw:[])
    monkeypatch.setenv('LAB_COLLECTION_COMMAND',json.dumps([sys.executable,str(Path(worker.__file__)),
        '{task_file}','{result_file}']))
    def execute(lib,job_id,attempt_id,argv,*args,**kwargs):
        assert job_id==task['id']
        monkeypatch.setattr(sys,'argv',[argv[1],argv[2],argv[3],'--vision-workers','1'])
        worker.main()
        return 0
    monkeypatch.setattr('ref_lab.agent_collection.run_process',execute)
    response=client.post(f"/api/jobs/{task['id']}/run-antigravity")
    assert response.status_code==200,response.text
    saved=response.json()
    assert saved['status']=='succeeded' and saved['collection_outcome']=='complete'
    assert saved['collection_coverage']['required_languages']==['en','ja','zh']
    assert saved['collection_coverage']['usable_languages']==['en','ja','zh']
    assert len(saved['last_receipt_reference_ids'])==1
