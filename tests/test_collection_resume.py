"""Synthetic transport/checkpoint tests; not visual accuracy evidence."""
import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from ref_lab import verified_collection as vision
from tools import collect_verified as worker
from test_verified_collection import PROJECT, result


def fake_processes(monkeypatch, responses):
    calls=[];values=iter(responses)
    class Process:
        def __init__(self,command,**kwargs):
            calls.append(command);self.returncode,self.output,self.error=next(values)
            self.stdout=io.StringIO(self.output);self.stderr=io.StringIO(self.error)
        def communicate(self,**kwargs):return self.output,self.error
        def poll(self):return self.returncode
        def wait(self,**kwargs):return self.returncode
    monkeypatch.setattr(vision,'find_antigravity_cli',lambda:'agy')
    monkeypatch.setattr(vision.subprocess,'Popen',Process)
    monkeypatch.setattr(vision.time,'sleep',lambda seconds:None)
    monkeypatch.setattr('ref_lab.agent_collection.stop_process_tree',lambda process:None)
    return calls


def terminal(status,structured=None):
    return json.dumps({'event':'result','result':{'status':status,'structured_output':structured,'usage':{'total_tokens':0},'duration_seconds':0}})


def test_eof_is_retried_but_raw_diagnostic_credentials_are_not_saved(tmp_path,monkeypatch):
    error='loadCodeAssist EOF; model not recognized; access_token=PRIVATE_ACCESS bearer PRIVATE_BEARER'
    calls=fake_processes(monkeypatch,[(1,terminal('ERROR'),error),(0,terminal('SUCCESS',{'names':['Example Person']}),'')])
    agent=vision.AntigravityCollectionAgent(tmp_path)
    assert agent.run('Synthetic prompt',vision.NamePlan).names==['Example Person']
    assert len(calls)==2
    attempts=list(tmp_path.glob('attempt-*.json'));assert len(attempts)==2
    saved=''.join(f.read_text('utf8') for f in attempts)
    assert 'transient_network' in saved and 'PRIVATE_ACCESS' not in saved and 'PRIVATE_BEARER' not in saved


def test_retry_limit_is_durable_across_process_restart(tmp_path,monkeypatch):
    calls=fake_processes(monkeypatch,[(1,terminal('ERROR'),'EOF')]*3)
    for _ in range(2):
        with pytest.raises(vision.AgentUnavailable):vision.AntigravityCollectionAgent(tmp_path).run('Same failed prompt',vision.NamePlan)
    assert len(calls)==3


def test_auth_failure_stops_without_transient_retry(tmp_path,monkeypatch):
    calls=fake_processes(monkeypatch,[(1,terminal('ERROR'),'Authentication required: please log in')])
    with pytest.raises(vision.AgentUnavailable) as error:vision.AntigravityCollectionAgent(tmp_path).run('Auth fixture',vision.NamePlan)
    assert len(calls)==1 and error.value.fatal


def test_denied_read_is_fatal_without_retry_even_when_cli_says_success(tmp_path,monkeypatch):
    response=json.dumps({'event':'result','result':{'status':'SUCCESS','denied_actions':[{'action':'read_file'}]}})
    calls=fake_processes(monkeypatch,[(0,response,'')])
    with pytest.raises(vision.AgentUnavailable) as error:vision.AntigravityCollectionAgent(tmp_path).run('Denied fixture',vision.NamePlan)
    assert len(calls)==1 and error.value.fatal and error.value.category=='permission_denied'


def test_resume_external_inputs_use_only_official_narrow_workspace_directories(tmp_path,monkeypatch):
    run=tmp_path/'run';run.mkdir();target=tmp_path/'original/images/target.png';target.parent.mkdir(parents=True);target.write_bytes(b'photo')
    ref=tmp_path/'original/reference/images/ref.png';ref.parent.mkdir(parents=True);ref.write_bytes(b'reference')
    def opened(p):return {'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(p.resolve())}}}}
    stream='\n'.join([json.dumps(opened(target)),json.dumps(opened(ref)),terminal('SUCCESS',result(target).model_dump())])
    calls=fake_processes(monkeypatch,[(0,stream,'')])
    vision.AntigravityCollectionAgent(run).run('Scoped photo fixture',vision.CollectionVision,target,reference_paths=(ref,))
    command=calls[0];directories={command[i+1] for i,x in enumerate(command) if x=='--add-dir'}
    assert directories=={str(target.parent.resolve()),str(ref.parent.resolve())}
    assert '--sandbox' in command and '--dangerously-skip-permissions' not in command


def test_model_catalog_eof_is_not_misclassified_as_model_or_startup_auth_failure():
    log='error getting token source: You are not logged into Antigravity.\napplyAuthResult: [redacted]\nloadCodeAssist: EOF\nmodel not recognized as a known model'
    d=vision.diagnose_cli(terminal('ERROR'),log=log)
    assert d['category']=='transient_network' and d['retryable'] and not d['fatal']


def test_valid_image_receipt_is_reused_after_restart_but_changed_bytes_are_blocked(tmp_path,monkeypatch):
    target=tmp_path/'image.png';target.write_bytes(b'original')
    value=result(target);read={'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(target.resolve())}}}}
    stream=json.dumps(read)+'\n'+terminal('SUCCESS',value.model_dump())
    calls=fake_processes(monkeypatch,[(0,stream,'')])
    for _ in range(2):assert vision.AntigravityCollectionAgent(tmp_path).run('Fixed photo prompt',vision.CollectionVision,target)==value
    assert len(calls)==1
    target.write_bytes(b'changed')
    with pytest.raises(vision.AgentUnavailable):vision.AntigravityCollectionAgent(tmp_path).run('Fixed photo prompt',vision.CollectionVision,target)
    assert len(calls)==1


def resume_fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(worker,'ROOT',tmp_path)
    source=tmp_path/'.local/collection-runs/synthetic/source';source.mkdir(parents=True)
    state=tmp_path/'.local/collection-resumes/synthetic/source';refs=source/'reference-research/images';refs.mkdir(parents=True)
    def image(path,color):
        path.parent.mkdir(parents=True,exist_ok=True);b=io.BytesIO();Image.new('RGB',(320,480),color).save(b,'PNG');path.write_bytes(b.getvalue());return hashlib.sha256(b.getvalue()).hexdigest()
    ref=refs/'ref.png';ref_sha=image(ref,'green');rows=[]
    for i,color in enumerate(['red','blue','yellow']):
        photo=source/f'images/{i}.png';sha=image(photo,color)
        rows.append({'asset_sha':sha,'original_path':str(photo.resolve()),'page_url':f'https://example.org/post/{i}','image_url':f'https://example.org/photo/{i}.png'})
    def prediction(path):return result(path,reference_comparisons=[{'reference_sha':ref_sha,'assessment':'supports','supporting_features':['Synthetic trait1','Synthetic trait2'],'conflicting_features':[]}])
    complete={'asset_sha':rows[0]['asset_sha'],'source_page':rows[0]['page_url'],'review':prediction(Path(rows[0]['original_path'])).model_dump(),'accepted':True,'decision':'CONFIRMED'}
    audit=[complete,*[{'asset_sha':r['asset_sha'],'source_page':r['page_url'],'review':None,'accepted':False,'decision':'NEEDS_EVIDENCE','execution_error':'Previous interruption'} for r in rows[1:]]]
    def save(name,v):(source/name).write_text(json.dumps(v),encoding='utf8')
    job={'id':'synthetic','project_snapshot':PROJECT,'notes':'','target_count':1}
    save('run-info.json',{'job_id':job['id'],'model':'synthetic','visual_call_budget':20,'binding':worker.job_binding(job,'synthetic')})
    save('counts.json',{'attempted_visual_calls':2})
    save('received.json',rows);save('visual-audit.json',audit)
    save('manifest.json',{'schema_version':3,'job_id':'synthetic','batch_id':'original','candidates':[], 'execution_report':{'producer':'synthetic','status':'blocked','summary':'Fixture','source_checks':[],'query_log':[],'gaps':[]}})
    save('reference-research/report.json',{'references':[{'asset_sha':ref_sha,'path':str(ref.resolve()),'page_url':'https://example.org/official','label':'Synthetic target','authority':'official_publisher'}]})
    calls=[]
    class Agent:
        producer='synthetic';model='synthetic'
        def __init__(self,*args,**kwargs):self.references=[];self.candidate_calls=0;self.vision_cli_calls=0
        def plan(self,*args):raise AssertionError('No new plan/search')
        def prepare(self,*args):raise AssertionError('No reference research')
        def review(self,path,project):calls.append(path.name);self.candidate_calls+=1;self.vision_cli_calls+=1;return prediction(path)
    monkeypatch.setattr(worker,'AntigravityCollectionAgent',Agent)
    monkeypatch.setattr(worker,'Browser',lambda *args:pytest.fail('Resume must not open browser'))
    return source,state,job,rows,complete,calls,Agent


def test_resume_reviews_pending_only_and_continues_past_soft_quantity_target(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    manifest,images=worker.resume_collection(job,source,state)
    assert calls==['1.png','2.png']  # Target1 must not cut off the25-style continuation.
    checkpoint=json.loads((state/'visual-audit.json').read_text('utf8'))
    assert checkpoint[0]==complete and all(r['review'] for r in checkpoint)
    worker.resume_collection(job,source,state)
    assert calls==['1.png','2.png']
    assert json.loads((source/'visual-audit.json').read_text('utf8'))[1]['review'] is None


def test_resume_after_interruption_skips_newly_completed_sha(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,Agent=resume_fixture(tmp_path,monkeypatch)
    original=Agent.review
    def interrupted(self,path,project):
        if path.name=='2.png':raise KeyboardInterrupt()
        return original(self,path,project)
    monkeypatch.setattr(Agent,'review',interrupted)
    with pytest.raises(KeyboardInterrupt):worker.resume_collection(job,source,state)
    monkeypatch.setattr(Agent,'review',original);worker.resume_collection(job,source,state)
    assert calls==['1.png','2.png']


def test_changed_photo_or_context_is_blocked_before_resume_model_call(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    Path(rows[1]['original_path']).write_bytes(b'changed')
    with pytest.raises((vision.AgentUnavailable,ValueError)):worker.resume_collection(job,source,state)
    assert not calls


def test_resume_context_and_reference_changes_do_not_reuse_completed_state(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    worker.resume_collection(job,source,state)
    changed={**job,'project_snapshot':{**PROJECT,'costume':'Different outfit'}}
    with pytest.raises(vision.AgentUnavailable):worker.resume_collection(changed,source,state)
    assert calls==['1.png','2.png']
    reference=next((source/'reference-research/images').iterdir());reference.write_bytes(b'changed')
    with pytest.raises(vision.AgentUnavailable):worker.resume_collection(job,source,state)
    assert calls==['1.png','2.png']


def test_concurrent_resume_refuses_second_worker_and_releases_lock(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,Agent=resume_fixture(tmp_path,monkeypatch);original=Agent.review
    def review(self,path,project):
        with pytest.raises(vision.AgentUnavailable):worker.resume_collection(job,source,state)
        return original(self,path,project)
    monkeypatch.setattr(Agent,'review',review);worker.resume_collection(job,source,state)
    worker.resume_collection(job,source,state)
    assert calls==['1.png','2.png']


def test_bootstrap_keeps_success_with_invalid_evidence_charged_and_pending_receipts(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    attempt={'result_type':'CollectionVision','result':{'status':'SUCCESS','denied_actions':['read_file']}}
    (source/'attempt-synthetic-1.json').write_text(json.dumps(attempt),encoding='utf8')
    receipt={'binding':{'model':'synthetic'},'result':{'asset_sha':rows[1]['asset_sha']}}
    (source/'agent-synthetic.json').write_text(json.dumps(receipt),encoding='utf8')
    worker.resume_collection(job,source,state)
    charged=list(state.glob('attempt-synthetic*.json'));assert len(charged)==1
    assert json.loads(charged[0].read_text('utf8'))['historic']
    assert json.loads((state/'agent-synthetic.json').read_text('utf8'))==receipt


def test_interrupted_bootstrap_does_not_commit_an_incomplete_checkpoint(tmp_path,monkeypatch):
    source,state,job,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    (source/'attempt-synthetic-1.json').write_text(json.dumps({'result':{'status':'ERROR'}}),encoding='utf8')
    original=worker.save
    def fail(path,value):
        if path.name.startswith('attempt-'):raise OSError('Synthetic write interruption')
        return original(path,value)
    monkeypatch.setattr(worker,'save',fail)
    with pytest.raises(OSError):worker.resume_collection(job,source,state)
    assert not calls and not (state/'resume-inputs.json').exists()
    monkeypatch.setattr(worker,'save',original);worker.resume_collection(job,source,state)
    assert calls==['1.png','2.png']
