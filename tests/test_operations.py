from __future__ import annotations
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from ref_lab.api import create_app
from ref_lab.cli import doctor
from ref_lab.config import Settings
from ref_lab.db import encode
from ref_lab.export import OFFLINE_HTML
from ref_lab.models import NoteInput
from conftest import TOKEN, add_reference, ready_reference


def test_note_edit_conflict_and_reimport_preserves_changes(client, library, project):
    value = {'title':'原笔记', 'body':'原始文字', 'source_path':'notes/one.md'}
    note = client.post(f"/api/projects/{project['id']}/notes", json=value).json()
    edit = client.put(f"/api/notes/{note['id']}", json={'expected_revision':note['revision'], 'title':'改过的标题', 'body':'用户修改的正文'})
    assert edit.status_code == 200
    assert client.put(f"/api/notes/{note['id']}", json={'expected_revision':note['revision'], 'title':'过期', 'body':'覆盖'}).status_code == 409
    imported = library.add_note(project['id'], NoteInput(**value))
    assert imported['id'] == note['id'] and imported['body'] == '用户修改的正文'


def test_doctor_retracts_corrupt_asset_acceptance(client, library, project):
    ref = ready_reference(client, project)
    path = library.assets.path(ref['asset'])
    original = path.read_bytes()
    path.write_bytes(b'corrupted')
    report = doctor(library)
    assert not report['ok']
    assert library.reference(ref['id'])['state'] == 'missing_asset'
    assert library.reference(ref['id'])['accepted_fingerprint'] is None
    assert library.stats(project['id'])['ready'] == 0
    path.write_bytes(original)
    assert doctor(library)['ok']
    assert not library.reference(ref['id'])['field_ready']


def test_streamed_body_limit_is_enforced(tmp_path):
    settings = Settings(tmp_path, TOKEN, public_origin='http://testserver', max_body_bytes=200)
    with TestClient(create_app(settings)) as client:
        def chunks():
            yield b'{"token":"'
            yield b'x'*300
            yield b'"}'
        response = client.post('/api/session', content=chunks(), headers={'content-type':'application/json'})
        assert response.status_code == 413


def test_offline_embedded_javascript_parses(tmp_path):
    node = shutil.which('node')
    if not node: pytest.skip('Node is required for offline JavaScript syntax validation')
    script = OFFLINE_HTML.split('<script>')[1].split('</script>')[0]
    path = tmp_path/'offline.js'
    path.write_text(script, encoding='utf-8')
    result = subprocess.run([node,'--check',str(path)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_ten_thousand_reference_index_and_project_isolation(client, library, project):
    # Synthetic metadata-only scale fixture, NOT 10,000 acquired or visually reviewed photos.
    template = add_reference(client, project)
    with library.db.transaction() as con:
        for index in range(10000):
            ref = {k:v for k,v in template.items() if k not in {'asset','blockers','field_ready'}}
            ref.update(id=f'scale-{index:05d}', asset_sha=None, state='missing_asset', title=f'合成规模记录 {index:05d}')
            con.execute('INSERT INTO refs VALUES(?,?,?,?,?,?)', (ref['id'], project['id'], None, 'pending', 'missing_asset', encode(ref)))
    page = library.references(project['id'], limit=60, offset=9960)
    assert page['total'] == 10001 and len(page['items']) == 41
    assert len({x['id'] for x in page['items']}) == 41
    other = client.post('/api/projects', json={'character':'另一角色'}).json()
    assert library.references(other['id'])['total'] == 0
    assert library.references(project['id'], query='合成规模记录 09999')['total'] == 1


def test_closeout_rejects_secrets_and_escape():
    spec = importlib.util.spec_from_file_location('finish_task', Path(__file__).resolve().parents[1]/'tools/finish_task.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in ('.env', '.env.production', '.local/access-token', '../outside', '.git/config', 'x.sqlite3'):
        with pytest.raises(ValueError): module.check_path(path)
    assert module.check_path('README.md') == 'README.md'
    assert module.check_path('.env.example') == '.env.example'
