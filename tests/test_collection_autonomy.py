"""Controller/dedup regressions only; synthetic images do not prove role accuracy."""
import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from ref_lab.collection_history import ImageHistory, collect_history_scope
from ref_lab.verified_collection import AgentCallFailed
from conftest import library_db
from tools import collect_verified as worker
from test_verified_collection import FakeAgent, FakeBrowser, job


def library_asset(assets_root, source):
    """Place bytes into a content-addressed asset store; returns the keeper path."""
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    target = Path(assets_root) / sha[:2] / sha / 'original.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target.resolve()


def photo(folder, seed, name=None):
    folder.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(180,240),'white');draw=ImageDraw.Draw(image);rng=random.Random(seed)
    for _ in range(40):
        x,y=rng.randrange(160),rng.randrange(220)
        draw.rectangle((x,y,x+20,y+20),fill=tuple(rng.randrange(256) for _ in range(3)))
    path=folder/(name or f'{seed}.png');image.save(path)
    return path


def row(path):
    return {'asset_sha':hashlib.sha256(path.read_bytes()).hexdigest(),'original_path':str(path),
            'page_url':'https://example.org/post/'+path.stem,'image_url':'https://example.org/'+path.name}


def test_reencoded_and_resized_previous_photo_cannot_be_counted_as_new(tmp_path):
    old=photo(tmp_path/'old',1);history=ImageHistory([old])
    changed=tmp_path/'changed.jpg'
    with Image.open(old) as im:im.resize((360,480)).save(changed,quality=86)
    match=history.consider(changed)
    assert match and match['duplicate_of']==row(old)['asset_sha'] and match['reason']=='near_duplicate'
    assert history.consider(old)['reason']=='same_bytes'
    assert history.consider(photo(tmp_path,2)) is None


def test_within_run_reencoded_duplicate_is_excluded_too(tmp_path):
    path=photo(tmp_path,4);history=ImageHistory([])
    assert history.consider(path) is None
    other=tmp_path/'other.jpg'
    with Image.open(path) as im:im.save(other,quality=90)
    assert history.consider(other)['duplicate_of']==row(path)['asset_sha']


def test_historical_scan_includes_rejected_received_and_library_but_not_current_or_symlinks(tmp_path):
    job_id = 'job-old'
    old = photo(tmp_path / '.local' / 'collection-runs' / job_id / 'current' / 'images', 3)
    (old.parent.parent / 'received.json').write_text(json.dumps({'candidates': [row(old)]}), encoding='utf8')
    staged = photo(tmp_path / 'staging', 5)
    original = library_asset(tmp_path / 'data' / 'assets', staged)
    library_db(tmp_path / 'data', jobs=[(job_id, 'proj-a')],
               refs=[('proj-a', hashlib.sha256(staged.read_bytes()).hexdigest())])
    current_job = 'job-current'
    current = photo(tmp_path / '.local' / 'collection-runs' / current_job / 'current' / 'images', 6)
    (current.parent.parent / 'received.json').write_text(json.dumps([row(current)]), encoding='utf8')
    library_db(tmp_path / 'data', jobs=[(current_job, 'proj-a')])
    paths = set(collect_history_scope(tmp_path, current.parent.parent, 'proj-a').paths)
    assert old.resolve() in paths and original in paths and current.resolve() not in paths


def test_parent_read_only_history_overrides_child_scratch_directory(tmp_path, monkeypatch):
    staged = photo(tmp_path / 'staging', 7)
    original = library_asset(tmp_path / 'library' / 'assets', staged)
    library_db(tmp_path / 'library',
               refs=[('proj-a', hashlib.sha256(staged.read_bytes()).hexdigest())])
    monkeypatch.setenv('LAB_DATA_DIR', str(tmp_path / 'adapter-scratch'))
    monkeypatch.setenv('LAB_COLLECTION_HISTORY_DIR', str(tmp_path / 'library' / 'assets'))
    assert original in set(collect_history_scope(tmp_path, tmp_path / '.local' / 'current', 'proj-a').paths)


def test_history_checks_original_hash_and_rejects_external_received_path(tmp_path):
    import pytest
    run = tmp_path / '.local' / 'collection-runs' / 'job-old' / 'current'
    path = photo(run / 'images', 8)
    record = row(path);record['asset_sha'] = '0' * 64
    (run / 'received.json').write_text(json.dumps([record]), encoding='utf8')
    library_db(tmp_path / 'data', jobs=[('job-old', 'proj-a')])
    with pytest.raises(ValueError, match='SHA changed'):
        collect_history_scope(tmp_path, tmp_path / '.local' / 'current', 'proj-a')
    external = photo(tmp_path / 'outside', 9)
    (run / 'received.json').write_text(json.dumps([row(external)]), encoding='utf8')
    with pytest.raises(ValueError, match='boundary'):
        collect_history_scope(tmp_path, tmp_path / '.local' / 'current', 'proj-a')


def test_one_request_moves_beyond_duplicate_first_screen_without_external_prompt(tmp_path):
    old=photo(tmp_path/'images',10);new=photo(tmp_path/'images',11)
    class More(FakeBrowser):
        windows=0
        def search(self,step):
            snapshot=super().search(step);snapshot['cards']=[{'page':'https://example.org/old'}];return snapshot
        def more(self,step):
            self.windows+=1;snapshot=super().search(step)
            snapshot['cards']=[{'page':'https://example.org/new'}];return snapshot
        def receive(self,card,step):return [row(old if card['page'].endswith('/old') else new)]
    browser=More([]);agent=FakeAgent()
    manifest,images=worker.collect({**job(),'target_count':1},agent,browser,tmp_path,history=ImageHistory([old]))
    assert browser.windows==1 and agent.calls==1 and len(images)==len(manifest['candidates'])==1
    assert manifest['candidates'][0]['id']=='verified-'+row(new)['asset_sha'][:20]
    progress=json.loads((tmp_path/'progress.json').read_text('utf8'))
    assert progress['stop_reason']=='soft_target_reached' and progress['duplicates']==1
    assert progress['phase']=='finished'


def test_fatal_cli_failure_stops_whole_request_honestly_without_more_search(tmp_path):
    a=photo(tmp_path/'images',20);b=photo(tmp_path/'images',21);agent=FakeAgent()
    def fail(*args):raise AgentCallFailed('authentication',fatal=True)
    agent.review=fail;browser=FakeBrowser([row(a),row(b)])
    manifest,images=worker.collect(job(),agent,browser,tmp_path,history=ImageHistory([]))
    assert browser.sources==['xiaohongshu'] and not images and not manifest['candidates']
    assert manifest['execution_report']['status']=='blocked'
    progress=json.loads((tmp_path/'progress.json').read_text('utf8'))
    assert progress['stop_reason']=='unrecoverable_agent_failure' and progress['received']==1
    assert browser.closed


def test_saturated_searches_stop_with_finite_windows_and_no_unverified_filler(tmp_path):
    old=photo(tmp_path/'images',31)
    class Stale(FakeBrowser):
        windows=0
        def more(self,step):self.windows+=1;return super().search(step)
    browser=Stale([row(old)]);agent=FakeAgent()
    manifest,images=worker.collect(job(),agent,browser,tmp_path,history=ImageHistory([old]))
    assert not images and not manifest['candidates'] and agent.calls==0
    assert browser.windows<=worker.MAX_QUERIES*(worker.MAX_WINDOWS-1)
    progress=json.loads((tmp_path/'progress.json').read_text('utf8'))
    assert progress['stop_reason']=='search_plan_exhausted' and progress['phase']=='finished'


def test_reference_phase_does_not_hide_permanent_model_failure(tmp_path,monkeypatch):
    import pytest
    from ref_lab.automatic_references import ReferenceResearch
    from ref_lab.verified_collection import NamePlan
    research=ReferenceResearch(FakeAgent(),tmp_path,job()['project_snapshot'],NamePlan(names=['测试角色甲']))
    calls=[]
    def fail(query):calls.append(query);raise AgentCallFailed('authentication',fatal=True)
    monkeypatch.setattr(research,'_search',fail)
    with pytest.raises(AgentCallFailed):research.prepare()
    assert len(calls)==1


def test_browser_command_leaves_recovery_to_controller_without_replay(tmp_path,monkeypatch):
    import pytest
    from types import SimpleNamespace
    calls=[]
    def command(args,**kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=1 if len(calls)%2 else 0,stdout='ok',stderr='')
    monkeypatch.setattr(worker.subprocess,'run',command);monkeypatch.setattr(worker.time,'sleep',lambda _:None)
    browser=worker.Browser(tmp_path);browser.bsk='fixture-bsk'
    with pytest.raises(worker.BrowserInfrastructureError):browser.command('navigate','https://example.org')
    assert len(calls)==1
    assert browser.command('navigate','https://example.org')=='ok' and len(calls)==2
    with pytest.raises(ValueError):browser.command('click','@e1')
    assert len(calls)==3


def test_gallery_contains_exact_agent_candidates_and_original_bytes(tmp_path):
    path=photo(tmp_path/'images',50);agent=FakeAgent()
    manifest,images=worker.collect({**job(),'target_count':1},agent,FakeBrowser([row(path)]),tmp_path)
    worker.render_result(tmp_path,manifest,images)
    page=(tmp_path/'public/index.html').read_text('utf8')
    assert page.count('<img ')==1 and 'form' not in page and 'AGY' in page
    assert (tmp_path/'public'/path.name).read_bytes()==path.read_bytes()


def test_model_does_not_receive_library_history_path(tmp_path,monkeypatch):
    from ref_lab import verified_collection as vision
    from test_collection_resume import fake_processes,terminal
    env={'LAB_COLLECTION_HISTORY_DIR':'private-library-path'}
    fake_processes(monkeypatch,[(0,terminal('SUCCESS',{'names':['Example Person']}),'')])
    monkeypatch.setattr(vision,'antigravity_environment',lambda:env)
    vision.AntigravityCollectionAgent(tmp_path).run('Synthetic plan only',vision.NamePlan)
    assert 'LAB_COLLECTION_HISTORY_DIR' not in env


def test_permanent_supplement_failure_preserves_first_prediction_and_stops(tmp_path,monkeypatch):
    import pytest
    from ref_lab.verified_collection import AntigravityCollectionAgent
    from test_verified_collection import result
    agent=AntigravityCollectionAgent(tmp_path);path=photo(tmp_path/'images',70)
    first=result(path,identity='uncertain');agent.references=[]
    class Research:
        references=[]
        def supplement(self,hint):raise AgentCallFailed('authentication',fatal=True)
    agent.research=Research();monkeypatch.setattr(agent,'_review_once',lambda *args:first)
    with pytest.raises(AgentCallFailed):agent.review(path,job()['project_snapshot'])
    trace=json.loads((tmp_path/('candidate-trace-'+first.asset_sha+'.json')).read_text('utf8'))
    assert trace['model_predictions']==[first.model_dump()] and 'authentication' in trace['supplement_error']
