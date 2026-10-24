"""Bounded F4 behavior checks with synthetic pixels; no live collection or model."""
import hashlib
import io
import json

import pytest
from PIL import Image

from ref_lab import collection_history as history_module
from tools import collect_verified as worker


@pytest.fixture
def tmp_path(tmp_path_factory):return tmp_path_factory.mktemp('ef')


@pytest.fixture(autouse=True)
def isolated_data(tmp_path,monkeypatch):
    monkeypatch.setenv('LAB_DATA_DIR',str(tmp_path/'data'))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_DIR',str(tmp_path/'data/assets'))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_ROOTS','[]')


def _png(color):
    stream=io.BytesIO();Image.new('RGB',(270,360),color).save(stream,format='PNG')
    return stream.getvalue()


def test_every_alias_is_read_but_identical_verified_bytes_decode_once(tmp_path,monkeypatch):
    raw=_png('green');paths=[]
    for i in range(3):
        path=tmp_path/f'alias-{i}.png';path.write_bytes(raw);paths.append(path)
    calls=[];real=history_module._fingerprint_from_raw
    def decode(path,raw,sha):
        calls.append((path,sha));return real(path,raw,sha)
    monkeypatch.setattr(history_module,'_fingerprint_from_raw',decode)
    history=history_module.ImageHistory(paths)
    try:
        assert len(calls)==1,'identical aliases were decoded repeatedly'
        assert len(history.records)==1
        assert history.match(paths[0])['reason']=='same_bytes'
        assert history.fingerprint_stats['hashed_bytes']==3*len(raw)
    finally:history.close()


def test_a_different_alias_is_never_reused_from_its_filename(tmp_path):
    green=_png('green');red=_png('red');sha=hashlib.sha256(green).hexdigest()
    first=tmp_path/'first.png';first.write_bytes(green)
    misleading=tmp_path/(sha+'.png');misleading.write_bytes(red)
    history=history_module.ImageHistory([first,misleading])
    try:assert set(history.records)=={sha,hashlib.sha256(red).hexdigest()}
    finally:history.close()


def test_unseen_first_is_stable_and_does_not_discard_old_posts():
    old={'page':'https://www.pinterest.com/pin/1/','text':'西木野真姬 cos'}
    first={'page':'https://www.pinterest.com/pin/2/','text':'西木野真姬 cos'}
    second={'page':'https://www.pinterest.com/pin/3/','text':'西木野真姬 cos'}
    result=worker._rank_discovery_cards([old,first,second],{worker._post_key(old['page'])},{},
        names=['西木野真姬'],work_terms=(),other_terms=())
    assert result==[first,second,old]
    note='a'*24
    assert worker._post_key('https://www.xiaohongshu.com/search_result/'+note)==worker._post_key('https://www.xiaohongshu.com/explore/'+note+'?token=synthetic')


@pytest.mark.parametrize('gain,pending,blocked,reason,low',[
    (0,0,False,'no_qualified_yield',True),
    (0,1,False,'qualification_pending',False),
    (1,0,False,'qualified_candidates_received',False),
    (0,0,True,'platform_blocked',False)])
def test_feedback_uses_qualified_gain_not_raw_downloads(gain,pending,blocked,reason,low):
    result=worker._qualified_feedback(before=0,after=gain,duplicates=0,received=8,cards=8,
        pending=pending,detail_failures=0,blocked=blocked)
    assert result['reason']==reason and result['low_yield']==low
    assert result['new_originals']==8


def _controller_fixture(tmp_path,monkeypatch,revisit=False,detail_cap=None):
    from urllib.parse import quote
    from tests.test_browserskill_recovery import SyntheticAgent,_job
    from tests.test_collage_split import _textured
    from tests.photo_type_fixture import synthetic_type
    monkeypatch.setattr(worker,'ROOT',tmp_path)
    old_page='https://www.pinterest.com/pin/111/'
    new_page='https://www.pinterest.com/pin/222/'
    raws=[]
    for seed,base in [(51,(30,80,140)),(52,(200,40,60)),(53,(60,180,90))]:
        buffer=io.BytesIO();_textured((800,600),seed,base).save(buffer,format='PNG');raws.append(buffer.getvalue())
    shas=[hashlib.sha256(raw).hexdigest() for raw in raws]
    old=tmp_path/'old.png';old.write_bytes(raws[0])
    metadata=tmp_path/'.local/collection-runs/old/received.json';metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps([{'asset_sha':shas[0],'page_url':old_page,
        'image_url':'https://i.pinimg.com/'+shas[0]+'.png','original_path':str(old)}]),'utf8')
    folder=tmp_path/'run';folder.mkdir()
    class Browser:
        supports_sort=True;known_shas=None;known_sources=None;incoming_dir=None
        return_failed=False;return_error=None;preview_reused=0
        def __init__(self):self.opened=[];self.window=0;self.old_visits=0
        def start(self):pass
        def close(self):pass
        def search(self,step,sort='relevance'):
            self.window=0
            return {'url':'https://www.pinterest.com/search/pins/?q='+quote(step['query']),
                    'search':step['query'],'cards':[{'page':page,'text':'西木野真姬 cosplay 摄影'}
                    for page in ([old_page] if revisit else [old_page,new_page])]}
        def more(self,step):
            snapshot=self.search(step);self.window=1;return snapshot
        def receive(self,card,step):
            self.opened.append(card['page'])
            if card['page']==old_page:self.old_visits+=1
            indexes=([0,2] if not revisit or self.old_visits>1 else [0]) if card['page']==old_page else [1]
            rows=[]
            for index in indexes:
                sha=shas[index];row={'asset_sha':sha,'page_url':card['page'],
                    'image_url':'https://i.pinimg.com/'+sha+'.png','width':800,'height':600,
                    'author_detail':{'title':'西木野真姬 cosplay 摄影'}}
                if self.known_sources and worker.normalize_image_url(row['image_url']) in self.known_sources:
                    rows.append({**row,'duplicate':True,'reason':'known_source_url'});continue
                path=folder/'incoming'/f'{len(self.opened)}-{index}.part';path.parent.mkdir(exist_ok=True)
                path.write_bytes(raws[index]);row.update(original_path=str(path),ext='png',temporary=True)
                synthetic_type(folder,row);rows.append(row)
            return rows
    if detail_cap is not None:monkeypatch.setattr(worker,'MAX_DETAIL_PAGES',detail_cap)
    browser=Browser();history=history_module.ImageHistory([old])
    job={**_job(target=1 if revisit else 2),'preferred_sources':['pinterest'],
         'search_attempt_id':'synthetic-efficiency-attempt'}
    try:summary,_=worker.collect(job,SyntheticAgent(),browser,folder,history=history,search_only=True)
    finally:history.close()
    return summary,browser,folder,shas


def test_controller_prefers_new_post_but_old_post_can_contribute_new_image(tmp_path,monkeypatch):
    summary,browser,folder,shas=_controller_fixture(tmp_path,monkeypatch)
    assert browser.opened[:2]==['https://www.pinterest.com/pin/222/','https://www.pinterest.com/pin/111/']
    received=json.loads((folder/'received.json').read_text('utf8'))
    assert {r['asset_sha'] for r in received}==set(shas[1:])
    assert summary['counts']['found']==2
    state=json.loads((folder/'collector-state.json').read_text('utf8'))
    assert state['details']==len(browser.opened)
    assert state['detail_schedule'][0]['previously_seen'] is False
    assert all(item['coverage']=='partial_or_unknown' for item in state['post_observations'].values())
    assert any(image['asset_sha']==shas[0] for item in state['post_observations'].values() for image in item['images'])
    milestone=state['qualified_timeline']['milestones']['1']
    assert milestone['attempt_id']=='synthetic-efficiency-attempt'
    assert milestone['qualified_count']==len(milestone['qualified_shas'])
    assert milestone['scope']=='collector_canonical_checkpoint'
    assert summary['qualified_timeline']['milestones']['1']==milestone


def test_controller_revisits_same_job_post_without_counting_old_bytes(tmp_path,monkeypatch):
    summary,browser,folder,shas=_controller_fixture(tmp_path,monkeypatch,revisit=True)
    assert len(browser.opened)>=2
    assert summary['counts']['found']==1
    assert json.loads((folder/'received.json').read_text('utf8'))[0]['asset_sha']==shas[2]
    state=json.loads((folder/'collector-state.json').read_text('utf8'))
    assert state['details']==len(browser.opened)<=3


def test_actual_revisits_consume_detail_budget(tmp_path,monkeypatch):
    summary,browser,folder,_=_controller_fixture(tmp_path,monkeypatch,revisit=True,detail_cap=1)
    assert len(browser.opened)==1
    assert summary['stop_reason']=='detail_budget_exhausted'
    assert summary['counts']['found']==0


def test_budget_freeze_does_not_raise_other_limits():
    assert (worker.MAX_DETAIL_PAGES,worker.MAX_GOAL_QUERIES,worker.MAX_WINDOWS)==(144,24,3)


def test_run_receipt_contains_actual_frozen_limits(tmp_path):
    from tests.test_browserskill_recovery import SyntheticAgent,_job
    job={**_job(target=30),'goal_id':'synthetic-goal','search_timeout_seconds':2700}
    worker._write_run_info(tmp_path,job,SyntheticAgent(),1,mode='search_only')
    info=json.loads((tmp_path/'run-info.json').read_text('utf8'))
    assert (info['candidate_budget'],info['query_budget'],info['windows_per_query'],
            info['detail_page_budget'],info['visual_call_budget'],info['search_timeout_seconds'])==(90,24,3,144,60,2700)


def _cover_fixture(tmp_path,monkeypatch):
    from tests.test_collage_split import _textured
    original=tmp_path/'original.png';_textured((540,720),77,(90,110,140)).save(original)
    with Image.open(original) as image:
        stream=io.BytesIO();image.resize((270,360)).save(stream,format='PNG')
    raw=stream.getvalue();sha=hashlib.sha256(raw).hexdigest()
    history=history_module.ImageHistory([original]);cache=tmp_path/'cover-cache.json';requests=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def raise_for_status(self):pass
        def iter_bytes(self):yield raw
    def get(method,url,**kwargs):requests.append(url);return Response()
    monkeypatch.setattr(worker.httpx,'stream',get)
    card={'page':'https://www.pinterest.com/pin/123/',
          'cover_url':'https://i.pinimg.com/236x/'+sha+'.png','cover_width':270,'cover_height':360}
    def browser(name):
        folder=tmp_path/name;folder.mkdir(exist_ok=True)
        instance=worker.Browser(folder);instance.cover_cache_path=cache
        return instance
    return history,card,cache,requests,browser


def test_cover_metadata_rechecks_relation_and_reuses_no_payload(tmp_path,monkeypatch):
    history,card,cache,requests,browser=_cover_fixture(tmp_path,monkeypatch)
    calls=[];real=history_module._photo_relation
    def relation(*args,**kwargs):calls.append(1);return real(*args,**kwargs)
    monkeypatch.setattr(history_module,'_photo_relation',relation)
    try:
        first=browser('first');initial=first.check_duplicate(card,history)
        assert initial and initial['preview_payload']=='temporary_removed'
        count=len(calls)
        second=browser('second');reused=second.check_duplicate(card,history)
        assert reused and reused['preview_payload']=='metadata_revalidated'
        assert len(calls)>count,'a stored duplicate verdict was inherited without pixel revalidation'
        assert len(requests)==1 and second.preview_payloads['metadata_hits']==1
        assert not (second.folder/'incoming').exists()
        assert not list((first.folder/'incoming/previews').glob('*'))
    finally:history.close()


@pytest.mark.parametrize('change',['version','checksum','reference_missing','url_query','dimensions'])
def test_cover_metadata_binding_changes_cannot_skip_download(tmp_path,monkeypatch,change):
    history,card,cache,requests,browser=_cover_fixture(tmp_path,monkeypatch)
    other=None
    try:
        assert browser('first').check_duplicate(card,history)
        data=json.loads(cache.read_text('utf8'))
        if change=='version':data['algorithm_version']-=1
        if change=='checksum':data['checksum']='0'*64
        cache.write_text(json.dumps(data),'utf8')
        if change=='reference_missing':other=history_module.ImageHistory([])
        if change=='url_query':card={**card,'cover_url':card['cover_url']+'?different=1'}
        if change=='dimensions':card={**card,'cover_width':540,'cover_height':720}
        current=browser('second');result=current.check_duplicate(card,other or history)
        assert len(requests)==2 and current.preview_payloads['metadata_hits']==0
        if other is not None:assert result is None
        current.close()
    finally:
        history.close()
        if other is not None:other.close()


def test_cover_metadata_has_a_fixed_entry_bound(tmp_path,monkeypatch):
    history,card,cache,requests,browser=_cover_fixture(tmp_path,monkeypatch)
    try:
        current=browser('first');current._cover_entries={f'old-{i}':{'unused':True} for i in range(64)}
        assert current.check_duplicate(card,history)
        entries=json.loads(cache.read_text('utf8'))['entries']
        assert len(entries)==64 and 'old-0' not in entries and card['cover_url'] in entries
    finally:history.close()


def test_goal_count_drop_after_target_observation_is_not_reported_as_success(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from ref_lab import collage,photo_types
    from tests.test_collect_repeat_association import _Browser,_raw
    from tests.test_browserskill_recovery import SyntheticAgent,_job
    monkeypatch.setattr(worker,'ROOT',tmp_path)
    from ref_lab.collection_history import DEDUP_SCOPE_VERSION
    baseline={'goal_id':'synthetic-goal','fingerprint_algorithm_version':history_module.FINGERPRINT_ALGORITHM_VERSION,
              'project_id':'synthetic-project','dedup_scope_version':DEDUP_SCOPE_VERSION,'items':[]}
    raw_baseline=json.dumps(baseline).encode();baseline_sha=hashlib.sha256(raw_baseline).hexdigest()
    (tmp_path/'baseline.json').write_bytes(raw_baseline)
    (tmp_path/'goal.json').write_text(json.dumps({'goal_id':'synthetic-goal','baseline_sha':baseline_sha,
        'baseline_shas':[],'started_at':0.,'target':1,'project_id':'synthetic-project',
        'dedup_scope_version':DEDUP_SCOPE_VERSION}),'utf8')
    class Types:
        def __init__(self,*a,**k):self.pending=SimpleNamespace(unfinished_tasks=0);self.blocked=False
        def enqueue(self,record):
            path=tmp_path/'photo-types.json';data=json.loads(path.read_text('utf8'))
            data['items'][record['parent_sha']]['history_check']={'state':'clear','baseline_sha':baseline_sha,
                'algorithm_version':history_module.FINGERPRINT_ALGORITHM_VERSION}
            path.write_text(json.dumps(data),'utf8')
        def drain(self,**k):pass
        def close(self,**k):pass
    class Collages:
        def __init__(self,folder,**kwargs):self.rows=[];self.callback=kwargs['on_record'];self._queue=SimpleNamespace(unfinished_tasks=0)
        def enqueue(self,row):
            self.rows.append(row);self.callback(collage.process_original(tmp_path,row))
        def drain(self,**kwargs):pass
        def close(self,**kwargs):
            for row in self.rows:row['source_text']='含 AI 生成内容'
        def summary(self):return collage.summarize_records(collage.DerivedStore(tmp_path).items())
    monkeypatch.setattr(photo_types,'PhotoTypeWorker',Types)
    monkeypatch.setattr(collage,'CollageWorker',Collages)
    raw=_raw();sha=hashlib.sha256(raw).hexdigest();history=history_module.ImageHistory([])
    history.baseline_sha=baseline_sha
    job={**_job(target=1),'goal_id':'synthetic-goal','search_attempt_id':'synthetic-attempt'}
    try:summary,_=worker.collect(job,SyntheticAgent(),_Browser(tmp_path,raw,sha,{'xiaohongshu','pinterest'}),
                                tmp_path,history=history,search_only=True)
    finally:history.close()
    assert summary['counts']['usable_named']==0
    assert not summary['target_reached'] and summary['status']!='completed'
    assert summary['stop_reason']=='qualified_count_decreased'
    timeline=summary['qualified_timeline']
    assert timeline['milestones']['1']['qualified_count']==1
    assert timeline['decreases'][-1]['qualified_count']==0
