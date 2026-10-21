"""Task completion and real process interruption tests; no external vision calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ref_lab.verified_collection import NamePlan
from tools import collect_verified as worker
from test_verified_collection import FakeAgent, FakeBrowser, job, row, PROJECT


class MultilingualAgent(FakeAgent):
    def plan(self, project):
        return NamePlan(names=[project['character'], 'Example Person', 'テスト甲'])


def test_target_does_not_skip_platform_or_available_language_opportunity(tmp_path):
    browser=FakeBrowser([row(tmp_path)]);agent=MultilingualAgent()
    manifest,images=worker.collect({**job(),'target_count':1},agent,browser,tmp_path)
    log=manifest['execution_report']['query_log']
    assert {q['source'] for q in log}=={'xiaohongshu','pinterest'}
    assert any('Example Person' in q['query'] for q in log)
    assert any('テスト甲' in q['query'] for q in log)
    assert len(images)==1 and agent.calls==1
    assert manifest['execution_report']['status']=='completed'


def test_partial_quantity_never_reports_complete(tmp_path):
    manifest,_=worker.collect(job(),FakeAgent(),FakeBrowser([row(tmp_path)]),tmp_path)
    assert len(manifest['candidates'])==1
    assert manifest['execution_report']['status']=='blocked'
    assert '部分完成' in manifest['execution_report']['summary']
    assert json.loads((tmp_path/'progress.json').read_text('utf8'))['outcome']=='partial'


def test_target_with_blocked_required_source_is_partial(tmp_path):
    class Browser(FakeBrowser):
        def search(self,step):
            value=super().search(step)
            if step['source']=='pinterest':value['login_required']=True
            return value
    manifest,_=worker.collect({**job(),'target_count':1},FakeAgent(),Browser([row(tmp_path)]),tmp_path)
    assert len(manifest['candidates'])==1
    assert manifest['execution_report']['status']=='blocked'
    assert json.loads((tmp_path/'progress.json').read_text('utf8'))['outcome']=='partial'


def test_completed_collect_reentry_preserves_batch_without_model_or_browser(tmp_path):
    task={**job(),'target_count':1};browser=FakeBrowser([row(tmp_path)])
    original,images=worker.collect(task,FakeAgent(),browser,tmp_path)
    class NoWork(FakeAgent):
        def plan(self,*args):raise AssertionError('completed planning repeated')
        def prepare(self,*args):raise AssertionError('completed research repeated')
        def review(self,*args):raise AssertionError('completed image reviewed again')
    second,again=worker.collect(task,NoWork(),FakeBrowser([]),tmp_path)
    assert original==second and images==again


def test_legacy_received_without_audit_row_is_recoverable(tmp_path,monkeypatch):
    from test_collection_resume import resume_fixture
    source,state,task,rows,complete,calls,_=resume_fixture(tmp_path,monkeypatch)
    (source/'visual-audit.json').write_text(json.dumps([complete]),encoding='utf8')
    manifest,_=worker.resume_collection(task,source,state)
    assert calls==['1.png','2.png'] and len(manifest['candidates'])==3


@pytest.mark.parametrize('fault',['received','audit','inflight'])
def test_hard_exit_reconciles_received_and_preserves_completed_decisions(tmp_path,fault):
    root=Path(worker.__file__).resolve().parents[1]
    script=tmp_path/'child.py'
    script.write_text('''import json, os, sys
from pathlib import Path
sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'tests')]
from tools import collect_verified as worker
from test_verified_collection import FakeAgent,FakeBrowser,job,row
folder=Path(sys.argv[2]); mode=sys.argv[3]
rows=[row(folder,'a.png',b'a'),row(folder,'b.png',b'b'),row(folder,'c.png',b'c')]
class Agent(FakeAgent):
 def review(self,path,project):
  if mode=='inflight' and path.name=='b.png':os._exit(73)
  with (folder/'model-calls.jsonl').open('a',encoding='utf8') as log:log.write(json.dumps(path.name)+'\\n')
  value=super().review(path,project)
  return value.model_copy(update={'identity':'mismatch' if path.name=='b.png' else 'match'})
save=worker.save
def interrupted(path,value):
 save(path,value)
 if mode=='received' and path.name=='received.json' and len(value)==1:os._exit(71)
 if mode=='audit' and path.name=='visual-audit.json' and value and value[0].get('review'):os._exit(72)
worker.save=interrupted
manifest,images=worker.collect({**job(),'target_count':3},Agent(states=['match','mismatch','match']),FakeBrowser(rows),folder)
(folder/'child-result.json').write_text(json.dumps({'manifest':manifest,'images':list(images)}),encoding='utf8')
''',encoding='utf8')
    command=[sys.executable,'-X','utf8',str(script),str(root),str(tmp_path)]
    crashed=subprocess.run([*command,fault],capture_output=True,text=True,encoding='utf8',timeout=30)
    assert crashed.returncode=={'received':71,'audit':72,'inflight':73}[fault],crashed.stderr
    resumed=subprocess.run([*command,'resume'],capture_output=True,text=True,encoding='utf8',timeout=30)
    assert resumed.returncode==0,resumed.stderr
    calls=[json.loads(line) for line in (tmp_path/'model-calls.jsonl').read_text('utf8').splitlines()]
    assert calls.count('a.png')==1
    assert calls.count('b.png')==1 and calls.count('c.png')==1
    assert len(json.loads((tmp_path/'visual-audit.json').read_text('utf8')))==3
    audit=json.loads((tmp_path/'visual-audit.json').read_text('utf8'))
    assert [r['accepted'] for r in audit]==[True,False,True]


def test_runtime_deadline_is_not_reset_by_agent_recreation(tmp_path):
    from ref_lab.verified_collection import AntigravityCollectionAgent
    import time
    first=AntigravityCollectionAgent(tmp_path)
    saved=json.loads((tmp_path/'runtime-budget.json').read_text('utf8'))
    saved['expires_at']=time.time()+50
    worker.save(tmp_path/'runtime-budget.json',saved)
    again=AntigravityCollectionAgent(tmp_path)
    assert 0<again.deadline-time.monotonic()<51


def test_scope_change_invalidates_completed_collection_before_any_model(tmp_path):
    task={**job(),'target_count':1}
    worker.collect(task,FakeAgent(),FakeBrowser([row(tmp_path)]),tmp_path)
    changed={**task,'project_snapshot':{**PROJECT,'costume':'different'}}
    with pytest.raises(worker.AgentUnavailable):
        worker.collect(changed,FakeAgent(),FakeBrowser([]),tmp_path)


@pytest.mark.parametrize('fault',['ReferenceDiscovery','SourceAssessment'])
def test_reference_receipt_hard_exit_resumes_exact_search_and_source_without_repeating_model(tmp_path,fault):
    root=Path(worker.__file__).resolve().parents[1];script=tmp_path/'research-child.py'
    script.write_text('''import hashlib, io, json, os, sys
from pathlib import Path
sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'tests')]
from PIL import Image
from ref_lab.automatic_references import ReferenceResearch
from ref_lab.verified_collection import AntigravityCollectionAgent,save_evidence
from test_automatic_references import PROJECT,PLAN,HTML,assessment
folder=Path(sys.argv[2]);fault=sys.argv[3]
buffer=io.BytesIO();Image.new('RGB',(320,480),'blue').save(buffer,'PNG');raw=buffer.getvalue()
class Agent(AntigravityCollectionAgent):
 def _run_attempt(self,prompt,result_type,image_path=None,*,reference_paths=(),search_query=None,attempt_path,binding):
  with (folder/'research-calls.jsonl').open('a',encoding='utf8') as log:log.write(json.dumps(result_type.__name__)+'\\n')
  if search_query:
   value=result_type(urls=['https://example.org/role'],reason='Synthetic exact search')
   reads=[{'tool':'search_web','state':state,'query':search_query} for state in ('ACTIVE','DONE')]
  else:
   value=assessment(hashlib.sha256(raw).hexdigest())
   reads=[{'tool':'view_file','state':'DONE','path':str(p.resolve())} for p in (image_path,*reference_paths)]
  self.last_tool_calls=reads
  attempt=json.loads(attempt_path.read_text('utf8'))
  save_evidence(attempt_path,{**attempt,'state':'finished','termination':'returned','exit_code':0,'tools':reads,
    'result':{'status':'SUCCESS','structured_output':value.model_dump(),'denied_actions':[]}})
  save_evidence(folder/('agent-'+hashlib.sha256(prompt.encode()).hexdigest()[:16]+'.json'),
    {'producer':self.producer,'binding':binding,'reads':reads,'result':value.model_dump()})
  if result_type.__name__==fault:os._exit(74)
  return value
def fetch(url,limit):return (raw,'image/png',url) if url.endswith('.png') else (HTML.encode(),'text/html',url)
agent=Agent(folder);research=ReferenceResearch(agent,folder,PROJECT,PLAN,fetch=fetch);research.prepare()
save_evidence(folder/'research-result.json',research.report())
''',encoding='utf8')
    command=[sys.executable,'-X','utf8',str(script),str(root),str(tmp_path)]
    crashed=subprocess.run([*command,fault],capture_output=True,text=True,encoding='utf8',timeout=30)
    assert crashed.returncode==74,crashed.stderr
    resumed=subprocess.run([*command,'resume'],capture_output=True,text=True,encoding='utf8',timeout=30)
    assert resumed.returncode==0,resumed.stderr
    calls=[json.loads(line) for line in (tmp_path/'research-calls.jsonl').read_text('utf8').splitlines()]
    assert calls.count('SourceAssessment')==1 and calls.count('ReferenceDiscovery')==2
    report=json.loads((tmp_path/'research-result.json').read_text('utf8'))
    assert report['prepared'] and report['search_queries']==2 and len(report['references'])==1
    again=subprocess.run([*command,'resume'],capture_output=True,text=True,encoding='utf8',timeout=30)
    assert again.returncode==0,again.stderr
    assert len((tmp_path/'research-calls.jsonl').read_text('utf8').splitlines())==3
    image=Path(report['references'][0]['path']);image.write_bytes(b'changed reference')
    changed=subprocess.run([*command,'resume'],capture_output=True,text=True,encoding='utf8',timeout=30)
    assert changed.returncode!=0 and 'resume_reference_changed' in changed.stderr
    assert len((tmp_path/'research-calls.jsonl').read_text('utf8').splitlines())==3


@pytest.mark.parametrize('source',['xiaohongshu','pinterest'])
def test_available_alias_languages_still_get_opportunity_with_one_selected_platform(source):
    steps=worker.query_steps(PROJECT,NamePlan(names=['测试角色甲','Example Person','テスト甲'],
        name_records=[{'name':'测试角色甲','language':'zh','source':'synthetic trusted record'}]),[source])
    assert {s['source'] for s in steps}=={source}
    assert {s['language'] for s in steps}=={'zh','en','ja'}
