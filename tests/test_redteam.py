"""Counterexamples against 6218a5f; isolated pixels are not a vision benchmark."""
import io
import json
from copy import deepcopy

import pytest
from PIL import Image

from conftest import add_reference, image_bytes
from ref_lab.cli import backup, doctor
from ref_lab.db import encode
from ref_lab.identity import build_identity_context
from ref_lab.models import CandidateInput
from ref_lab.preflight import detect_modality, evaluate_identity, run_candidate_preflight


def choose(client, ref, decision, **extra):
    result = client.patch('/api/references/'+ref['id'], json={
        'expected_revision':ref['revision'], 'decision':decision, **extra})
    assert result.status_code == 200, result.text
    return result.json()


def finish(client, project):
    session = client.get(f"/api/projects/{project['id']}/screening-sessions/current").json()
    response = client.post('/api/screening-sessions/'+session['id']+'/finish')
    assert response.status_code == 200, response.text
    return session, response.json()


def confirm(client, session, summary):
    return client.post('/api/screening-sessions/'+session['id']+'/confirm', json={
        'accepted_hypotheses':[h['text'] for h in summary['hypotheses']], 'apply_to_profile':True})


@pytest.mark.parametrize('change', ['undo', 'replace', 'project'])
def test_summary_cannot_confirm_stale_owner_state(client, project, library, change):
    ref = choose(client, add_reference(client, project, 61), 'reject', is_aesthetic_negative=True)
    session, summary = finish(client, project)
    before = client.get('/api/profile').json()
    if change == 'undo':
        response = client.post('/api/references/'+ref['id']+'/restore',json={'expected_revision':ref['revision']})
    elif change == 'replace':
        response = client.post('/api/references/'+ref['id']+'/replace',
            data={'expected_revision':str(ref['revision'])},files={'file':('new.png',image_bytes(62),'image/png')})
    else:
        response = client.put('/api/projects/'+project['id'],json={
            'expected_revision':project['revision'],'character':project['character'],'brief':'changed shooting context'})
    assert response.status_code == 200, response.text
    result = confirm(client, session, summary)
    assert result.status_code == 409, result.text
    assert client.get('/api/profile').json() == before


def test_repeated_keep_across_sessions_is_one_reusable_project_sample(client, project):
    ref = add_reference(client, project, 63)
    for iteration in range(2):
        ref = choose(client, ref, 'keep', **({'preference':'only project use'} if iteration==0 else {}))
        session, summary = finish(client, project)
        assert confirm(client, session, summary).status_code == 200
    profile = client.get('/api/profile').json()
    assert len(profile['project_use_exemplars']) == 1
    assert profile['project_use_exemplars'][0]['preference']=='only project use'
    assert profile['provenance']['total_feedback_count'] == 1
    assert len(profile['provenance']['source_session_ids']) == 2  # Raw confirmation history survives.


def test_editing_note_cannot_confirm_an_imported_choice(client, project, library):
    asset = library.ingest_asset(image_bytes(64),'import.png')
    ref = library.add_candidate(project['id'],CandidateInput(asset_sha=asset['id']),decision='keep',actor='import')['reference']
    assert client.patch('/api/references/'+ref['id'],json={
        'expected_revision':ref['revision'],'preference':'I wrote a note, not K'}).status_code == 200
    _, summary = finish(client, project)
    assert summary['stats']['keep']==0
    assert not any(h['category']=='keep_reference' for h in summary['hypotheses'])


def test_metadata_does_not_become_visual_modality_or_identity():
    image = Image.open(io.BytesIO(image_bytes(65)))
    neutral = {'title':'ordinary','source':{}}
    claimed = {'title':'OFFICIAL_09 render 柔光 布光图','source':{'page_url':'https://example.com/model'}}
    assert detect_modality(image,neutral) == detect_modality(image,claimed)
    # A solid red rectangle is not a person, let alone a verified character.
    stream = io.BytesIO(); Image.new('RGB',(300,400),(180,40,40)).save(stream,'PNG')
    result = evaluate_identity(stream.getvalue(),{'title':'有马加奈','source':{}},build_identity_context('有马加奈'))
    assert result['prediction']=='uncertain'
    pf = run_candidate_preflight(image_bytes(65),claimed,None,'a'*64,'p')
    assert pf['content_type']=='unknown' and not pf['visual_evidence']
    assert pf['discovery_context']['origin']=='discovery_metadata'


def test_legacy_local_preflight_is_not_republished_as_visual_evidence(client, project, library):
    ref = add_reference(client,project,66)
    with library.db.transaction() as con:
        stored = json.loads(con.execute('SELECT data FROM refs WHERE id=?',(ref['id'],)).fetchone()[0])
        stored['preflight']={'asset_sha':ref['asset_sha'],'producer':'vision-preflight-gate',
            'content_type':'real_person_cosplay','identity_prediction':'match','confidence':'high',
            'visual_evidence':['具备光学镜头实拍特征与真实光影景深'],'status':'passed'}
        stored['preflight_status']='passed'
        con.execute('UPDATE refs SET data=? WHERE id=?',(encode(stored),ref['id']))
    shown = client.get('/api/references/'+ref['id']).json()
    assert shown['recommendation']['evidence']['preflight']['items']==[]
    assert shown['preflight']['content_type']=='unknown'
    assert shown['preflight']['identity_prediction']=='uncertain'
    with library.db.read() as con:
        assert json.loads(con.execute('SELECT data FROM refs WHERE id=?',(ref['id'],)).fetchone()[0])==stored


def test_doctor_and_backup_do_not_accept_corrupt_display_assets(client, project, library, tmp_path):
    ref = add_reference(client,project,67)
    library.assets.path(ref['asset'],'preview').write_bytes(b'not a jpeg')
    assert library.assets.verify(ref['asset'])  # Original SHA is still valid.
    assert not doctor(library)['ok']
    with pytest.raises(ValueError,match='derivative'):
        backup(library,tmp_path/'bad.zip')
    assert not (tmp_path/'bad.zip').exists()
    assert doctor(library,repair_derived=True)['ok']
    with Image.open(library.assets.path(ref['asset'],'preview')) as image:
        image.load()


def test_withdrawn_saved_negative_is_history_not_current_learning(client, project):
    ref = choose(client, add_reference(client,project,68),'reject',is_aesthetic_negative=True)
    session, summary = finish(client,project)
    assert confirm(client,session,summary).status_code == 200
    assert client.get('/api/profile').json()['explicit_aesthetic_negatives'][0]['learning_eligible'] is True
    assert client.post('/api/references/'+ref['id']+'/restore',json={'expected_revision':ref['revision']}).status_code==200
    profile = client.get('/api/profile').json()
    assert len(profile['explicit_aesthetic_negatives'])==1  # No silent history deletion.
    assert profile['explicit_aesthetic_negatives'][0]['learning_eligible'] is False


def test_removed_interest_invalidates_summary_without_touching_project_use(client, project):
    ref = choose(client,add_reference(client,project,69),'keep')
    # Simultaneous project use and global interest is valid.
    ref = choose(client,ref,'keep',lane='inspiration')
    session, summary = finish(client,project)
    item = client.get('/api/inspirations/'+ref['inspiration_id']).json()
    assert client.patch('/api/inspirations/'+item['id'],json={'expected_revision':item['revision'],'active':False}).status_code==200
    result = confirm(client,session,summary)
    assert result.status_code==409, result.text


def test_shared_pixels_keep_distinct_project_judgments(client, project):
    first = choose(client,add_reference(client,project,71),'keep',preference='project A movement')
    session, summary = finish(client,project)
    assert confirm(client,session,summary).status_code==200
    other = client.post('/api/projects',json={'character':'another character'}).json()
    second = client.post(f"/api/projects/{other['id']}/references",json={'asset_sha':first['asset_sha']}).json()['reference']
    second = choose(client,second,'keep',preference='project B composition')
    session, summary = finish(client,other)
    assert confirm(client,session,summary).status_code==200
    items = client.get('/api/profile').json()['project_use_exemplars']
    assert len(items)==2 and {i['preference'] for i in items}=={'project A movement','project B composition'}
    assert all(i['learning_eligible'] for i in items)


def test_valid_but_swapped_preview_is_not_original_evidence(client,project,library,tmp_path):
    ref = add_reference(client,project,72)
    other = add_reference(client,project,73)
    library.assets.path(ref['asset'],'preview').write_bytes(library.assets.path(other['asset'],'preview').read_bytes())
    with Image.open(library.assets.path(ref['asset'],'preview')) as image:
        image.load()  # It decodes, has expected dimensions, and still depicts wrong bytes.
    assert library.assets.verify(ref['asset'])
    assert not doctor(library)['ok']
    with pytest.raises(ValueError,match='derivative'):
        backup(library,tmp_path/'swapped.zip')


def test_choose_replace_choose_only_confirms_latest_image(client,project):
    ref = choose(client,add_reference(client,project,75),'keep')
    changed = client.post('/api/references/'+ref['id']+'/replace',
        data={'expected_revision':str(ref['revision'])},files={'file':('new.png',image_bytes(76),'image/png')}).json()
    changed = choose(client,changed,'keep')
    session,summary = finish(client,project)
    assert len(session['actions'])==2 and summary['stats']['keep']==1
    result = confirm(client,session,summary)
    assert result.status_code==200,result.text
    samples = client.get('/api/profile').json()['project_use_exemplars']
    assert [s['asset_sha'] for s in samples]==[changed['asset_sha']]


def test_stale_summary_can_be_explicitly_discarded(client,project):
    ref = choose(client,add_reference(client,project,77),'keep')
    session,summary = finish(client,project)
    choose(client,ref,'maybe')
    result = client.post('/api/screening-sessions/'+session['id']+'/confirm',json={
        'accepted_hypotheses':[], 'apply_to_profile':False})
    assert result.status_code==200,result.text
    assert result.json()['status']=='completed_skipped_learning'


def test_apply_cleanup_preserves_confirmed_history_shared_uses_and_sources(client,project,library):
    from ref_lab.recycle import cleanup
    ref = choose(client,add_reference(client,project,78),'keep')
    session,summary = finish(client,project)
    assert confirm(client,session,summary).status_code==200
    other = client.post('/api/projects',json={'character':'shared use'}).json()
    shared = client.post(f"/api/projects/{other['id']}/references",json={
        'asset_sha':ref['asset_sha'],'import_key':'protected-shared-alias'}).json()['reference']
    ref = choose(client,ref,'reject')
    shared = choose(client,shared,'reject')
    unprotected = choose(client,add_reference(client,project,79),'reject')
    library.rollback_profile(1)  # Only historical confirmation now protects it.
    with library.db.transaction() as con:
        for item in (ref,shared,unprotected):
            stored = json.loads(con.execute('SELECT data FROM refs WHERE id=?',(item['id'],)).fetchone()[0])
            stored['rejected_at']='2020-01-01T00:00:00+00:00'
            con.execute('UPDATE refs SET data=? WHERE id=?',(encode(stored),item['id']))
        counts = {t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('refs','aliases','discoveries','preflights')}
    result = cleanup(library,days=30,apply=True)
    assert result['purged']==[unprotected['asset_sha']]
    assert library.assets.verify(ref['asset'])
    with library.db.read() as con:
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
        assert all(con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]==n for t,n in counts.items())


@pytest.mark.parametrize('saved', [False,True])
def test_raw_writer_cannot_keep_a_withdrawn_negative_current_without_revision(client,project,library,saved):
    ref = choose(client,add_reference(client,project,80),'reject',is_aesthetic_negative=True)
    session,summary = finish(client,project)
    if saved:
        assert confirm(client,session,summary).status_code==200
    with library.db.transaction() as con:
        stored = json.loads(con.execute('SELECT data FROM refs WHERE id=?',(ref['id'],)).fetchone()[0])
        stored.update(decision='keep',is_aesthetic_negative=False)
        con.execute("UPDATE refs SET decision='keep',data=? WHERE id=?",(encode(stored),ref['id']))
    assert library.reference(ref['id'])['revision']==ref['revision']
    if saved:
        assert client.get('/api/profile').json()['explicit_aesthetic_negatives'][0]['learning_eligible'] is False
    else:
        assert confirm(client,session,summary).status_code==409
