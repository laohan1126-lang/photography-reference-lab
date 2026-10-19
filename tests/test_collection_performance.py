"""Fixed scheduling/evidence checks; synthetic pixels are not a vision benchmark."""
import copy
import hashlib
import json
from pathlib import Path
import threading
import time

import pytest

from ref_lab.collection_pipeline import OrderedReviews
from ref_lab.verified_collection import AntigravityCollectionAgent, AgentCallFailed, NamePlan
from tools import collect_verified as worker
from test_verified_collection import PROJECT, FakeBrowser, job, result, row


class TimedAgent(AntigravityCollectionAgent):
    def __init__(self, folder, *, delays=None, states=None):
        super().__init__(folder, model='synthetic-scheduling')
        self.delays=delays or {};self.states=states or {}
        self.active=0;self.peak=0;self.finished=[];self.committed=[]

    def plan(self, project):return NamePlan(names=[project['character']])

    def prepare(self, project, plan):
        self.references=[{'asset_sha':'c'*64,'page_url':'https://example.org/official'}]

    def _review_once(self, path, project, *, references=None):
        refs=copy.deepcopy(self.references if references is None else references)
        with self._budget_lock:
            self.candidate_calls+=1;self.vision_cli_calls+=1;self.active+=1
            self.peak=max(self.peak,self.active)
        try:
            if self.cancelled.wait(self.delays.get(path.name,.005)):
                raise AgentCallFailed('cancelled',fatal=True)
            state=self.states.get(path.name,'match')
            if isinstance(state,Exception):raise state
            value=result(path,project,identity=state,reference_comparisons=[
                {'reference_sha':r['asset_sha'],'assessment':'supports','scope':'identity',
                 'supporting_features':['Synthetic garment','Synthetic accessory'],'conflicting_features':[]}
                for r in refs])
            self.finished.append(path.name)
            return value
        finally:
            with self._budget_lock:self.active-=1

    def complete_review(self,path,project,value):
        self.committed.append(path.name)
        return super().complete_review(path,project,value)


def run_fixed(tmp_path, *, count=3,target=2,workers=2,states=None,delays=None):
    rows=[row(tmp_path,f'{i}.png',str(i).encode()) for i in range(count)]
    agent=TimedAgent(tmp_path,states=states,delays=delays)
    browser=FakeBrowser(rows)
    manifest,images=worker.collect({**job(),'target_count':target},agent,browser,tmp_path,workers=workers)
    return agent,browser,manifest,images,json.loads((tmp_path/'counts.json').read_text('utf8'))


def test_soft_target_never_records_an_unsubmitted_extra_candidate(tmp_path):
    agent,_,manifest,images,counts=run_fixed(tmp_path)
    assert len(manifest['candidates'])==len(images)==2
    assert counts['execution_unreviewed']==0
    assert counts['unique_images_received']==counts['completed_image_reviews']==2
    assert counts['stop_reason']=='soft_target_reached'
    assert agent.candidate_calls==2


def test_out_of_order_workers_commit_in_original_order(tmp_path):
    agent,_,manifest,_,counts=run_fixed(tmp_path,target=3,delays={'0.png':.07,'1.png':.001})
    assert agent.peak==2 and agent.finished.index('1.png')<agent.finished.index('0.png')
    assert agent.committed==['0.png','1.png','2.png']
    assert [Path(c['file']).name for c in manifest['candidates']]==agent.committed
    assert counts['execution_unreviewed']==0


def test_window_rejections_do_not_prematurely_stop_pending_valid_results(tmp_path):
    agent,_,manifest,_,counts=run_fixed(tmp_path,target=3,states={'0.png':'mismatch','1.png':'uncertain'})
    assert agent.candidate_calls==3 and len(manifest['candidates'])==1
    assert counts['completed_image_reviews']==3 and counts['stop_reason']=='search_plan_exhausted'
    audit=json.loads((tmp_path/'visual-audit.json').read_text('utf8'))
    assert [r['review']['identity'] for r in audit]==['mismatch','uncertain','match']


def test_browser_has_one_controller_and_overlaps_vision(tmp_path):
    records=[row(tmp_path,f'{i}.png',str(i).encode()) for i in range(3)]
    agent=TimedAgent(tmp_path,delays={f'{i}.png':.05 for i in range(3)})
    owner=threading.get_ident();overlaps=[]
    class Browser(FakeBrowser):
        def search(self,step):
            assert threading.get_ident()==owner
            value=super().search(step)
            value['cards']=[{'page':f'https://example.org/post/{i}'} for i in range(3)]
            return value
        def receive(self,card,step):
            assert threading.get_ident()==owner
            overlaps.append(agent.active>0)
            time.sleep(.005)
            return [records[int(card['page'].rsplit('/',1)[1])]]
        def close(self):
            assert threading.get_ident()==owner
            super().close()
    browser=Browser(records)
    manifest,_=worker.collect({**job(),'target_count':3},agent,browser,tmp_path,workers=2)
    assert any(overlaps) and len(manifest['candidates'])==3 and browser.closed


def test_gallery_exists_before_the_next_review_and_finishes_without_refresh(tmp_path):
    records=[row(tmp_path,f'{i}.png',str(i).encode()) for i in range(3)]
    agent=TimedAgent(tmp_path)
    original=agent.complete_review
    def complete(path,project,value):
        if len(agent.committed)>0:
            page=(tmp_path/'public/index.html').read_text('utf8')
            assert '任务仍在运行' in page and page.count('<img ')==len(agent.committed)
        return original(path,project,value)
    agent.complete_review=complete
    manifest,images=worker.collect({**job(),'target_count':3},agent,FakeBrowser(records),tmp_path,workers=2)
    page=(tmp_path/'public/index.html').read_text('utf8')
    assert 'http-equiv="refresh"' not in page and page.count('<img ')==3
    for candidate in manifest['candidates']:
        name=Path(candidate['file']).name
        assert (tmp_path/'public'/name).read_bytes()==images[name]


def test_queue_close_prevents_new_work_and_cancels_owned_workers(tmp_path):
    agent=TimedAgent(tmp_path,delays={'slow.png':10});agent.prepare(PROJECT,None)
    queued=OrderedReviews(agent,PROJECT,workers=2)
    queued.submit(row(tmp_path,'slow.png'))
    start=time.monotonic();queued.close(cancel=True)
    assert time.monotonic()-start<2 and agent.active==0
    with pytest.raises((ValueError,RuntimeError)):queued.submit(row(tmp_path,'late.png'))
    queued.close(cancel=True)


def test_fatal_failure_retains_all_queued_candidates_without_more_search(tmp_path):
    agent,browser,manifest,_,counts=run_fixed(tmp_path,target=3,
        states={'0.png':AgentCallFailed('authentication',fatal=True)},delays={'1.png':.05})
    assert browser.sources==['xiaohongshu'] and browser.closed and agent.active==0
    assert manifest['execution_report']['status']=='blocked'
    audit=json.loads((tmp_path/'visual-audit.json').read_text('utf8'))
    received=json.loads((tmp_path/'received.json').read_text('utf8'))
    assert [r['asset_sha'] for r in audit]==[r['asset_sha'] for r in received]
    assert counts['stop_reason']=='unrecoverable_agent_failure'


def test_reference_update_waits_for_readers_and_rechecks_old_pending_result(tmp_path):
    agent=TimedAgent(tmp_path,states={'0.png':'uncertain'},delays={'1.png':.04})
    agent.prepare(PROJECT,None)
    class Research:
        def __init__(self):self.references=agent.references;self.done=False
        def supplement(self,hint):
            assert agent.active==0
            if self.done:return False
            self.done=True
            self.references=[*self.references,{'asset_sha':'d'*64,'page_url':'https://example.org/another'}]
            agent.states['0.png']='match'
            return True
    agent.research=Research()
    queue=OrderedReviews(agent,PROJECT,workers=2)
    try:
        queue.submit(row(tmp_path,'0.png',b'0'));queue.submit(row(tmp_path,'1.png',b'1'))
        first=queue.take();second=queue.take()
        assert len(first[2])==len(second[2])==2
        assert agent.finished.count('1.png')==2
        assert {c.reference_sha for c in second[1].reference_comparisons}=={'c'*64,'d'*64}
        assert list(tmp_path.glob('superseded-initial-*.json'))
    finally:queue.close(cancel=True)


def test_duplicate_cli_startup_is_refused_before_agent_creation(tmp_path,monkeypatch):
    import sys
    task=tmp_path/'job.json';output=tmp_path/'result.zip';output.write_bytes(b'previous result')
    monkeypatch.setattr(worker,'ROOT',tmp_path)
    monkeypatch.setattr(worker,'load_job_info',lambda p:(job(),None))
    monkeypatch.setattr(worker,'AntigravityCollectionAgent',lambda *a,**k:pytest.fail('No model before result preflight'))
    monkeypatch.setattr(sys,'argv',['collect_verified',str(task),str(output)])
    with pytest.raises(ValueError,match='already exists'):worker.main()
    assert output.read_bytes()==b'previous result'
    assert not list((tmp_path/'.local').rglob('run-info.json'))


def test_same_job_lock_rejects_second_process_before_creating_a_run(tmp_path,monkeypatch):
    import sys
    monkeypatch.setattr(worker,'ROOT',tmp_path)
    monkeypatch.setattr(worker,'load_job_info',lambda p:(job(),None))
    monkeypatch.setattr(worker,'AntigravityCollectionAgent',lambda *a,**k:pytest.fail('No concurrent task startup'))
    monkeypatch.setattr(sys,'argv',['collect_verified',str(tmp_path/'job'),str(tmp_path/'result.zip')])
    with worker.resume_lock(tmp_path/'.local/collection-runs'/job()['id']):
        from ref_lab.verified_collection import AgentUnavailable
        with pytest.raises(AgentUnavailable):worker.main()
    assert not list((tmp_path/'.local').rglob('run-info.json'))


def test_same_prompt_concurrency_reuses_one_bound_receipt(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from test_collection_resume import fake_processes,terminal
    from ref_lab.verified_collection import CollectionVision
    path=Path(row(tmp_path)['original_path']);value=result(path)
    opened={'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(path.resolve())}}}}
    calls=fake_processes(monkeypatch,[(0,json.dumps(opened)+'\n'+terminal('SUCCESS',value.model_dump()),'')])
    agent=AntigravityCollectionAgent(tmp_path,model='synthetic-only')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:agent.run('Identical input fixture',CollectionVision,path),range(2)))
    assert results==[value,value] and len(calls)==1 and agent.vision_cli_calls==1 and agent.cache_hits==1


def test_atomic_budget_prevents_parallel_overdraw(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from ref_lab.verified_collection import CollectionVision
    agent=AntigravityCollectionAgent(tmp_path,model='synthetic-only');agent.vision_cli_limit=1
    paths=[Path(row(tmp_path,f'{i}.png',str(i).encode())['original_path']) for i in range(2)]
    calls=[]
    def attempt(prompt,kind,path,**kwargs):
        calls.append(path);time.sleep(.01);return result(path)
    monkeypatch.setattr(agent,'_run_attempt',attempt)
    def run(path):
        try:return agent.run(path.name,CollectionVision,path)
        except AgentCallFailed as exc:return exc.category
    with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(run,paths))
    assert agent.vision_cli_calls==len(calls)==1 and values.count('call_budget_exhausted')==1


def test_running_cli_cancellation_stops_its_actual_owned_process(tmp_path,monkeypatch):
    import os,subprocess,sys
    from concurrent.futures import ThreadPoolExecutor
    from ref_lab import verified_collection as vision
    from ref_lab import agent_collection as runner
    real_popen=subprocess.Popen;processes=[];started=threading.Event()
    def spawn(command,**kwargs):
        own=[sys._base_executable,'-c',"import json,time; print(json.dumps({'event':'started'}),flush=True); time.sleep(60)"]
        if os.name=='nt':own=[sys._base_executable,str(Path(runner.__file__).with_name('windows_adapter_runner.py')),*own]
        process=real_popen(own,**kwargs);processes.append(process);return process
    monkeypatch.setattr(vision,'find_antigravity_cli',lambda:'synthetic-process-only')
    monkeypatch.setattr(vision.subprocess,'Popen',spawn)
    agent=AntigravityCollectionAgent(tmp_path,model='synthetic-only');event=agent.timing.event
    def observed(stage,**fields):
        event(stage,**fields)
        if stage=='cli_first_event':started.set()
    agent.timing.event=observed
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(agent.run,'Process cancellation fixture',vision.CollectionVision)
        try:
            assert started.wait(8),'Synthetic process did not report startup'
        finally:agent.cancelled.set()
        with pytest.raises(AgentCallFailed,match='cancelled'):future.result(timeout=8)
    assert processes and all(p.poll() is not None for p in processes)
    attempt=json.loads(next(tmp_path.glob('attempt-*.json')).read_text('utf8'))
    assert attempt['termination']=='cancelled' and attempt['state']=='finished' and agent.vision_cli_calls==1


def test_timeout_attempts_are_bounded_and_durable(tmp_path,monkeypatch):
    import io,subprocess
    from ref_lab import verified_collection as vision
    from ref_lab import agent_collection as runner
    clock=[time.monotonic()];processes=[]
    class Process:
        def __init__(self,*args,**kwargs):
            self.stdout=io.StringIO('');self.stderr=io.StringIO('');self.returncode=None;processes.append(self)
        def wait(self,timeout=None):
            if self.returncode is not None:return self.returncode
            clock[0]+=300
            raise subprocess.TimeoutExpired('synthetic-only',timeout)
        def terminate(self):self.returncode=-1
        def poll(self):return self.returncode
    monkeypatch.setattr(vision.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(vision,'find_antigravity_cli',lambda:'synthetic-only')
    monkeypatch.setattr(vision.subprocess,'Popen',Process)
    monkeypatch.setattr(runner,'stop_process_tree',lambda p:p.terminate())
    agent=AntigravityCollectionAgent(tmp_path,model='synthetic-only');agent.deadline=clock[0]+10000
    monkeypatch.setattr(agent.cancelled,'wait',lambda seconds:False)
    with pytest.raises(AgentCallFailed,match='timeout'):agent.run('Timeout fixture',vision.CollectionVision)
    attempts=[json.loads(p.read_text('utf8')) for p in tmp_path.glob('attempt-*.json')]
    assert len(processes)==len(attempts)==3 and all(a['termination']=='timeout' for a in attempts)
    with pytest.raises(AgentCallFailed,match='retry_exhausted'):agent.run('Timeout fixture',vision.CollectionVision)
    assert len(processes)==3


def test_spawn_error_is_recorded_instead_of_looking_like_an_unfinished_call(tmp_path,monkeypatch):
    from ref_lab import verified_collection as vision
    monkeypatch.setattr(vision,'find_antigravity_cli',lambda:'synthetic-only')
    def missing(*args,**kwargs):raise OSError('Synthetic executable disappeared')
    monkeypatch.setattr(vision.subprocess,'Popen',missing)
    agent=AntigravityCollectionAgent(tmp_path,model='synthetic-only')
    with pytest.raises(AgentCallFailed,match='cli_spawn_failed'):agent.run('Spawn fixture',vision.CollectionVision)
    attempt=json.loads(next(tmp_path.glob('attempt-*.json')).read_text('utf8'))
    assert attempt['state']=='finished' and attempt['termination']=='spawn_failed' and agent.vision_cli_calls==1


def test_post_review_file_loss_is_not_misreported_as_successful_collection(tmp_path):
    rows=[row(tmp_path,f'{i}.png',str(i).encode()) for i in range(3)]
    agent=TimedAgent(tmp_path);original=agent.complete_review
    def lose_file(path,project,value):
        value=original(path,project,value)
        if path.name=='1.png':path.unlink()
        return value
    agent.complete_review=lose_file
    manifest,_=worker.collect({**job(),'target_count':3},agent,FakeBrowser(rows),tmp_path,workers=2)
    assert manifest['execution_report']['status']=='blocked'
    counts=json.loads((tmp_path/'counts.json').read_text('utf8'))
    assert counts['execution_unreviewed']>=1 and counts['stop_reason']=='unrecoverable_agent_failure'


def test_parallel_schema_and_working_directories_are_isolated(tmp_path,monkeypatch):
    import io
    from concurrent.futures import ThreadPoolExecutor
    from ref_lab import verified_collection as vision
    from ref_lab import agent_collection as runner
    path=Path(row(tmp_path)['original_path']);gate=threading.Barrier(2);calls=[]
    class Process:
        returncode=0
        def __init__(self,command,**kwargs):
            prompt=command[command.index('-p')+1]
            self.schema=Path(command[command.index('--json-schema')+1])
            self.expected='NamePlan' if prompt=='plan fixture' else 'CollectionVision'
            calls.append((kwargs['cwd'],self.schema))
            value={'names':['Synthetic']} if self.expected=='NamePlan' else result(path).model_dump()
            read={'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(path.resolve())}}}}
            stream=([json.dumps(read)] if self.expected=='CollectionVision' else [])
            stream.append(json.dumps({'event':'result','result':{'status':'SUCCESS','structured_output':value}}))
            self.stdout=io.StringIO('\n'.join(stream));self.stderr=io.StringIO('')
        def wait(self,**kwargs):
            gate.wait(timeout=3)
            assert json.loads(self.schema.read_text('utf8'))['title']==self.expected
            return 0
    monkeypatch.setattr(vision,'find_antigravity_cli',lambda:'synthetic-only')
    monkeypatch.setattr(vision.subprocess,'Popen',Process)
    monkeypatch.setattr(runner,'stop_process_tree',lambda process:None)
    agent=AntigravityCollectionAgent(tmp_path,model='synthetic-only')
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(agent.run,'plan fixture',NamePlan)
        second=pool.submit(agent.run,'photo fixture',vision.CollectionVision,path)
        assert first.result(timeout=5).names==['Synthetic']
        assert second.result(timeout=5).asset_sha==hashlib.sha256(path.read_bytes()).hexdigest()
    assert len({str(cwd) for cwd,_ in calls})==len({str(path) for _,path in calls})==2


def test_default_smoke_selects_both_prior_admission_strata_in_original_order(tmp_path):
    from tools.benchmark_collection import smoke_rows
    records=[row(tmp_path,f'{i}.png',str(i).encode()) for i in range(8)]
    values={r['asset_sha']:result(Path(r['original_path']),identity='match' if i%2 else 'uncertain') for i,r in enumerate(records)}
    chosen=smoke_rows(records,values,PROJECT,None)
    assert [Path(r['original_path']).name for r in chosen]==['0.png','1.png','6.png','7.png']


def test_positive_smoke_controls_are_fixed_before_model_output(tmp_path):
    from tools.benchmark_collection import smoke_rows
    records=[row(tmp_path,f'{i}.png',str(i).encode()) for i in range(8)]
    values={r['asset_sha']:result(Path(r['original_path']),identity='match' if i%2 else 'uncertain') for i,r in enumerate(records)}
    chosen=smoke_rows(records,values,PROJECT,None,True)
    assert [Path(r['original_path']).name for r in chosen]==['1.png','3.png','5.png','7.png']
