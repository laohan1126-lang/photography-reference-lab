"""Read-only ancestry checks; any child processes belong exclusively to this test."""
import json
import os
import subprocess
import sys

import pytest

from ref_lab import agent_collection as processes
from ref_lab.service import collection_progress


def _record(pid,creation):return {'pid':pid,'creation':creation,'executable':'python'}


@pytest.mark.parametrize('parents,owner_creation,expected',[
    ({30:20,20:10},1,True),
    ({30:20,20:1},1,False),
    ({30:20,20:10},50,False),
    ({30:20,20:30},1,False)])
def test_ancestry_rejects_unrelated_live_processes_pid_reuse_and_cycles(monkeypatch,parents,owner_creation,expected):
    records={10:_record(10,owner_creation),20:_record(20,2),30:_record(30,3),1:_record(1,0)}
    monkeypatch.setattr(processes,'_process_identity',records.get)
    monkeypatch.setattr(processes,'_process_parent_pid',parents.get)
    assert processes._process_is_owned_by(records[10],records[30]) is expected


def test_matching_labels_and_two_live_processes_do_not_prove_recovery(tmp_path,monkeypatch):
    records={10:_record(10,1),20:_record(20,2),1:_record(1,0)}
    monkeypatch.setattr(processes,'_process_identity',records.get)
    monkeypatch.setattr(processes,'_process_parent_pid',lambda pid:1 if pid in (10,20) else None)
    job={'id':'job','status':'running','search_state':'running','search_attempt_id':'attempt',
         'collection_process_owner':records[10]}
    (tmp_path/'progress.json').write_text(json.dumps({'phase':'browser_recovering','job_id':'job',
        'attempt_id':'attempt','owner':records[20]}),'utf8')
    assert not collection_progress(job,folder=tmp_path)['recovering']


def test_unknown_identity_never_proves_ownership(monkeypatch):
    monkeypatch.setattr(processes,'_process_identity',lambda pid:{'pid':pid,'unknown':True})
    assert not processes._process_is_owned_by(_record(10,1),_record(20,2))


def test_live_owned_child_and_unrelated_live_sibling(tmp_path):
    children=[]
    try:
        for _ in range(2):
            child=subprocess.Popen([sys.executable,'-B','-c',
                "import sys; print('ready',flush=True); sys.stdin.readline()"],
                cwd=tmp_path,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            children.append(child)
            assert child.stdout.readline().strip()=='ready'
        owner=processes._owner_record(os.getpid(),phase='test-supervisor')
        first=processes._owner_record(children[0].pid,phase='test-child')
        second=processes._owner_record(children[1].pid,phase='test-child')
        assert processes._process_is_owned_by(owner,first)
        assert processes._process_is_owned_by(owner,second)
        assert not processes._process_is_owned_by(first,second)
    finally:
        for child in children:
            try:child.communicate(input='\n',timeout=5)
            except subprocess.TimeoutExpired:
                child.kill();child.communicate(timeout=5)
