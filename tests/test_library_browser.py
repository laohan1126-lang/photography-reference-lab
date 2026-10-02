"""Synthetic data tests; no claim of visual accuracy or owner-library acceptance."""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import add_reference, image_bytes, review_data
from ref_lab.api import create_app
from ref_lab.db import encode
from ref_lab.models import CandidateInput


def choose(client, ref, decision, **kw):
    response = client.patch(f"/api/references/{ref['id']}", json={"expected_revision":ref['revision'], "decision":decision, **kw})
    assert response.status_code == 200, response.text
    return response.json()


def gallery(client, **kw):
    r=client.get('/api/library/assets',params=kw)
    assert r.status_code == 200, r.text
    return r.json()


def annotate(client, ref, **kw):
    r=client.put(f"/api/library/assets/{ref['asset_sha']}/annotation",json={'expected_revision':0,**kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_global_asset_identity_does_not_merge_project_choices(client,project,library):
    ref=choose(client,add_reference(client,project), 'keep')
    other=client.post('/api/projects',json={'character':'另一个角色'}).json()
    use=client.post(f"/api/projects/{other['id']}/references",json={'asset_sha':ref['asset_sha'],'title':'另一个用途'}).json()['reference']
    use=choose(client,use,'reject')
    result=gallery(client)
    assert result['total']==1
    assert {u['decision'] for u in result['items'][0]['uses']}=={'keep','reject'}
    assert gallery(client,project_id=other['id'])['total']==0
    assert gallery(client,scope='kept',project_id=other['id'])['total']==0
    # A keep in another project cannot satisfy this project's pending/keep filter.
    choose(client,use,'pending')
    assert gallery(client,scope='kept',project_id=other['id'])['total']==0
    assert gallery(client,project_id=other['id'])['total']==1


def test_inspiration_is_independent_from_project_keep(client,project):
    ref=choose(client,add_reference(client,project),'keep')
    assert gallery(client,scope='inspiration')['total']==0
    inspiration=client.post('/api/inspirations',json={'asset_sha':ref['asset_sha'],'title':'独立审美收藏'} )
    assert inspiration.status_code == 201, inspiration.text
    choose(client,ref,'reject')
    result=gallery(client)
    assert result['total']==1 and result['items'][0]['inspiration_id']
    assert gallery(client,scope='kept')['total']==0


def test_recycled_filtered_and_archived_uses_do_not_leak(client,project,library):
    ref=add_reference(client,project)
    with library.db.transaction() as con:
        data=json.loads(con.execute('SELECT data FROM refs WHERE id=?',(ref['id'],)).fetchone()[0])
        data['preflight_filtered']=True
        con.execute('UPDATE refs SET data=? WHERE id=?',(encode(data),ref['id']))
    assert gallery(client)['total']==0
    with library.db.transaction() as con:
        data.update(preflight_filtered=False,detached_at='2026-10-02T00:00:00Z')
        con.execute('UPDATE refs SET data=? WHERE id=?',(encode(data),ref['id']))
    assert gallery(client)['total']==0
    with library.db.transaction() as con:
        data['detached_at']=None
        con.execute('UPDATE refs SET data=? WHERE id=?',(encode(data),ref['id']))
    assert gallery(client)['total']==1
    client.request("DELETE", f"/api/projects/{project['id']}",json={'expected_revision':project['revision']})
    assert gallery(client)['total']==0
    assert client.get('/api/library/assets',params={'project_id':project['id']}).status_code==409


def test_facets_are_explicit_and_do_not_change_reference_or_asset(client,project,library):
    ref=add_reference(client,project,title='仰拍全身回眸，这只是标题')
    before=library.reference(ref['id'])
    raw=library.assets.path(before['asset']).read_bytes()
    assert gallery(client,viewpoint='low_angle')['total']==0
    assert gallery(client,viewpoint='unknown')['total']==1
    annotation=annotate(client,ref,viewpoint='low_angle',framing='full_body',pose='turning')
    assert annotation['actor']=='human'
    assert gallery(client,viewpoint='low_angle',framing='full_body',pose='turning')['total']==1
    assert gallery(client,viewpoint='low_angle',framing='half_body')['total']==0
    after=library.reference(ref['id'])
    assert after==before
    assert hashlib.sha256(library.assets.path(after['asset']).read_bytes()).digest()==hashlib.sha256(raw).digest()
    r=client.put(f"/api/library/assets/{ref['asset_sha']}/annotation",json={'expected_revision':0,'viewpoint':'high_angle'})
    assert r.status_code==409
    assert gallery(client,viewpoint='low_angle')['total']==1


def test_filters_apply_before_stable_pagination_and_unknown_stays_unknown(client,project):
    refs=[add_reference(client,project,seed=i) for i in range(6)]
    annotate(client,refs[0],framing='full_body')
    annotate(client,refs[3],framing='full_body')
    first=gallery(client,framing='full_body',limit=1)
    second=gallery(client,framing='full_body',limit=1,offset=1)
    assert first['total']==second['total']==2
    assert first['items'][0]['id']!=second['items'][0]['id']
    assert gallery(client,framing='full_body',limit=1)['items'][0]['id']==first['items'][0]['id']
    assert gallery(client,framing='unknown')['total']==4
    assert gallery(client,limit=1,offset=999)['offset']==5
    assert gallery(client,q="%' OR 1=1 --")['total']==0
    assert gallery(client,orientation='portrait')['total']==6
    assert gallery(client,orientation='landscape')['total']==0


def test_kind_uses_observation_not_title_or_query(client,project):
    ref=add_reference(client,project,title='cosplay_photo 真人cos 正片')
    assert gallery(client,kind='cosplay_photo')['total']==0
    assert gallery(client,kind='unknown')['total']==1
    r=client.post(f"/api/references/{ref['id']}/review",json={'expected_revision':ref['revision'],'review':review_data(ref['asset_sha'])})
    assert r.status_code==200,r.text
    assert gallery(client,kind='cosplay_photo')['total']==1


def test_saved_queries_are_dynamic_and_survive_restart(client,project,settings):
    first=add_reference(client,project)
    annotate(client,first,viewpoint='low_angle')
    saved=client.post('/api/library/searches',json={'name':'仰拍','filters':{'viewpoint':'low_angle'}})
    assert saved.status_code==201, saved.text
    saved=saved.json()
    second=add_reference(client,project,seed=2)
    annotate(client,second,viewpoint='low_angle')
    assert gallery(client,**saved['filters'])['total']==2
    with TestClient(create_app(settings)) as reopened:
        reopened.headers['Authorization']='Bearer '+settings.token
        assert reopened.get('/api/library/searches').json()==[saved]
    assert client.post('/api/library/searches',json={'name':'仰拍','filters':{}}).status_code==409
    assert client.delete(f"/api/library/searches/{saved['id']}?expected_revision=2").status_code==409
    assert client.delete(f"/api/library/searches/{saved['id']}?expected_revision=1").status_code==200
    assert gallery(client)['total']==2


def test_project_navigation_persists_without_changing_choices(client,project,settings,library):
    ref=add_reference(client,project)
    before=library.reference(ref['id'])
    assert client.put(f"/api/library/projects/{project['id']}/pin",json={'pinned':True}).status_code==200
    assert client.post(f"/api/library/projects/{project['id']}/visit").status_code==200
    with TestClient(create_app(settings)) as reopened:
        reopened.headers['Authorization']='Bearer '+settings.token
        nav=reopened.get('/api/library/navigation').json()
        assert nav['pinned_ids']==nav['recent_ids']==[project['id']]
    assert library.reference(ref['id'])==before
    assert library.project(project['id'])['revision']==project['revision']


def test_pin_limit_and_archived_project_exclusion(client):
    projects=[client.post('/api/projects',json={'character':f'角色{i}'}).json() for i in range(9)]
    for p in projects[:8]:
        assert client.put(f"/api/library/projects/{p['id']}/pin",json={'pinned':True}).status_code==200
    assert client.put(f"/api/library/projects/{projects[8]['id']}/pin",json={'pinned':True}).status_code==409
    p=projects[0]
    client.request("DELETE", f"/api/projects/{p['id']}",json={'expected_revision':p['revision']})
    assert p['id'] not in client.get('/api/library/navigation').json()['pinned_ids']
    assert client.put(f"/api/library/projects/{projects[8]['id']}/pin",json={'pinned':True}).status_code==200


@pytest.mark.parametrize('params',[{'limit':0},{'limit':101},{'offset':-1},{'scope':'reject'},{'viewpoint':'guess'},{'kind':'guess'},{'q':'a'*401}])
def test_invalid_filters_fail_explicitly(client,params):
    assert client.get('/api/library/assets',params=params).status_code==422


def test_auth_csrf_and_maintenance_guards_cover_new_routes(app,client,project):
    ref=add_reference(client,project)
    with TestClient(app) as unlocked:
        assert unlocked.get('/api/library/assets').status_code==401
        assert unlocked.put(f"/api/library/assets/{ref['asset_sha']}/annotation",json={'expected_revision':0}).status_code==401
    csrf=client.headers.pop('X-Lab-CSRF')
    assert client.post('/api/library/searches',json={'name':'x','filters':{}}).status_code==403
    client.headers['X-Lab-CSRF']=csrf
    assert client.post('/api/maintenance',json={'enabled':True}).status_code==200
    assert client.put(f"/api/library/assets/{ref['asset_sha']}/annotation",json={'expected_revision':0}).status_code==503
    assert gallery(client)['total']==1


def test_ten_thousand_metadata_rows_are_filtered_and_paginated_in_sql(client,project,library):
    """Metadata scale only: these synthetic IDs have no real image files."""
    seed=add_reference(client,project)
    with library.db.transaction() as con:
        ref=json.loads(con.execute('SELECT data FROM refs WHERE id=?',(seed['id'],)).fetchone()[0])
        asset=json.loads(con.execute('SELECT data FROM assets WHERE id=?',(seed['asset_sha'],)).fetchone()[0])
        for i in range(10000):
            sha=f'{i:064x}'
            a={**asset,'id':sha}
            r={**ref,'id':f'scale-{i}','asset_sha':sha,'title':f'合成规模样本{i}'}
            con.execute('INSERT INTO assets VALUES(?,?)',(sha,encode(a)))
            con.execute('INSERT INTO refs VALUES(?,?,?,?,?,?)',(r['id'],project['id'],sha,r['decision'],r['state'],encode(r)))
    result=gallery(client,limit=60,offset=9960)
    assert result['total']==10001 and len(result['items'])==41
    filtered=gallery(client,q='合成规模样本9999',limit=1)
    assert filtered['total']==1 and filtered['items'][0]['title']=='合成规模样本9999'


def test_gallery_static_module_is_served_and_packaged(client):
    import tomllib
    root=Path(__file__).resolve().parents[1]
    config=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))
    assert 'web/library-browser.js' in config['tool']['setuptools']['data-files']['share/photography-reference-lab/web']
    html=client.get('/').text
    assert html.index('/static/library-browser.js') < html.index('/static/app.js')
    script=client.get('/static/library-browser.js')
    assert script.status_code==200 and 'window.LibraryDiscovery' in script.text
    assert client.get('/static/not-an-allowed-file.js').status_code==404


def test_full_backup_restores_gallery_annotations_searches_and_navigation(client,project,library,tmp_path,settings):
    import zipfile
    from dataclasses import replace
    from ref_lab.cli import backup
    ref=add_reference(client,project)
    annotate(client,ref,viewpoint='high_angle')
    saved=client.post('/api/library/searches',json={'name':'备份搜索','filters':{'viewpoint':'high_angle'}}).json()
    client.put(f"/api/library/projects/{project['id']}/pin",json={'pinned':True})
    output=tmp_path/'gallery-backup.zip'
    backup(library,output)
    restored=tmp_path/'restored'
    with zipfile.ZipFile(output) as bundle:
        bundle.extractall(restored)
    with TestClient(create_app(replace(settings,data_dir=restored))) as reopened:
        reopened.headers['Authorization']='Bearer '+settings.token
        assert reopened.get('/api/library/searches').json()==[saved]
        assert reopened.get('/api/library/navigation').json()['pinned_ids']==[project['id']]
        result=gallery(reopened,viewpoint='high_angle')
        assert result['total']==1 and result['items'][0]['file_available']
        assert result['items'][0]['annotation']['viewpoint']=='high_angle'
