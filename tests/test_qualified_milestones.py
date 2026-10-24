"""Canonical checkpoint observations, not model-finish timestamps or UI visibility."""
import copy
import json

import pytest

from ref_lab.collection_timing import CollectionTiming


def counts(n):return {'usable_named':n,'goal_shas':[f'{i:064x}' for i in range(n)]}


def test_milestones_persist_across_resume_and_count_decreases_stay_visible(tmp_path,monkeypatch):
    from ref_lab import collection_timing
    clock=[100.];monkeypatch.setattr(collection_timing.time,'time',lambda:clock[0])
    timing=CollectionTiming(tmp_path);state={'first_usable':7.}
    def observe(n,attempt='a',initial=False,resumed=False):
        return timing.qualified_checkpoint(state,counts(n),job_id='job',attempt_id=attempt,
            collector_elapsed=clock[0]-100,cumulative_elapsed=clock[0]-90,initial=initial,resumed=resumed)
    observe(0,initial=True);clock[0]=110.;observe(5)
    first=copy.deepcopy(state['qualified_timeline']['milestones'])
    assert set(first)=={'1','5'} and first['5']['at']==110.
    state=json.loads(json.dumps(state));clock[0]=115.;observe(5,'b',initial=True,resumed=True)
    assert state['qualified_timeline']['milestones']==first
    clock[0]=120.;observe(10,'b');clock[0]=125.;observe(4,'b');clock[0]=130.;observe(30,'b')
    timeline=state['qualified_timeline']
    assert set(timeline['milestones'])=={'1','5','10','20','30'}
    assert timeline['milestones']['1']==first['1'] and timeline['milestones']['5']==first['5']
    assert timeline['milestones']['30']['at']==130.
    assert timeline['decreases'][0]['qualified_count']==4 and timeline['decreases'][0]['previous_count']==10
    assert timeline['decreases'][0]['attempt_id']=='b' and len(timeline['decreases'][0]['qualified_shas_digest'])==64
    assert state['first_usable']==7.
    events=[json.loads(line) for line in timing.path.read_text('utf8').splitlines()]
    assert any(event['stage']=='qualified_count_decreased' for event in events)


def test_preexisting_resumed_counts_are_not_backfilled_as_new_milestones(tmp_path):
    timing=CollectionTiming(tmp_path);state={}
    timing.qualified_checkpoint(state,counts(20),job_id='job',attempt_id='resumed',
        collector_elapsed=0.,cumulative_elapsed=300.,initial=True,resumed=True)
    timeline=state['qualified_timeline']
    assert timeline['milestones']=={}
    assert timeline['not_backfilled']==[1,5,10,20]
    assert timeline['resume_observations'][0]['qualified_count']==20
    timing.qualified_checkpoint(state,counts(30),job_id='job',attempt_id='resumed',
        collector_elapsed=12.,cumulative_elapsed=312.)
    assert set(timeline['milestones'])=={'30'}


def test_milestones_fail_closed_on_count_or_job_binding_mismatch(tmp_path):
    timing=CollectionTiming(tmp_path);state={}
    with pytest.raises(ValueError,match='count/SHA'):
        timing.qualified_checkpoint(state,{'usable_named':1,'goal_shas':[]},job_id='job',attempt_id='a',
            collector_elapsed=0.,cumulative_elapsed=0.)
    timing.qualified_checkpoint(state,counts(0),job_id='job',attempt_id='a',collector_elapsed=0.,cumulative_elapsed=0.)
    with pytest.raises(ValueError,match='another Job'):
        timing.qualified_checkpoint(state,counts(1),job_id='another',attempt_id='a',collector_elapsed=1.,cumulative_elapsed=1.)


def test_resume_from_an_earlier_zero_checkpoint_does_not_backfill_later(tmp_path):
    timing=CollectionTiming(tmp_path);state={}
    timing.qualified_checkpoint(state,counts(0),job_id='job',attempt_id='a',collector_elapsed=0.,cumulative_elapsed=0.)
    state=json.loads(json.dumps(state))
    timing.qualified_checkpoint(state,counts(20),job_id='job',attempt_id='b',collector_elapsed=0.,
        cumulative_elapsed=100.,initial=True,resumed=True)
    timing.qualified_checkpoint(state,counts(21),job_id='job',attempt_id='b',collector_elapsed=1.,cumulative_elapsed=101.)
    assert state['qualified_timeline']['milestones']=={}
    assert state['qualified_timeline']['not_backfilled']==[1,5,10,20]


def test_unbound_local_observation_cannot_claim_a_bound_milestone(tmp_path):
    timing=CollectionTiming(tmp_path);state={}
    timing.qualified_checkpoint(state,counts(1),job_id='job',attempt_id=None,collector_elapsed=0.,cumulative_elapsed=0.)
    assert not state['qualified_timeline']['last']['binding_complete']
    assert not state['qualified_timeline']['milestones']
