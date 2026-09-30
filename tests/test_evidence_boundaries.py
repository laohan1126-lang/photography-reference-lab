from copy import deepcopy
from fastapi.testclient import TestClient
from ref_lab.api import create_app
from ref_lab.ranking import score_and_rank_candidates
from conftest import add_reference, review_data


def test_search_text_cannot_change_photographic_evidence_or_preference():
    candidate = {'id':'r', 'asset_sha':'a', 'asset':{'id':'a','width':800,'height':1200},
                 'title':'普通来源标题', 'source':{}, 'preflight':{}}
    enriched = deepcopy(candidate)
    enriched['title'] = '低机位 动态 轮廓光 柔光 全身'
    enriched['source']['search_query'] = 'low angle rim backlight dynamic'
    first, second = [score_and_rank_candidates([c], {'dimensions':{'lighting':{'rim_light':1}}})[0]['recommendation']
                     for c in (candidate, enriched)]
    assert first['photographic_points'] == second['photographic_points']
    assert first['preference_points'] == second['preference_points'] == []
    assert first['preference_score'] is None
    assert first['exploration_score'] is None


def test_runtime_path_and_persistent_maintenance(client, settings):
    info = client.get('/api/runtime').json()
    assert info['database'] == str((settings.data_dir/'library.sqlite3').resolve())
    assert not info['maintenance']
    with TestClient(create_app(settings)) as locked:
        assert locked.get('/api/runtime').status_code == 401
        assert locked.post('/api/maintenance',json={'enabled':True}).status_code == 401
    assert client.post('/api/maintenance',json={'enabled':True}).status_code == 200
    with TestClient(create_app(settings)) as restarted:
        from conftest import TOKEN
        restarted.headers['Authorization']='Bearer '+TOKEN
        assert restarted.get('/api/runtime').json()['maintenance']
        assert restarted.post('/api/projects',json={'character':'blocked'}).status_code == 503
        assert restarted.get('/api/projects').json() == []
        assert restarted.get('/api/profile').status_code == 503
        assert restarted.get('/api/projects/unknown/screening-sessions/current').status_code == 503
    assert client.post('/api/maintenance',json={'enabled':False}).status_code == 200
    assert client.post('/api/projects',json={'character':'allowed'}).status_code == 201


def test_api_curation_is_durable_without_keyword_weight_learning(client, project, library):
    refs = [add_reference(client, project, i+200) for i in range(3)]
    before = client.get('/api/profile').json()
    for idx, ref in enumerate(refs):
        body = {'expected_revision': ref['revision'], 'decision':'reject', 'rejection_reason':'错角色，背景杂乱'}
        if idx == 1:
            body.update(is_aesthetic_negative=True, rejection_reason='我不喜欢这种光影')
        if idx == 2:
            body.update(decision='keep', preference='低机位轮廓光只是我的喜好记录')
        response = client.patch('/api/references/'+ref['id'],json=body)
        assert response.status_code == 200, response.text
        refs[idx] = response.json()
    # A repeated click remains raw history but cannot inflate exemplar count.
    assert client.patch('/api/references/'+refs[2]['id'],json={'expected_revision':refs[2]['revision'],'decision':'keep'}).status_code == 200
    session = client.get(f"/api/projects/{project['id']}/screening-sessions/current").json()
    assert len(session['actions']) == 4
    assert all(a['origin']=='human_curation' for a in session['actions'])
    summary = client.post('/api/screening-sessions/'+session['id']+'/finish').json()
    assert summary['stats']['viewed'] == 3
    negatives = next(h for h in summary['hypotheses'] if h['category']=='aesthetic_negative')
    assert negatives['evidence_count'] == 1
    assert negatives['evidence'][0]['asset_sha'] == refs[1]['asset_sha']
    confirm = {'accepted_hypotheses':[h['text'] for h in summary['hypotheses']], 'apply_to_profile':True}
    learned = client.post('/api/screening-sessions/'+session['id']+'/confirm',json=confirm).json()
    assert learned['status']=='completed_feedback_saved'
    profile = client.get('/api/profile').json()
    assert profile['dimensions']==before['dimensions']
    assert len(profile['explicit_aesthetic_negatives'])==1
    assert profile['explicit_aesthetic_negatives'][0]['asset_sha']==refs[1]['asset_sha']
    assert profile['project_use_exemplars'][0]['session_id']==session['id']
    assert profile['project_use_exemplars'][0]['preference']=='低机位轮廓光只是我的喜好记录'
    again = client.post('/api/screening-sessions/'+session['id']+'/confirm',json=confirm).json()
    assert profile['positive_exemplars']==[]
    assert profile['project_use_exemplars'][0]['project_context']['character']==project['character']
    assert again['idempotent']
    assert client.get('/api/profile').json()['version']==profile['version']
    confirm['accepted_hypotheses']=['搜索词不能成为这个会话的总结']
    assert client.post('/api/screening-sessions/'+session['id']+'/confirm',json=confirm).status_code==422


def test_review_origins_stale_hash_and_metadata_remain_separate(client, project):
    ref = add_reference(client,project,200,title='轮廓光 低机位 动态')
    if ref.get('preflight_filtered'):
        ref = client.post('/api/references/'+ref['id']+'/restore-preflight', json={'expected_revision':ref['revision']}).json()
    listed = client.get(f"/api/projects/{project['id']}/references?focus_id={ref['id']}").json()['items'][0]
    e = listed['recommendation']['evidence']
    assert e['visual_observations']['items']==[]
    assert e['discovery_context']['learning_eligible'] is False
    saved = client.post('/api/references/'+ref['id']+'/review',json={'expected_revision':ref['revision'],'review':review_data(ref['asset_sha'])}).json()
    assert saved['recommendation']['evidence']['visual_observations']['origin']=='human_visual_review'
    ai = deepcopy(saved); ai['review_actor']='ai'; ai['review_producer']='test-agent'
    e = score_and_rank_candidates([ai])[0]['recommendation']['evidence']
    assert e['visual_observations']['origin']=='ai_visual_inference'
    ai['asset_sha']='changed'
    e = score_and_rank_candidates([ai])[0]['recommendation']['evidence']
    assert not e['visual_observations']['items'] and not e['file_measurements']
    assert not e['preflight']['items']


def test_reason_report_has_no_skill_sync_or_ai_manifest_feedback(client,project,library):
    ref=add_reference(client,project,220)
    client.patch('/api/references/'+ref['id'],json={'expected_revision':ref['revision'],'decision':'reject','rejection_reason':'光线质量不足'})
    inspections=library.settings.data_dir/'inspections'/'ai-experiment';inspections.mkdir(parents=True)
    (inspections/'manifest.json').write_text('[{"verdict":"DROPPED","verdict_desc":"负向排除AI假图"}]',encoding='utf-8')
    before=client.get('/api/profile').json()
    result=client.post('/api/skills/curator/refine').json()
    assert result['total_reasons_collected']==1
    assert result['skill_synced'] is False and result['profile_updated'] is False
    case=result['categories'][0]['cases'][0]
    assert case['origin']=='human_rejection_reason' and not case['learning_eligible']
    assert case['reference_id']==ref['id']
    assert client.get('/api/profile').json()==before


def test_confirmed_negative_asset_survives_cleanup_and_profile_rollback(client,project,library):
    from ref_lab.db import encode
    from ref_lab.recycle import cleanup
    ref=add_reference(client,project,230)
    client.patch('/api/references/'+ref['id'],json={'expected_revision':ref['revision'],'decision':'reject',
                 'rejection_reason':'明确审美不喜欢','is_aesthetic_negative':True})
    session=library.current_screening_session(project['id'])
    summary=library.finish_screening_session(session['id'])
    library.confirm_screening_summary(session['id'],[summary['hypotheses'][0]['text']],True)
    library.rollback_profile(1)
    with library.db.transaction() as con:
        import json
        stored=json.loads(con.execute('SELECT data FROM refs WHERE id=?',(ref['id'],)).fetchone()[0])
        stored['rejected_at']='2020-01-01T00:00:00+00:00'
        con.execute('UPDATE refs SET data=? WHERE id=?',(encode(stored),ref['id']))
    assert not cleanup(library,days=30)['eligible']
    assert library.assets.verify(library.asset(ref['asset_sha']))


def test_restoring_rejection_withdraws_current_negative_summary(client,project,library):
    ref=add_reference(client,project,240)
    rejected=client.patch('/api/references/'+ref['id'],json={'expected_revision':ref['revision'],
        'decision':'reject','rejection_reason':'暂时不喜欢','is_aesthetic_negative':True}).json()
    restored=client.post('/api/references/'+ref['id']+'/restore',json={'expected_revision':rejected['revision']}).json()
    assert not restored['is_aesthetic_negative']
    session=library.current_screening_session(project['id'])
    assert len(session['actions'])==2
    summary=library.finish_screening_session(session['id'])
    assert summary['stats']['reject']==0
    assert not any(h['category']=='aesthetic_negative' for h in summary['hypotheses'])
