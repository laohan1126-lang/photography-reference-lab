import copy
import hashlib
import json
from pathlib import Path
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest
from tools import learning_v2 as v2


def sample(tmp_path):
    p = tmp_path/'one.jpg'
    p.write_bytes(b'actual immutable sample bytes')
    sha = v2.file_sha(p)
    task = {'context': {'character':'A','costume':'version A'},
            'criteria': {'gesture':['prop_held'], 'background':['environment']},
            'min_known_features':3, 'label':'场照测试'}
    record = {'asset_sha':sha, 'original_path':str(p)}
    review = {'asset_sha':sha, 'opened_sha':sha, 'actor':'ai','producer':'test',
              'context_sha':v2.context_sha(task), 'kind':'cosplay_photo',
              'identity':'match', 'costume':'match',
              'evidence':{k:['synthetic test evidence'] for k in ('kind','identity','costume')},
              'features':{'viewpoint':'eye_level','gesture':'prop_held','background':'environment'}}
    return record, review, task


def test_unknown_and_component_evidence_do_not_become_match(tmp_path):
    r,v,t=sample(tmp_path)
    assert v2.evidence_state(r,v,t)['ai_state']=='CONFIRMED'
    v['identity']='uncertain'
    assert v2.evidence_state(r,v,t)['ai_state']=='NEEDS_EVIDENCE'
    v['identity']='match';v['evidence']['identity']=[]
    assert v2.evidence_state(r,v,t)['state']=='NEEDS_EVIDENCE'


@pytest.mark.parametrize('change', ['sha','context','opened','bytes','producer'])
def test_stale_or_unbound_evidence_is_refused(tmp_path,change):
    r,v,t=sample(tmp_path)
    if change=='sha':v['asset_sha']='0'*64
    if change=='context':t['context']['costume']='new version'
    if change=='opened':v['opened_sha']='0'*64
    if change=='producer':v['producer']=''
    if change=='bytes':Path(r['original_path']).write_bytes(b'changed')
    assert v2.evidence_state(r,v,t)['state']=='NEEDS_EVIDENCE'


@pytest.mark.parametrize('key,value', [('kind','collage'),('kind','illustration'),
                                       ('identity','mismatch'),('costume','mismatch')])
def test_observed_counterexamples_are_mismatch(tmp_path,key,value):
    r,v,t=sample(tmp_path);v[key]=value
    assert v2.evidence_state(r,v,t)['state']=='MISMATCH'


def test_human_is_separate_and_never_erases_type_or_version(tmp_path):
    r,v,t=sample(tmp_path);v['identity']='uncertain'
    h={'asset_sha':r['asset_sha'],'context_sha':v2.context_sha(t), 'actor':'human',
       'source_snapshot_sha':'exact snapshot hash','identity':'match'}
    s=v2.evidence_state(r,v,t,h)
    assert (s['ai_state'],s['state'],s['identity_source'])==('NEEDS_EVIDENCE','CONFIRMED','human')
    v['costume']='uncertain'
    assert v2.evidence_state(r,v,t,h)['state']=='NEEDS_EVIDENCE'
    v['kind']='collage'
    assert v2.evidence_state(r,v,t,h)['state']=='MISMATCH'
    v['identity']='mismatch'
    assert v2.evidence_state(r,v,t,h)['state']=='NEEDS_EVIDENCE'


def test_rank_preserves_pool_and_abstains_without_features(tmp_path):
    r,v,t=sample(tmp_path)
    ranked=v2.task_rank([r],{r['asset_sha']:v},t)
    assert ranked[0]['task_points']==2
    v['features']={}
    assert v2.task_rank([r],{r['asset_sha']:v},t)[0]['task_points'] is None
    with pytest.raises(ValueError):v2.task_rank([r,r],{r['asset_sha']:v},t)


def test_global_ndcg_and_missing_not_zero():
    ranking=list('abcdef')
    scores=dict(zip(ranking,[1,1,1,1,1,2]))
    assert 0<v2.ndcg(ranking,scores)<1
    assert v2.ndcg(ranking,{**scores,'f':None}) is None
    assert v2.ndcg(['a'],{'a':2}) is None


def evaluation_fixture(tmp_path,monkeypatch):
    r,v,t=sample(tmp_path)
    v2.save(tmp_path/'received.json',{'candidates':[r]})
    v2.save(tmp_path/'model-reviews.json',[v])
    ev={'rows':[r], 'review_order':[r['asset_sha']], 'task':t,
        'rankings':{m:[r['asset_sha']] for m in v2.METHODS},
        'reviews_sha':v2.digest([v]),'pool_sha':v2.digest([r]),
        'source_traceability':{},'search':{}}
    ev['rows'][0]['decision']={'ai_state':'CONFIRMED'}
    # Pool digest must match bytes actually saved before the decision was added.
    v2.save(tmp_path/'evaluation.json',ev)
    monkeypatch.setattr(v2,'check_freeze',lambda _: {})
    return r


def test_empty_review_has_no_accuracy_or_ndcg(tmp_path,monkeypatch):
    r=evaluation_fixture(tmp_path,monkeypatch)
    result=v2.ReviewStore(tmp_path).report()
    assert result['verification']['false_accept'] is None
    assert result['methods']['task_rank']['ndcg5'] is None
    assert result['outcome']=='NOT_PROVEN'
    assert not (tmp_path/'labels.json').exists()


def test_real_http_draft_resume_submit_immutable_and_token(tmp_path,monkeypatch):
    r=evaluation_fixture(tmp_path,monkeypatch)
    server=v2.create_server(tmp_path)
    th=threading.Thread(target=server.serve_forever,daemon=True);th.start()
    url=f'http://127.0.0.1:{server.server_port}'
    try:
        page=urlopen(url).read().decode()
        token=page.split("const token='")[1].split("'")[0]
        def call(path,payload=None,token_value=token):
            headers={'X-Review-Token':token_value,'Content-Type':'application/json'}
            req=Request(url+path,headers=headers,data=None if payload is None else json.dumps(payload).encode())
            return json.loads(urlopen(req).read())
        with pytest.raises(HTTPError):call('/api/draft',{},'wrong')
        with pytest.raises(HTTPError):call('/api/submit',{})
        labels={'identity':'target_cosplay','photography':'useful','aesthetic':'like'}
        call('/api/draft',{'asset_sha':r['asset_sha'],'labels':labels})
        assert v2.ReviewStore(tmp_path).state()['labels'][r['asset_sha']]==labels
        call('/api/submit',{})
        before=v2.file_sha(tmp_path/'labels-final.json')
        with pytest.raises(HTTPError):call('/api/draft',{'asset_sha':r['asset_sha'],'labels':labels})
        assert before==v2.file_sha(tmp_path/'labels-final.json')
        assert call('/api/report')['label_status']=='SUBMITTED'
        assert urlopen(url+'/image/'+r['asset_sha']).read()==Path(r['original_path']).read_bytes()
    finally:
        server.shutdown();server.server_close();th.join()
        if (tmp_path/'labels-final.json').exists():
            (tmp_path/'labels-final.json').chmod(0o666)


def test_drift_after_review_refused(tmp_path,monkeypatch):
    evaluation_fixture(tmp_path,monkeypatch)
    store=v2.ReviewStore(tmp_path)
    v2.save(tmp_path/'model-reviews.json',[])
    with pytest.raises(ValueError,match='drift'):store.state()
