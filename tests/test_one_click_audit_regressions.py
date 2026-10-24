"""Synthetic audit counterexamples, never proof of real photo accuracy."""
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from ref_lab import collage, photo_types, service
from ref_lab.models import JobInput
from ref_lab.browser_recovery import BrowserInfrastructureError
from tests.test_collage_split import _collage, _textured, _write_original
from tools import collect_verified as collector


@pytest.fixture
def goal_root(tmp_path, monkeypatch):
    monkeypatch.setattr(service, '__file__', str(tmp_path/'ref_lab/service.py'))
    return tmp_path


def goal_job(library, project, target=40):
    return library.create_job(project['id'], JobInput(kind='collection', collection_mode='search', target_count=target))


def prior_collection_job(library, project, job_id='history-job'):
    """A synthetic prior collection job so history runs have attribution."""
    with library.db.transaction() as con:
        con.execute('INSERT INTO jobs VALUES(?,?,?,?,?)',
                    (job_id, project['id'], 'collection', 'blocked', '{}'))
    return job_id


def test_same_second_goals_do_not_overwrite(library, project, goal_root, monkeypatch):
    monkeypatch.setattr(service.time, 'time', lambda: 100)
    a = goal_job(library, project, 30)
    folder = goal_root/'.local/goals'/a['goal_id']
    before = {p.name:p.read_bytes() for p in folder.iterdir()}
    b = goal_job(library, project, 40)
    assert a['goal_id'] != b['goal_id']
    assert before == {p.name:p.read_bytes() for p in folder.iterdir()}


def test_rejected_extend_changes_nothing(library, project, goal_root):
    job = goal_job(library, project)
    path = goal_root/'.local/goals'/job['goal_id']/'goal.json'
    before = path.read_bytes()
    with pytest.raises(service.Problem) as error:
        library.extend_search(job['id'], 70)
    assert error.value.status == 422
    assert path.read_bytes() == before
    assert library.job(job['id']) == job


def test_extend_file_failure_rolls_back_database(library, project, goal_root, monkeypatch):
    job = goal_job(library, project)
    path = goal_root/'.local/goals'/job['goal_id']/'goal.json'
    path.unlink()
    path.mkdir()  # Actual read/write failure, not a successful optional skip.
    with pytest.raises((OSError, service.Problem)):
        library.extend_search(job['id'], 1)
    assert library.job(job['id']) == job


def test_type_retry_respects_attempt_budget_and_keeps_each_receipt(tmp_path):
    row = _write_original(tmp_path, _textured((800, 600), 1, (70, 80, 90)))
    path = Path(row['original_path'])
    path.rename(path.with_name(row['asset_sha']+'.png'))
    class Analyzer:
        producer_name = 'synthetic'
        actual_calls = 0
        def classify(self, raw, sha, stop):
            self.actual_calls += 1
            self.last_receipt = {'status':'failed', 'tokens':100 if self.actual_calls == 1 else 7,
                                 'stream_path':f'attempt-{self.actual_calls}', 'stream_sha':str(self.actual_calls)}
            raise photo_types.ClassificationUnavailable('synthetic unavailable')
    for limit in (1, 2):
        (tmp_path/'photo-types.json').unlink(missing_ok=True)
        analyzer = Analyzer()
        worker = photo_types.PhotoTypeWorker(tmp_path, analyzer=analyzer, limit=limit)
        try:
            worker._process({'parent_sha':row['asset_sha'], 'status':collage.STATUS_NO_COLLAGE})
        finally:
            worker.close(timeout=0)
        data=json.loads((tmp_path/'photo-types.json').read_text())
        assert analyzer.actual_calls == limit
        assert len(data['calls']) == limit
        assert [c['tokens'] for c in data['calls']] == [100,7][:limit]
        assert len({c['stream_path'] for c in data['calls']}) == limit
        assert all(c['finished_at'] >= c['started_at'] for c in data['calls'])


def test_failed_close_retains_session_and_retries_original(tmp_path, monkeypatch):
    browser=collector.Browser(tmp_path)
    browser.session='owned-original'
    commands=[]
    def command(*args, **kw):
        commands.append(args)
        if len(commands)==1:raise BrowserInfrastructureError('timeout',code='timeout')
        return '{}'
    monkeypatch.setattr(browser,'command',command)
    with pytest.raises(BrowserInfrastructureError):browser.close()
    assert browser.session == 'owned-original'
    saved=json.loads((tmp_path/'browser-session.json').read_text())
    assert saved['session_id']=='owned-original' and saved['state']=='cleanup_pending'
    browser.close()
    assert commands == [('session','stop','owned-original')]*2
    assert browser.session is None


def test_expired_browser_budget_is_not_infrastructure(tmp_path, monkeypatch):
    browser=collector.Browser(tmp_path)
    browser.deadline=time.monotonic()-1
    monkeypatch.setattr(collector.subprocess,'run',lambda *a, **kw:pytest.fail('must not dispatch'))
    with pytest.raises(Exception) as error:browser.command('evaluate')
    assert not isinstance(error.value, BrowserInfrastructureError)
    assert getattr(error.value,'category',None)=='time_budget_exhausted'


def test_v2_no_collage_is_outdated_and_explicitly_recomputed(tmp_path):
    row=_write_original(tmp_path,_collage(3,1,tile=(800,600)))
    old={'parent_sha':row['asset_sha'],'algorithm_version':2,'status':collage.STATUS_NO_COLLAGE,
         'children':[], 'original_path':row['original_path']}
    collage.DerivedStore(tmp_path).put(row['asset_sha'],old)
    assert not collage.record_is_current(old)
    result=collage.process_original(tmp_path,row)
    assert result['previous_algorithm_version']=='2'
    snapshot=json.loads(Path(result['previous_record_snapshot']).read_text())
    assert snapshot['record']==old
    assert len(result['children'])==3
    assert hashlib.sha256(Path(row['original_path']).read_bytes()).hexdigest()==row['asset_sha']


@pytest.mark.parametrize('box', [(80, 30, 760, 570), (160, 90, 720, 510), (60, 60, 740, 570),
                                (240, 0, 560, 600), (272, 0, 528, 600), (0, 180, 800, 420),
                                (296, 24, 488, 336)])
def test_history_excludes_reencoded_crops_but_preserves_other_frames(tmp_path, box):
    from PIL import ImageDraw
    from ref_lab.collection_history import ImageHistory
    image = _textured((800, 600), 41, (70, 90, 120))
    draw = ImageDraw.Draw(image)
    draw.ellipse((310, 75, 460, 220), fill=(210, 170, 130))
    draw.line((380, 260, 650, 400), fill=(220, 40, 50), width=45)
    original = tmp_path/'original.png'; image.save(original)
    cropped = tmp_path/'crop.jpg'; image.crop(box).resize((1020, 810)).save(cropped, quality=91)
    # Preserve actual crop aspect; arbitrary aspect distortion is not a re-encoding.
    image.crop(box).resize(((box[2]-box[0])*2, (box[3]-box[1])*2)).save(cropped, quality=91)
    other = image.copy()
    draw = ImageDraw.Draw(other)
    draw.rectangle((340, 230, 700, 450), fill=(70, 90, 120))
    draw.line((380, 260, 250, 450), fill=(220, 40, 50), width=45)
    next_frame=tmp_path/'next-frame.png';other.save(next_frame)
    history=ImageHistory([original])
    assert history.match(cropped), 'cropped copy must be excluded'
    assert history.match(next_frame) is None, 'a different arm pose must stay available'


@pytest.mark.parametrize('rotated', [False, True])
def test_narrow_crop_does_not_reject_a_different_visible_pose(tmp_path, rotated):
    from PIL import Image, ImageDraw
    from ref_lab.collection_history import ImageHistory
    original = _textured((800, 600), 19, (70, 90, 120))
    next_frame = original.copy()
    ImageDraw.Draw(original).line((330, 180, 470, 420), fill=(230, 30, 50), width=50)
    ImageDraw.Draw(next_frame).line((470, 180, 330, 420), fill=(230, 30, 50), width=50)
    box = (240, 0, 560, 600)
    if rotated:
        original = original.transpose(Image.Transpose.ROTATE_90)
        next_frame = next_frame.transpose(Image.Transpose.ROTATE_90)
        box = (0, 240, 600, 560)
    source = tmp_path / 'original.png'
    original.save(source)
    duplicate = tmp_path / 'same-frame.jpg'
    original.crop(box).save(duplicate, quality=93)
    different = tmp_path / 'different-frame.jpg'
    next_frame.crop(box).save(different, quality=93)
    history = ImageHistory([source])
    assert history.match(duplicate), 'the same visible crop must stay excluded'
    assert history.match(different) is None, 'a changed visible pose must remain available'


def test_goal_baseline_freezes_verified_fingerprints(library, project, goal_root):
    from tests.conftest import image_bytes
    from ref_lab.db import encode
    asset=library.assets.ingest(image_bytes(17), 'synthetic.png')
    with library.db.transaction() as con:
        con.execute('INSERT INTO assets VALUES(?,?)',(asset['id'],encode(asset)))
        con.execute('INSERT INTO refs VALUES(?,?,?,?,?,?)',
                    ('ref-baseline', project['id'], asset['id'], 'keep', 'active', '{}'))
    job=goal_job(library,project,30)
    baseline=json.loads((goal_root/'.local/goals'/job['goal_id']/'baseline.json').read_text())
    entries={r['sha']:r for r in baseline['items']}
    assert entries[asset['id']]['fingerprint']['asset_sha']==asset['id']


def test_mixed_collage_keeps_new_panel_and_parent_is_not_its_own_history(tmp_path):
    from ref_lab.collection_history import ImageHistory
    first = _write_original(tmp_path, _collage(2, 1, tile=(800, 600),
        bases=[(28, 30, 34), (222, 220, 214)]), name='first.png')
    first_record = collage.process_original(tmp_path, first)
    history = ImageHistory([Path(first['original_path'])])
    for child in first_record['children']:
        history.consider(Path(child['path']), exclude={first['asset_sha']})
    second = _write_original(tmp_path, _collage(2, 1, tile=(800, 600),
        bases=[(28, 30, 34), (52, 150, 196)]), name='second.png')
    assert history.consider(Path(second['original_path'])) is None, 'an old panel does not make the entire new collage old'
    result = collage.process_original(tmp_path, second, history=history)
    assert result['children'][0]['status'] == collage.DUPLICATE_RUN
    assert result['children'][1]['status'] == collage.VALID
    assert history.match(Path(second['original_path']))['reason'] == 'same_bytes'
    assert history.match(Path(result['children'][1]['path']))['reason'] == 'same_bytes'
    history.close()


def test_history_requires_matcher_before_marking_index_ready(monkeypatch):
    import builtins
    from ref_lab.collection_history import ImageHistory
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == 'cv2':
            raise ImportError('synthetic missing matcher')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', missing)
    with pytest.raises(ValueError, match='History matcher unavailable'):
        ImageHistory([])


def test_extend_second_file_failure_restores_first_and_database(library, project, goal_root, monkeypatch):
    from ref_lab import storage
    job=goal_job(library,project)
    goal=goal_root/'.local/goals'/job['goal_id']/'goal.json'
    run_goal=goal_root/'.local/collection-runs'/job['id']/'current/goal.json'
    run_goal.parent.mkdir(parents=True)
    run_goal.write_bytes(goal.read_bytes())
    before=goal.read_bytes(); real=storage.atomic_write
    def fail_second(path, raw):
        if path==run_goal:raise PermissionError('synthetic held file')
        return real(path,raw)
    monkeypatch.setattr(storage,'atomic_write',fail_second)
    with pytest.raises(PermissionError):library.extend_search(job['id'],1)
    assert library.job(job['id'])==job
    assert goal.read_bytes()==run_goal.read_bytes()==before


def test_complete_native_type_receipt_is_reused_after_retry(tmp_path):
    row=_write_original(tmp_path,_textured((800,600),2,(80,100,130)))
    sha=row['asset_sha'];path=Path(row['original_path']);path.rename(path.with_name(sha+'.png'))
    evidence=tmp_path/'type-evidence';evidence.mkdir()
    result={'asset_sha':sha,'kind':'cosplay_photo','evidence':'synthetic actual-read routing fixture'}
    class Analyzer:
        producer_name='synthetic'
        count=0
        def classify(self,raw,asset_sha,stop):
            self.count+=1
            stream=evidence/f'{self.count}.jsonl'
            preview=tmp_path/'images'/(sha+'.png')
            stream.write_text(json.dumps({'step_update':{'tool_name':'view_file','state':'DONE','tool_info':{'parameters':{'AbsolutePath':str(preview)}}}})+'\n'+json.dumps({'event':'result','result':{'status':'SUCCESS','response':json.dumps(result)}}))
            self.last_receipt={'asset_sha':sha,'producer':self.producer_name,'status':'failed',
             'stream_path':str(stream),'stream_sha':hashlib.sha256(stream.read_bytes()).hexdigest(),
             'tokens':None if self.count==1 else 7}
            if self.count==1:raise photo_types.ClassificationUnavailable('synthetic retry')
            self.last_receipt.update(status='succeeded',result_status='SUCCESS',read_evidence={
             'tool':'view_file','state':'DONE','asset_sha':sha,'preview_sha':sha,'path':str(preview)})
            return SimpleNamespace(model_dump=lambda **kw:result)
    analyzer=Analyzer();worker=photo_types.PhotoTypeWorker(tmp_path,analyzer=analyzer,limit=2)
    record={'parent_sha':sha,'status':collage.STATUS_NO_COLLAGE}
    try:
        worker._process(record);worker._process(record)
        data=json.loads((tmp_path/'photo-types.json').read_text())
        assert analyzer.count==2 and len(data['calls'])==2
        assert data['calls'][0]['tokens'] is None and data['calls'][0]['status']=='blocked'
        assert data['calls'][1]['status']=='succeeded' and data['calls'][1]['tokens']==7
        assert not worker.blocked
    finally:worker.close(timeout=0)


def test_type_deadline_prevents_any_model_attempt(tmp_path):
    row=_write_original(tmp_path,_textured((800,600),7,(80,100,130)))
    sha=row['asset_sha'];path=Path(row['original_path']);path.rename(path.with_name(sha+'.png'))
    class Analyzer:
        producer_name='synthetic'
        def classify(self,*args):pytest.fail('expired job must not call a model')
    worker=photo_types.PhotoTypeWorker(tmp_path,analyzer=Analyzer(),deadline=time.monotonic()-1)
    try:
        worker._process({'parent_sha':sha,'status':collage.STATUS_NO_COLLAGE})
        assert worker.blocked and worker.block_reason=='time_budget_exhausted'
        assert not (tmp_path/'photo-types.json').exists()
    finally:worker.close(timeout=0)


def test_single_command_timeout_remains_distinct_from_total_budget(tmp_path,monkeypatch):
    browser=collector.Browser(tmp_path);browser.deadline=time.monotonic()+60
    def timeout(*args,**kw):raise subprocess.TimeoutExpired(args,kw['timeout'])
    monkeypatch.setattr(collector.subprocess,'run',timeout)
    with pytest.raises(BrowserInfrastructureError) as err:browser.command('evaluate',timeout=1)
    assert err.value.code=='command_timeout' and err.value.is_timeout


def test_corrupt_type_ledger_does_not_reset_attempt_budget(tmp_path):
    row=_write_original(tmp_path,_textured((800,600),6,(70,100,120)))
    sha=row['asset_sha'];path=Path(row['original_path']);path.rename(path.with_name(sha+'.png'))
    ledger=tmp_path/'photo-types.json';ledger.write_bytes(b'{corrupt existing evidence')
    class Analyzer:
        producer_name='synthetic'
        def classify(self,*args):pytest.fail('corrupt ledger must not reset calls')
    worker=photo_types.PhotoTypeWorker(tmp_path,analyzer=Analyzer(),limit=1)
    try:
        worker._process({'parent_sha':sha,'status':collage.STATUS_NO_COLLAGE})
        assert worker.blocked and worker.block_reason=='type_evidence_invalid'
        assert ledger.read_bytes()==b'{corrupt existing evidence'
    finally:worker.close(timeout=0)


def test_type_receipt_must_match_native_result(tmp_path):
    from tests.photo_type_fixture import synthetic_type
    from ref_lab.collection_counts import compute
    row=_write_original(tmp_path,_textured((800,600),8,(70,100,130)))
    record=collage.process_original(tmp_path,row)
    synthetic_type(tmp_path,row)
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==1
    path=tmp_path/'photo-types.json';data=json.loads(path.read_text())
    data['items'][row['asset_sha']]['result']['kind']='portrait_photo'
    path.write_text(json.dumps(data),'utf8')
    assert compute(tmp_path,[row],{row['asset_sha']:record})['usable_named']==0


@pytest.mark.skipif(os.name != 'nt', reason='Actual Windows file sharing boundary')
@pytest.mark.parametrize('module_name',['ref_lab.storage','tools.learning_v1_human'])
def test_atomic_json_write_recovers_after_polling_reader_releases(tmp_path,monkeypatch,module_name):
    import importlib
    module=importlib.import_module(module_name)
    path=tmp_path/'polled.json';path.write_bytes(b'{"old":true}')
    opened=threading.Event();release=threading.Event();attempts=[];real=module.os.replace
    def reader():
        with path.open('rb'):
            opened.set();release.wait(30)
    def replace(*args,**kw):
        try:return real(*args,**kw)
        except PermissionError:
            attempts.append('reader still owns handle');release.set();raise
    thread=threading.Thread(target=reader);thread.start();assert opened.wait(2)
    monkeypatch.setattr(module.os,'replace',replace)
    try:module.atomic_write(path,b'{"new":true}')
    finally:release.set();thread.join(2)
    assert attempts and path.read_bytes()==b'{"new":true}'


def test_unreadable_goal_projection_cannot_reuse_stored_success_counts(client,library,project,goal_root,monkeypatch):
    from ref_lab import api
    job=goal_job(library,project,30)
    library.start_collection_attempt(job['id'],job['revision'],'projection-fixture',timeout=900)
    library.update_search_stage(job['id'],'projection-fixture','completed',
        {'counts':{'found':30,'usable_named':30,'goal_shas':['a'*64]},'stop_reason':'target_reached'},'synthetic receipt')
    def broken(*a,**kw):raise ValueError('synthetic damaged evidence')
    monkeypatch.setattr(api,'candidate_snapshot',broken)
    result=client.get('/api/jobs/'+job['id']).json()
    assert result['search_counts']['usable_named']==0
    assert result['search_counts']['goal_shas']==[]
    assert result['search_counts']['verification_error']=='evidence_unavailable'


def test_failed_run_downloads_still_enter_history_without_received_rows(tmp_path):
    from ref_lab.collection_history import collect_history_scope
    from conftest import library_db
    run=tmp_path/'.local/collection-runs/failed-job/current'
    row=_write_original(run,_textured((800,600),12,(90,100,120)))
    path=Path(row['original_path']);path=path.rename(path.with_name(row['asset_sha']+'.png'))
    (path.parent.parent/'received.json').write_text('[]','utf8')
    library_db(tmp_path/'data', jobs=[('failed-job','proj-a')])
    paths=set(collect_history_scope(tmp_path,tmp_path/'.local/current','proj-a').paths)
    assert path.resolve() in paths


def test_duplicate_alias_cannot_hide_corrupt_library_original(library,project,goal_root):
    from tests.conftest import image_bytes
    from ref_lab.db import encode
    first=library.assets.ingest(image_bytes(21),'a.png');second=library.assets.ingest(image_bytes(22),'b.png')
    with library.db.transaction() as con:
        for asset in (first,second):con.execute('INSERT INTO assets VALUES(?,?)',(asset['id'],encode(asset)))
        for index,asset in enumerate((first,second)):
            con.execute('INSERT INTO refs VALUES(?,?,?,?,?,?)',
                        (f'ref-corrupt-{index}', project['id'], asset['id'], 'keep', 'active', '{}'))
    library.assets.path(first).write_bytes(library.assets.path(second).read_bytes())
    with pytest.raises((service.Problem,ValueError),match='SHA|历史|完整'):
        goal_job(library,project,30)


@pytest.mark.parametrize('unavailable',[False,True])
def test_uncertain_tile_history_stays_pending_instead_of_confirmed_duplicate(tmp_path,unavailable):
    row=_write_original(tmp_path,_collage(2,1,tile=(800,600)))
    class History:
        def consider(self,path,**kwargs):
            if unavailable:raise OSError('synthetic history unavailable')
            return {'state':'needs_review','reason':'possible_crop_duplicate','duplicate_of':'a'*64}
    record=collage.process_original(tmp_path,row,history=History())
    assert all(c['status']=='history_pending' for c in record['children'])
    assert record['status']==collage.STATUS_NEEDS_MANUAL
    assert all(c['history_check']['state']=='needs_review' for c in record['children'])
    assert record['counts']['independent']==0


def test_uncertain_history_relation_blocks_review_without_claiming_duplicate(tmp_path):
    from tests.test_collection_stages import FakeReviewAgent,seed_search_rows
    task,rows=seed_search_rows(tmp_path,1)
    class History:
        def exclude(self,shas):pass
        def match(self,path):return {'state':'needs_review','reason':'possible_crop_duplicate'}
    agent=FakeReviewAgent()
    collector.review_candidates(task,agent,tmp_path,history=History())
    item=json.loads((tmp_path/'review-audit.json').read_text('utf8'))['items'][rows[0]['asset_sha']]
    assert item['status']=='blocked' and item['decision']=='REVIEW_BLOCKED'
    assert agent.review_calls==0


def test_damaged_historical_tile_records_cannot_silently_shrink_baseline(tmp_path):
    from ref_lab.collection_history import collect_history_scope
    from conftest import library_db
    run=tmp_path/'.local/collection-runs/history-job/current';run.mkdir(parents=True)
    (run/'received.json').write_text('[]','utf8')
    (run/'derived.json').write_bytes(b'{damaged history')
    library_db(tmp_path/'data', jobs=[('history-job','proj-a')])
    with pytest.raises(ValueError):collect_history_scope(tmp_path,tmp_path/'.local/current','proj-a')


def test_unreadable_historical_image_blocks_goal_instead_of_omitting_fingerprint(library,project,goal_root):
    prior=prior_collection_job(library,project)
    run=goal_root/'.local/collection-runs'/prior/'current';images=run/'images';images.mkdir(parents=True)
    raw=b'not an image';sha=hashlib.sha256(raw).hexdigest()
    (images/(sha+'.png')).write_bytes(raw)
    (run/'received.json').write_text('[]','utf8')
    with pytest.raises(service.Problem,match='历史图片指纹'):
        goal_job(library,project,30)


@pytest.mark.parametrize('old_tile',[False,True])
def test_old_goal_photos_remain_readable_as_history_without_current_admission(client,library,project,goal_root,monkeypatch,old_tile):
    from ref_lab import api
    from tests.conftest import image_bytes
    from ref_lab.db import encode
    asset=library.assets.ingest(image_bytes(33),'old.png');sha=asset['id']
    with library.db.transaction() as con:con.execute('INSERT INTO assets VALUES(?,?)',(sha,encode(asset)))
    job=goal_job(library,project,30)
    library.start_collection_attempt(job['id'],job['revision'],'legacy-fixture',timeout=900)
    library.update_search_stage(job['id'],'legacy-fixture','completed',
        {'counts':{'usable_named':1,'goal_shas':[sha]},'stop_reason':'target_reached'},'synthetic old report')
    item={'asset_sha':sha,'goal_qualified':False,'source':{},'goal_name_evidence':{},'photo_type':{},
          'original_url':'/historical-original.png'}
    monkeypatch.setattr(api,'candidate_snapshot',lambda *a,**kw:{'items':[] if old_tile else [item],'counts':{'usable_named':0}})
    response=client.get('/api/jobs/'+job['id']+'/goal-results')
    url=f'/api/assets/{sha}/original' if old_tile else '/historical-original.png'
    assert response.status_code==200 and url in response.text
    assert '历史准入记录' in response.text and '当前待复核' in response.text
    assert '0/30' in response.text
    assert client.get(f'/api/assets/{sha}/original').content==image_bytes(33)


def test_crop_with_local_overlay_is_uncertain_instead_of_cleared_as_new(tmp_path):
    from PIL import ImageDraw
    from ref_lab.collection_history import ImageHistory
    image=_textured((800,600),41,(70,90,120))
    source=tmp_path/'source.png';image.save(source)
    crop=image.crop((60,30,760,555)).resize((800,600))
    ImageDraw.Draw(crop).rectangle((695,555,790,590),fill=(255,255,255))
    variant=tmp_path/'overlay.jpg';crop.save(variant,quality=93)
    match=ImageHistory([source]).match(variant)
    assert match and match.get('state')=='needs_review'


def test_parallel_original_and_tile_admission_has_one_winner(tmp_path,monkeypatch):
    from ref_lab.collection_history import ImageHistory
    image=_textured((800,600),17,(70,100,140))
    a=tmp_path/'a.png';b=tmp_path/'b.jpg';image.save(a);image.save(b,quality=98)
    history=ImageHistory([]);real=history._match;barrier=threading.Barrier(2)
    def overlap(value):
        result=real(value)
        try:barrier.wait(timeout=.2)
        except threading.BrokenBarrierError:pass
        return result
    monkeypatch.setattr(history,'_match',overlap)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(history.consider,(a,b)))
    assert sum(result is None for result in results)==1


@pytest.mark.parametrize('expired',[False,True])
def test_goal_refines_exhausted_plan_inside_single_frozen_attempt(tmp_path,monkeypatch,expired):
    from tests.test_search_continue_recovery import Agent
    row=_write_original(tmp_path,_textured((800,600),23,(80,100,150)))
    offsets=[]
    def plans(project,plan,sources,*,intent_offset=0):
        offsets.append(intent_offset)
        return [{'source':'xiaohongshu','query':'角色甲 cos '+str(intent_offset),
                 'language':'zh','used_name':'角色甲','name_source':'project_character'}]
    monkeypatch.setattr(collector,'query_steps',plans)
    class Browser:
        def start(self):pass
        def close(self):pass
        def search(self,step):
            from urllib.parse import quote
            return {'url':'https://example.org/?keyword='+quote(step['query']),'search':step['query'],
                    'cards':[] if step['query'].endswith('0') else
                    [{'page':'https://example.org/fresh','text':'角色甲 cos 正片'}]}
        def receive(self,card,step):return [row]
    job={'id':'feedback-fixture','goal_id':'synthetic-controller-only',
         'project_snapshot':{'character':'角色甲','work':'','costume':'','brief':''},
         'target_count':1,'notes':'','preferred_sources':['xiaohongshu'],
         'search_timeout_seconds':900,'active_attempt_id':'same-attempt'}
    agent=Agent()
    if expired:agent.deadline=time.monotonic()-1
    summary,_=collector.collect(job,agent,Browser(),tmp_path,search_only=True)
    assert summary['counts']['found']==(0 if expired else 1)
    if expired:
        assert offsets==[0] and summary['stop_reason']=='time_budget_exhausted'
    else:
        assert 1 in offsets
    assert job['active_attempt_id']=='same-attempt'
    assert job['search_timeout_seconds']==900
    assert summary['query_budget']==collector.MAX_GOAL_QUERIES
    assert summary['termination_reason']


def test_goal_reaches_new_note_image_after_three_historical_images(tmp_path):
    from tests.test_search_continue_recovery import Agent
    from ref_lab.collection_history import ImageHistory
    rows=[_write_original(tmp_path,_textured((800,600),i,(40+i*20,90,150)),name=f'frame-{i}.png')
          for i in range(4)]
    class Browser:
        def start(self):pass
        def close(self):pass
        def search(self,step):
            from urllib.parse import quote
            return {'url':'https://example.org/?keyword='+quote(step['query']),'search':step['query'],
                    'cards':[{'page':'https://example.org/gallery','text':'角色甲 cos 正片'}]}
        def receive(self,card,step):return rows[:getattr(self,'note_image_limit',3)]
    job={'id':'note-quota-fixture','goal_id':'synthetic-controller-only',
         'project_snapshot':{'character':'角色甲','work':'','costume':'','brief':''},
         'target_count':1,'notes':'','preferred_sources':['xiaohongshu']}
    history=ImageHistory([Path(r['original_path']) for r in rows[:3]])
    summary,_=collector.collect(job,Agent(),Browser(),tmp_path,search_only=True,history=history)
    assert summary['counts']['found']==1 and summary['counts']['duplicates']==3


@pytest.mark.parametrize('as_tile',[False,True])
def test_platform_ai_warning_blocks_count_even_with_native_photo_receipt(tmp_path,as_tile):
    from tests.photo_type_fixture import synthetic_type
    from ref_lab.collection_counts import compute
    row=_write_original(tmp_path,_textured((800,600),88,(70,90,110)))
    row.update(relevance={'tier':'target_named'},source_text='可能含AI生成内容\n1/4\n角色甲 cos 摄影')
    record=collage.process_original(tmp_path,row)
    synthetic_type(tmp_path,row)
    if as_tile:
        child=tmp_path/'derived'/('a'*64)/Path(row['original_path']).name
        child.parent.mkdir(parents=True);child.write_bytes(Path(row['original_path']).read_bytes())
        record.update(status=collage.STATUS_SPLIT_OK,children=[{'parent_sha':row['asset_sha'],'child_sha':row['asset_sha'],'path':str(child),'status':collage.VALID}])
    result=compute(tmp_path,[row],{row['asset_sha']:record})
    assert result['usable_named']==result['usable_independent']==0
    assert result['source_pending']==1 and result['awaiting_manual']==1


def test_platform_ai_warning_does_not_dispatch_type_model(tmp_path):
    row=_write_original(tmp_path,_textured((800,600),89,(70,90,110)))
    row['source_text']='可能含AI生成内容\n作者正文';(tmp_path/'received.json').write_text(json.dumps([row]),'utf8')
    class Analyzer:
        producer_name='synthetic'
        def classify(self,*args):pytest.fail('Unresolved platform warning cannot spend a type-only model attempt')
    worker=photo_types.PhotoTypeWorker(tmp_path,analyzer=Analyzer())
    try:worker._process({'parent_sha':row['asset_sha'],'status':collage.STATUS_NO_COLLAGE})
    finally:worker.close(timeout=0)
    assert not (tmp_path/'photo-types.json').exists()


def test_platform_warning_is_separate_from_name_and_survives_later_discovery():
    from ref_lab.search_relevance import associate_detail,is_confirmed,source_warnings
    row={'source_text':'可能含AI生成内容\n作者甲\n角色甲 cosplay',
         'author_detail':{'title':'角色甲 cosplay','description':'摄影 作者甲'}}
    result=associate_detail({},row,names=['角色甲'])
    assert is_confirmed({'relevance':result})
    assert result['source_warnings']==['可能含AI生成内容']
    assert source_warnings({'source_text':'新来源标题','relevance':{'tier':'target_named'},
                            'discovery_evidence_history':[result]})==['可能含AI生成内容']
    assert source_warnings({'source_text':'讨论AI生成内容\n不是AI生成\n可能含AI生成内容的提示是否准确？'})==[]


def test_later_parent_warning_blocks_an_already_seen_shared_tile(tmp_path):
    from tests.photo_type_fixture import synthetic_type
    from ref_lab.collection_counts import compute
    a=_write_original(tmp_path,_textured((800,600),90,(70,90,110)),name='a.png')
    b=_write_original(tmp_path,_textured((800,600),91,(70,90,110)),name='b.png')
    for row in (a,b):row['relevance']={'tier':'target_named'}
    b['source_text']='可能含AI生成内容\n作者正文'
    child=tmp_path/'derived'/a['asset_sha']/Path(a['original_path']).name
    child.parent.mkdir(parents=True);child.write_bytes(Path(a['original_path']).read_bytes())
    records={}
    for row,status in [(a,collage.VALID),(b,collage.DUPLICATE_RUN)]:
        record=collage.process_original(tmp_path,row)
        record.update(status=collage.STATUS_SPLIT_OK,children=[{'parent_sha':row['asset_sha'],'child_sha':a['asset_sha'],'path':str(child),'status':status}])
        records[row['asset_sha']]=record
    synthetic_type(tmp_path,a)
    counts=compute(tmp_path,[a,b],records)
    assert counts['source_pending']==1 and counts['usable_named']==0
