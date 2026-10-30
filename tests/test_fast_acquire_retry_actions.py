import json

import pytest

from ref_lab.db import encode


@pytest.mark.parametrize('search_state,preparation,expected', [
    ('idle', 'ready', True),
    ('idle', 'running', False),
    ('running', 'ready', False),
    ('partial', 'ready', True),
])
def test_existing_search_retry_actions(client, library, project, search_state, preparation, expected):
    response = client.post(f"/api/projects/{project['id']}/jobs", json={
        'kind': 'collection', 'collection_mode': 'search', 'target_count': 10,
    })
    assert response.status_code == 201
    ident = response.json()['id']
    with library.db.transaction() as con:
        job = json.loads(con.execute('SELECT data FROM jobs WHERE id=?', (ident,)).fetchone()['data'])
        job.update(status='blocked', search_state=search_state, preparation_state=preparation,
                   search_stop_reason='', search_timeout_seconds=2700)
        if search_state == 'running':
            import os
            from ref_lab.agent_collection import _owner_record
            job.update(status='running', active_attempt_id='active-test', search_attempt_id='active-test',
                       collection_process_owner=_owner_record(os.getpid(), phase='search'))
        con.execute('UPDATE jobs SET status=?, data=? WHERE id=?', (job['status'], encode(job), ident))
    result = client.get(f'/api/jobs/{ident}')
    assert result.status_code == 200
    assert result.json()['can_retry_search'] is expected
    assert library.job(ident)['id'] == ident
