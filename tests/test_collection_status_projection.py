'''F8: a finished Search is not a blocked job, and one status speaks everywhere.

The stage records are the truth: a Search that completed and whose Review
never ran is neither a failure nor a finished collection, and the same reading
has to appear in the stored record, in the API and on the page. An older record
that stored ``blocked`` for a finished Search is corrected on read; the stored
row itself is never rewritten.
'''
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ref_lab.models import JobInput, ProjectInput
from ref_lab.service import collection_progress, collection_stage_states, collection_status

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_data(tmp_path,monkeypatch):
    monkeypatch.setenv('LAB_DATA_DIR',str(tmp_path/'data'))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_DIR',str(tmp_path/'data/assets'))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_ROOTS','[]')


def _summary(state, found=2, target_reached=False):
    return {"version": 1, "status": state, "stop_reason": "probe", "target": 2,
            "target_reached": target_reached,
            "counts": {"found": found, "duplicates": 0, "errors": 0,
                       "usable_named": found, "target_confirmed": found},
            "elapsed_seconds": 1.0, "first_received_seconds": 0.5,
            "queries": [], "source_checks": [], "searches": {}, "errors": [],
            "model_calls": 0, "tokens": 0, "cumulative_elapsed_seconds": 1.0}


def _job(library, mode="search"):
    project = library.create_project(ProjectInput(character="西木野真姬", brief="合成探针"))
    return library.create_job(project["id"], JobInput(
        kind="collection", target_count=2, collection_mode=mode, notes="合成探针"))


def _run_search(library, job, state, found=2, target_reached=False):
    attempt = "probe-attempt-0001"
    library.start_collection_attempt(job["id"], job["revision"], attempt)
    return library.update_search_stage(job["id"], attempt, state,
                                       _summary(state, found, target_reached), "probe " + state)


def test_a_completed_search_is_not_persisted_as_blocked(library):
    job = _job(library, mode="search_review")
    updated = _run_search(library, job, "completed", 2, True)
    assert updated["search_state"] == "completed"
    assert updated["collection_outcome"] == "complete"
    assert updated["status"] != "blocked", (
        "search_state=completed but status=%r: an unrun Review must not negate it"
        % updated["status"])
    assert updated["status"] != "succeeded", (
        "a completed Search is not a passed Review")


@pytest.mark.parametrize("state,found", [("partial", 1), ("failed", 0),
                                          ("blocked", 1), ("cancelled", 1)])
def test_every_other_search_state_keeps_its_own_verdict(library, state, found):
    job = _job(library, mode="search_review")
    updated = _run_search(library, job, state, found, False)
    assert updated["search_state"] == state
    assert updated["status"] != "succeeded", "a %s search must not report success" % state
    assert updated["status"] != "awaiting_review", "a %s search is not awaiting a Review" % state
    if state == "partial":
        assert updated["collection_outcome"] == "partial"


def test_the_stored_status_and_the_read_projection_agree(library):
    job = _job(library, mode="search_review")
    updated = _run_search(library, job, "completed", 2, True)
    assert collection_status(updated) == updated["status"]


def test_an_older_record_that_said_blocked_is_read_as_finished():
    """A legacy row keeps its bytes; the read projection states the truth."""
    legacy = {"kind": "collection", "status": "blocked", "collection_mode": "search_review",
              "search_state": "completed", "review_state": "idle",
              "collection_outcome": "complete"}
    assert collection_status(legacy) != "blocked"
    assert collection_status(legacy) == "awaiting_review"


def test_a_stale_review_with_imported_refs_is_not_still_running():
    """A Review whose process is gone cannot keep the Job looking running."""
    stale = {"kind": "collection", "status": "running", "collection_mode": "search_review",
             "search_state": "completed", "review_state": "running",
             "review_imported_ids": ["prior-accepted-ref"],
             "review_process_owner": {"pid": 999999, "creation": 1, "executable": "python312"}}
    assert collection_stage_states(stale) == ("completed", "blocked")
    assert collection_status(stale) != "running", "a dead owner keeps the job running"
    assert collection_status(stale) == "blocked"


def test_a_finished_admission_keeps_its_recorded_status():
    admitted = {"kind": "collection", "status": "succeeded", "collection_mode": "search_review",
                "search_state": "completed", "review_state": "completed",
                "collection_outcome": "complete", "review_imported_ids": ["ref-1"]}
    assert collection_status(admitted) == "succeeded"


def test_a_running_recovery_is_reported_from_the_real_progress_file(tmp_path):
    from ref_lab.agent_collection import _owner_record
    import os
    owner = _owner_record(os.getpid(), phase="running")
    job = {"id":"recovery-job", "kind":"collection", "status":"running", "collection_mode":"search_review",
           "search_state":"running", "review_state":"idle", "search_attempt_id":"attempt-1",
           "collection_process_owner":owner}
    progress = {"phase":"browser_recovering", "job_id":job["id"], "attempt_id":"attempt-1", "owner":owner}
    (tmp_path / "progress.json").write_text(json.dumps(progress), encoding="utf8")
    assert collection_progress(job, folder=tmp_path)["recovering"] is True
    for patch in ({"search_attempt_id":"attempt-2"}, {"status":"cancelled"},
                  {"search_state":"completed"}, {"collection_process_owner":{**owner,"creation":-1}}):
        assert collection_progress({**job,**patch}, folder=tmp_path)["recovering"] is False
    (tmp_path / "progress.json").write_text(json.dumps({"phase":"browser_recovering"}), encoding="utf8")
    assert collection_progress(job, folder=tmp_path)["recovering"] is False


def test_a_platform_login_wait_is_reported_as_a_manual_action(tmp_path):
    """Only the owner can log in; the product states it and does not retry."""
    (tmp_path / "progress.json").write_text(json.dumps({"phase": "collecting"}), encoding="utf8")
    job = {"kind": "collection", "status": "blocked", "collection_mode": "search_review",
           "search_state": "blocked", "review_state": "idle",
           "search_stop_reason": "login_or_challenge"}
    signals = collection_progress(job, folder=tmp_path)
    assert signals["manual_action"] == "login_required"
    assert signals["recovering"] is False


def test_a_formal_admission_keeps_its_recorded_status():
    admitted = {"kind": "collection", "status": "succeeded", "collection_mode": "search_review",
                "search_state": "completed", "review_state": "completed",
                "collection_outcome": "complete", "review_imported_ids": ["ref-1"]}
    assert collection_status(admitted) == "succeeded"


def test_a_running_stage_is_running():
    from ref_lab.agent_collection import _owner_record
    import os
    running = {"kind": "collection", "status": "running", "collection_mode": "search_review",
               "search_state": "running", "review_state": "idle",
               "collection_process_owner": _owner_record(os.getpid(), phase="initializing")}
    assert collection_status(running) == "running"


def test_a_stale_running_stage_is_not_reported_as_running():
    """The process that owned the run is gone: the record keeps its history,
    the projection states that nothing is running any more."""
    from ref_lab.agent_collection import _owner_record
    import os
    stale = {"kind": "collection", "status": "running", "collection_mode": "search_review",
             "search_state": "running", "review_state": "idle",
             "collection_process_owner": {"pid": 999999, "creation": 1,
                                           "executable": "python312"}}
    assert collection_status(stale) == "blocked"
    assert collection_stage_states(stale)[0] == "blocked"
    assert stale["search_state"] == "running", "the stored record is untouched"

    alive = {"kind": "collection", "status": "running", "collection_mode": "search_review",
             "search_state": "running", "review_state": "idle",
             "collection_process_owner": _owner_record(os.getpid(), phase="initializing")}
    assert collection_status(alive) == "running"
    assert collection_stage_states(alive)[0] == "running"


def test_every_state_the_service_can_persist_has_a_page_label():
    source = (REPO / "web" / "app.js").read_text("utf8")
    search_match = re.search(r"searchStageLabels\s*=\s*\{([^}]*)\}", source)
    review_match = re.search(r"reviewStageLabels\s*=\s*\{([^}]*)\}", source)
    assert search_match and review_match

    def labels(block):
        return dict(re.findall(r"([a-z_]+)\s*:\s*'([^']+)'", block))

    search = labels(search_match.group(1))
    review = labels(review_match.group(1))
    for state in ("idle", "queued", "running", "completed", "partial", "blocked", "failed", "cancelled"):
        assert state in search, "search state %r has no page label" % state
        assert search[state].strip(), "search state %r has an empty page label" % state
    for state in ("idle", "queued", "running", "completed", "partial", "blocked", "failed", "cancelled"):
        assert state in review, "review state %r has no page label" % state
    assert len(set(search.values())) == len(search), "two search states share one page label"


def test_the_overall_status_has_a_readable_label():
    source = (REPO / "web" / "app.js").read_text("utf8")
    match = re.search(r"const statuses = \{([^}]*)\}", source)
    assert match
    labels = dict(re.findall(r"([a-z_]+)\s*:\s*'([^']+)'", match.group(1)))
    for state in ("blocked", "running", "succeeded", "failed", "cancelled", "partial", "awaiting_review"):
        assert state in labels, "overall status %r has no page label" % state
        assert labels[state].strip()


def test_completed_search_does_not_wait_for_login_to_an_unused_source(tmp_path):
    job = {"status":"completed","search_state":"completed","search_stop_reason":"target_reached",
           "search_summary":{"source_blocked":True}}
    assert collection_progress(job,folder=tmp_path)["manual_action"] == ""


def test_search_only_completion_keeps_review_and_import_available(library):
    job=_job(library,mode='search')
    updated=_run_search(library,job,'completed',2,True)
    assert updated['status']=='completed' and updated['review_state']=='idle'
    started=library.start_review_stage(job['id'],'review-next')
    assert started['status']=='running' and started['review_state']=='running'


def test_cancel_search_does_not_cancel_the_independent_review(library):
    job=_job(library,mode='search_review')
    running=library.start_collection_attempt(job['id'],job['revision'],'cancel-search')
    cancelled=library.cancel_search_stage(job['id'])
    assert cancelled['search_state']=='cancelled'
    assert cancelled['status']!='cancelled'
    assert library.start_review_stage(job['id'],'review-next')['review_state']=='running'


@pytest.mark.parametrize('state,reached',[('partial',False),('completed',True)])
def test_new_terminal_search_status_can_be_explicitly_cancelled(library,state,reached):
    job=_job(library,mode='search')
    updated=_run_search(library,job,state,1 if not reached else 2,reached)
    cancelled=library.transition_job(job['id'],'cancelled',updated['revision'],'owner cancelled')
    assert cancelled['status']=='cancelled'


def test_partial_search_can_restart_with_its_existing_budget(library):
    job=_job(library,mode='search')
    updated=_run_search(library,job,'partial',1,False)
    restarted=library.start_collection_attempt(job['id'],updated['revision'],'next-attempt')
    assert restarted['status']=='running' and restarted['search_attempt_id']=='next-attempt'


def test_recovery_progress_written_by_the_controller_is_attempt_bound(tmp_path,monkeypatch):
    import hashlib,os
    from tools import collect_verified as worker
    from ref_lab.collection_history import ImageHistory
    from ref_lab.agent_collection import _owner_record
    from tests.test_collect_repeat_association import _Browser,_raw
    from tests.test_browserskill_recovery import _job,SyntheticAgent
    raw=_raw();sha=hashlib.sha256(raw).hexdigest()
    job={**_job(target=1),'search_state':'running','status':'running','search_attempt_id':'current-attempt',
         'collection_process_owner':_owner_record(os.getpid(),phase='running')}
    monkeypatch.setenv('LAB_COLLECTION_JOB_ID',job['id'])
    monkeypatch.setenv('LAB_COLLECTION_ATTEMPT_ID','current-attempt')
    observed=[]
    class RecoveringBrowser(_Browser):
        def receive(self,card,step):
            rows=super().receive(card,step)
            self.return_failed=True
            return rows
        def can_recover(self):return True
        def recover(self,*args,**kwargs):
            observed.append(collection_progress(job,folder=tmp_path))
            return True
    browser=RecoveringBrowser(tmp_path,raw,sha,{'xiaohongshu','pinterest'})
    history=ImageHistory([])
    try:summary,_=worker.collect(job,SyntheticAgent(),browser,tmp_path,history=history,search_only=True)
    finally:history.close()
    assert observed and all(signal['recovering'] for signal in observed)
    assert summary['counts']['found']==1
    assert not collection_progress(job,folder=tmp_path)['recovering']


@pytest.mark.parametrize('mode,search,review,status,expected',[
    ('search','completed','failed','failed','completed'),
    ('search','completed','blocked','blocked','completed'),
    ('search','completed','cancelled','blocked','completed'),
    ('search_review','completed','failed','failed','failed'),
    ('search_review','completed','blocked','blocked','blocked'),
    ('search_review','completed','completed','succeeded','succeeded'),
    ('search_review','running','completed','running','blocked'),
    ('search_review','running','completed','succeeded','blocked'),
    ('search','running','completed','succeeded','blocked'),
    ('search_review','idle','completed','succeeded','blocked'),
    ('search_review','partial','completed','succeeded','partial'),
    ('search_review','failed','completed','succeeded','failed')])
def test_current_stage_priority_table(mode,search,review,status,expected):
    job={'kind':'collection','status':status,'collection_mode':mode,'search_state':search,
         'review_state':review,'collection_outcome':'complete','review_imported_ids':['old-ref'],
         'collection_process_owner':{'pid':999999,'creation':1,'executable':'python'}}
    assert collection_status(job)==expected
    assert job['review_imported_ids']==['old-ref'] and job['status']==status


@pytest.mark.parametrize('raw_status',['running','succeeded'])
def test_interrupted_search_with_old_review_can_resume_same_attempt(library,raw_status):
    from ref_lab.agent_collection import collection_can_resume
    from ref_lab.db import encode
    job=_job(library,mode='search_review')
    job=library.start_collection_attempt(job['id'],job['revision'],'new-search')
    job.update(status=raw_status,review_state='completed',collection_outcome='complete',
               review_imported_ids=['old-ref'],collection_process_owner={
                   'pid':999999,'creation':1,'executable':'python'})
    with library.db.transaction() as con:
        con.execute('UPDATE jobs SET status=?, data=? WHERE id=?',(raw_status,encode(job),job['id']))
    assert collection_status(job)=='blocked'
    assert collection_can_resume(library,job)
    resumed=library.resume_collection_attempt(job['id'],job['revision'],'new-search')
    assert resumed['status']=='running' and resumed['active_attempt_id']=='new-search'
    assert resumed['review_imported_ids']==['old-ref']


@pytest.mark.parametrize('review',['failed','blocked','cancelled'])
def test_optional_review_terminal_write_does_not_negate_completed_search(library,review):
    job=_job(library,mode='search')
    completed=_run_search(library,job,'completed',2,True)
    library.start_review_stage(job['id'],'optional-review')
    if review=='cancelled':updated=library.cancel_review_stage(job['id'])
    else:updated=library.update_review_stage(job['id'],'optional-review',review,
        {'counts':{'accepted':0,'found':0}},'optional review '+review)
    assert updated['status']=='completed' and updated['search_state']=='completed'
    assert updated['review_state']==review and not updated.get('review_imported_ids')
    if review=='failed':
        from ref_lab.agent_collection import review_can_resume
        assert review_can_resume(library,updated)


@pytest.mark.parametrize('current_search,revision_delta,allowed',[
    ('running',0,True),('running',1,False),('completed',0,False)])
def test_cancel_transition_uses_current_status_without_bypassing_revision_or_success(library,current_search,revision_delta,allowed):
    from ref_lab.db import encode
    from ref_lab.service import Problem
    job=_job(library,mode='search_review')
    job.update(status='succeeded',search_state=current_search,review_state='completed',
               collection_outcome='complete',review_imported_ids=['old-ref'],active_attempt_id='new-attempt',
               collection_process_owner={'pid':999999,'creation':1,'executable':'python'})
    with library.db.transaction() as con:
        con.execute('UPDATE jobs SET status=?,data=? WHERE id=?',('succeeded',encode(job),job['id']))
    if allowed:
        cancelled=library.transition_job(job['id'],'cancelled',job['revision']+revision_delta,'owner cancel')
        assert cancelled['status']=='cancelled' and cancelled['review_imported_ids']==['old-ref']
        assert 'active_attempt_id' not in cancelled
    else:
        with pytest.raises(Problem) as failure:
            library.transition_job(job['id'],'cancelled',job['revision']+revision_delta,'owner cancel')
        assert failure.value.status==409
        assert library.job(job['id'])['status']=='succeeded'
