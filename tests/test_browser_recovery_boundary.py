"""Exercise production recovery methods; doubles replace only external commands."""
import json
import subprocess
from types import SimpleNamespace
from urllib.parse import quote
import pytest
from ref_lab import browser_recovery as errors
from tools import collect_verified as worker
from tests.test_browserskill_recovery import SyntheticAgent, _job

def test_plain_exception_is_not_infrastructure():
    assert errors.is_infrastructure_error(ValueError("bad image")) is False
    assert errors.is_infrastructure_error(errors.PlatformRestrictionError("login")) is False

@pytest.mark.parametrize("text,secret", [
    ("Cookie: sid=fake-cookie; other=fake-other", "fake-cookie"),
    ("Authorization: Bearer fake-bearer.123", "fake-bearer"),
    ('{"token": "tiny"}', "tiny"),
    ('{"cookie": "sid=fake-cookie; other=fake-other"}', "fake-other"),
])
def test_secrets_do_not_survive(text, secret):
    assert secret not in errors.sanitize_diagnostics(text)

@pytest.mark.parametrize("code", ["challenge", "http_403", "rate_limited"])
def test_platform_errors_do_not_recreate_browser(code):
    err=errors.classify_bsk_error("navigate",1,json.dumps({"code":code,"message":"HTTP 403 captcha"}),"")
    assert isinstance(err, errors.PlatformRestrictionError)

def test_command_does_not_retry_dead_session(tmp_path, monkeypatch):
    calls=[]
    def run(*a,**kw):
        calls.append(a)
        return SimpleNamespace(returncode=1,stdout="",stderr="session not registered or already stopped")
    monkeypatch.setattr(worker.subprocess,"run",run)
    monkeypatch.setattr(worker.time,"sleep",lambda _:None)
    browser=worker.Browser(tmp_path);browser.bsk="bsk"
    with pytest.raises(errors.BrowserInfrastructureError):browser.command("navigate","https://example.test")
    assert len(calls)==1

def test_recovery_never_changes_browser_instance(tmp_path, monkeypatch):
    browser=worker.Browser(tmp_path);browser.bsk="bsk";browser.browser_id="original";browser.session="old"
    commands=[]
    def run(argv,**kw):
        commands.append(argv)
        stdout=json.dumps([{"instance_id":"other","browser_name":"edge"}]) if argv[1]=="browsers" else '{"session_id":"replacement"}'
        return SimpleNamespace(returncode=0,stdout=stdout,stderr="")
    monkeypatch.setattr(worker.subprocess,"run",run)
    monkeypatch.setattr(worker,"select_browserskill",lambda env:("bsk","other"))
    monkeypatch.setattr(worker.time,"sleep",lambda _:None)
    assert browser.recover() is False
    assert not any(c[1:3]==["session","start"] for c in commands)

def test_recovery_clamps_every_command_to_remaining_time(tmp_path,monkeypatch):
    browser=worker.Browser(tmp_path);browser.bsk="bsk";browser.browser_id="original";browser.session="old"
    clock=[0.0]; deadlines=[]
    monkeypatch.setattr(worker.time,"time",lambda:clock[0])
    monkeypatch.setattr(worker.time,"monotonic",lambda:clock[0])
    monkeypatch.setattr(worker.time,"sleep",lambda n:clock.__setitem__(0,clock[0]+n))
    def select(env):
        clock[0]+=59
        return "bsk","original"
    monkeypatch.setattr(worker,"select_browserskill",select)
    def run(argv,**kw):
        deadlines.append(clock[0]+kw["timeout"])
        if argv[1:3]==["session","stop"]:clock[0]+=6
        if argv[1]=="browsers":
            clock[0]+=min(kw["timeout"],54)
            raise subprocess.TimeoutExpired(argv,kw["timeout"])
        return SimpleNamespace(returncode=0,stdout='{"session_id":"replacement"}',stderr="")
    monkeypatch.setattr(worker.subprocess,"run",run)
    browser.recover()
    assert max(deadlines)<=60
    assert clock[0]<=60

class DetailDisconnect:
    supports_sort=True
    def __init__(self): self.recoveries=0; self.reads=0
    def start(self):pass
    def close(self):pass
    def can_recover(self):return True
    def recover(self,step=None):self.recoveries+=1;return False
    def search(self,step,sort="relevance"):
        return {"url":"https://www.pinterest.com/search/pins/?q="+quote(step["query"]),"search":step["query"],"visibleMain":"",
                "cards":[{"page":"https://www.pinterest.com/pin/123456/","text":"西木野真姬 cos 摄影"}]}
    def more(self,step): return self.search(step)
    def receive(self,card,step):
        self.reads+=1
        raise errors.BrowserInfrastructureError("session lost",code="session_not_found")

def test_detail_disconnect_reaches_recovery_and_remains_pending(tmp_path):
    browser=DetailDisconnect()
    summary,_=worker.collect(_job(),SyntheticAgent(),browser,tmp_path,search_only=True)
    state=json.loads((tmp_path/"collector-state.json").read_text("utf8"))
    assert browser.recoveries==1
    assert browser.reads==1
    assert summary["stop_reason"]=="browser_unavailable"
    assert state["searches"]["0"]["done"] is False
    assert summary["browser_errors"]
    assert json.loads((tmp_path/"progress.json").read_text("utf8"))["browser_errors"]

def test_start_disconnect_is_blocked_not_internal_error(tmp_path):
    class StartFailure(DetailDisconnect):
        def start(self):raise errors.BrowserInfrastructureError("daemon lost")
    summary,_=worker.collect(_job(),SyntheticAgent(),StartFailure(),tmp_path,search_only=True)
    assert summary["stop_reason"]=="browser_unavailable"
    assert summary["status"]=="blocked"

def test_adapters_use_collector_command_boundary(tmp_path):
    from tools.collect_adapter import fetch_pinterest_detail_metadata
    from tools.exact_recall import capture_note
    def dead(*args,**kwargs):
        raise errors.BrowserInfrastructureError("session lost",code="session_not_found")
    with pytest.raises(errors.BrowserInfrastructureError):
        fetch_pinterest_detail_metadata("bsk","owned","https://www.pinterest.com/pin/123456/",{},command=dead)
    with pytest.raises(errors.BrowserInfrastructureError):
        capture_note("bsk","owned",tmp_path,"https://www.xiaohongshu.com/explore/"+"a"*24,command=dead)

def test_recovery_requires_actual_read_after_session_creation(tmp_path,monkeypatch):
    browser=worker.Browser(tmp_path);browser.bsk="bsk";browser.browser_id="original";browser.session="old"
    commands=[]
    def run(argv,**kw):
        commands.append(argv[1])
        if argv[1]=="browsers":out='[{"instance_id":"original"}]'
        elif argv[1:3]==["session","start"]:out='{"session_id":"new"}'
        elif argv[1:3]==["cooperate","sync"]:out='{"context_id":"fresh","ready":true}'
        elif argv[1]=="evaluate":out='{"ok":true,"value":{"url":"about:blank","cards":[]}}'
        else:out='{}'
        return SimpleNamespace(returncode=0,stdout=out,stderr="")
    monkeypatch.setattr(worker.subprocess,"run",run)
    assert browser.recover() is True
    assert commands==["browsers","session","session","session","session","cooperate","evaluate"]
    assert browser.session=="new"

def test_api_projects_recovery_diagnostics(client,library,project,tmp_path,monkeypatch):
    from ref_lab import collection_queue
    from ref_lab.agent_collection import _owner_record
    import os
    monkeypatch.setattr(collection_queue,"run_directory",lambda _:tmp_path)
    response=client.post(f"/api/projects/{project['id']}/jobs",json={"kind":"collection","target_count":30,"collection_mode":"search"})
    assert response.status_code==201
    job_id=response.json()["id"]
    owner=_owner_record(os.getpid(),phase='running');attempt='fixture-recovery'
    library.start_collection_attempt(job_id,response.json()['revision'],attempt,owner=owner)
    safe=errors.sanitize_diagnostics({"action":"navigate","code":"session_not_found","details":"Cookie: sid=fake-cookie","result":"failed"})
    worker.save(tmp_path/"progress.json",{"phase":"browser_recovering","browser_errors":[safe],
                'job_id':job_id,'attempt_id':attempt,'owner':owner})
    worker.save(tmp_path/"search-summary.json",{"status":"blocked","stop_reason":"old_attempt"})
    data=client.get(f"/api/jobs/{job_id}/candidates").json()
    assert data["search"]["phase"]=="browser_recovering"
    assert data["search"]["status"]=="running"
    assert "fake-cookie" not in json.dumps(data)
    worker.save(tmp_path/"progress.json",{"phase":"finished"})
    worker.save(tmp_path/"search-summary.json",{"status":"blocked","stop_reason":"browser_unavailable","browser_errors":[safe]})
    library.update_search_stage(job_id,attempt,'blocked',
        {'status':'blocked','stop_reason':'browser_unavailable','counts':{'found':0}},'browser unavailable')
    data=client.get(f"/api/jobs/{job_id}/candidates").json()
    assert data["search"]["stop_reason"]=="browser_unavailable"
    assert data["search"]["browser_errors"]==[safe]


@pytest.mark.parametrize('patch',[{'attempt_id':'old-attempt'},{'owner':{}},{'job_id':'another-job'}])
def test_api_rejects_unbound_recovery_progress(client,library,project,tmp_path,monkeypatch,patch):
    from ref_lab import collection_queue
    from ref_lab.agent_collection import _owner_record
    import os
    monkeypatch.setattr(collection_queue,'run_directory',lambda _:tmp_path)
    response=client.post(f"/api/projects/{project['id']}/jobs",json={
        'kind':'collection','target_count':1,'collection_mode':'search'})
    assert response.status_code==201
    job=response.json();owner=_owner_record(os.getpid(),phase='running')
    library.start_collection_attempt(job['id'],job['revision'],'current-attempt',owner=owner)
    worker.save(tmp_path/'progress.json',{'phase':'browser_recovering','job_id':job['id'],
                'attempt_id':'current-attempt','owner':owner,**patch})
    data=client.get(f"/api/jobs/{job['id']}/candidates").json()
    assert data['job']['recovering'] is False
    assert data['search']['phase']!='browser_recovering'
    assert data['search']['status']=='running'

def test_lost_start_reply_cancels_exact_request_even_after_job_deadline(tmp_path,monkeypatch):
    browser=worker.Browser(tmp_path);browser.bsk="bsk";browser.browser_id="original"
    requests=[]
    def run(argv,**kw):
        requests.append(argv)
        if argv[1:3]==["session","start"]:
            raise subprocess.TimeoutExpired(argv,kw["timeout"])
        return SimpleNamespace(returncode=0,stdout='{"state":"closed"}',stderr='')
    monkeypatch.setattr(worker.subprocess,"run",run)
    with pytest.raises(errors.BrowserInfrastructureError):browser._start_session(timeout=1)
    start=next(r for r in requests if r[1:3]==["session","start"])
    token=start[start.index("--request-id")+1]
    browser.deadline=0
    browser.close()
    assert requests[-1][1:5]==["session","request",token,"--cancel"]
    assert browser.start_request is None
    assert json.loads((tmp_path/"browser-session.json").read_text("utf8"))["state"]=="closed"

def test_download_timeout_is_not_a_browser_disconnect():
    import httpx
    assert errors.is_infrastructure_error(httpx.ReadTimeout("timed out")) is False

def test_recovery_does_not_create_session_while_old_request_cleanup_pending(tmp_path,monkeypatch):
    browser=worker.Browser(tmp_path);browser.bsk="bsk";browser.browser_id="original";browser.start_request="owned-request"
    commands=[]
    def run(argv,**kw):
        commands.append(argv)
        out='[{"instance_id":"original"}]' if argv[1]=="browsers" else '{"state":"cancelling"}'
        return SimpleNamespace(returncode=0,stdout=out,stderr="")
    monkeypatch.setattr(worker.subprocess,"run",run)
    assert browser.recover() is False
    assert browser.start_request=="owned-request"
    assert not any(r[1:3]==["session","start"] for r in commands)
