"""Real HTTP/Chromium and process restart; isolated synthetic assets only."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import expect

from conftest import TOKEN, image_bytes
from ref_lab.agent_collection import stop_process_tree
from ref_lab.config import Settings
from ref_lab.models import CandidateInput, ProjectInput
from ref_lab.service import Library
from test_browser import browser_page, unlock
from test_ui_components import choose, idle

ROOT = Path(__file__).resolve().parents[1]


def request(url, path, method='GET', body=None):
    req = urllib.request.Request(url+path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


@contextmanager
def running(data_dir, port):
    url = f'http://127.0.0.1:{port}'
    env = dict(os.environ,LAB_DATA_DIR=str(data_dir),LAB_ACCESS_TOKEN=TOKEN,LAB_PUBLIC_ORIGIN=url)
    env.pop('LAB_COLLECTION_COMMAND',None)
    process = subprocess.Popen([sys.executable,'-X','utf8','-m','ref_lab','serve','--port',str(port)],
        cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        **({'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}))
    try:
        deadline = time.monotonic()+15
        while True:
            assert process.poll() is None, 'Isolated HTTP server exited during startup'
            try:
                info = request(url,'/api/runtime')
                break
            except OSError:
                assert time.monotonic()<deadline, 'Isolated server did not become ready'
                time.sleep(.05)
        assert Path(info['database']) == (data_dir/'library.sqlite3').resolve()
        assert Path(info['source']) == ROOT/'ref_lab/api.py'
        yield url, info
    finally:
        stop_process_tree(process)


def test_browser_feedback_survives_native_process_restart_and_rejects_stale_summary(tmp_path,browser_page):
    data_dir = tmp_path/'data'
    library = Library(Settings(data_dir,TOKEN))
    project = library.create_project(ProjectInput(character='restart regression'))
    asset = library.ingest_asset(image_bytes(74),'isolated.png')
    ref = library.add_candidate(project['id'],CandidateInput(asset_sha=asset['id']))['reference']
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    page,_ = browser_page
    with running(data_dir,port) as (url, first):
        unlock(page,url)
        page.locator('#auto-advance').uncheck()
        choose(page,'keep')
        page.locator('#finish-screening-btn').click()
        page.locator('[name=hypothesis]').check()
        page.locator('[name=apply_choice][value=true]').check()
        page.locator('#session-confirm-form button[type=submit]').click()
        page.locator('#editor').wait_for(state='hidden')
        before = request(url,'/api/profile')
        assert len(before['project_use_exemplars'])==1
        assert before['project_use_exemplars'][0]['learning_eligible'] is True
        sessions = request(url,f"/api/projects/{project['id']}/screening-sessions")
        assert len(sessions)==1 and len(sessions[0]['actions'])==1
        ref = request(url,'/api/references/'+ref['id'])
    # Entire server process stopped; same data + browser cookie, a new PID.
    with running(data_dir,port) as (url, second):
        assert second['pid'] != first['pid']
        page.reload()
        expect(page.locator('[data-decision=keep]')).to_have_class('chosen')
        assert request(url,'/api/profile')==before
        assert request(url,f"/api/projects/{project['id']}/screening-sessions")==sessions
        # Two rapid clicks must be one write. A fresh session may confirm the
        # same use without creating a second reusable sample.
        page.locator('[data-decision=keep]').evaluate('(n)=>{n.click();n.click();}')
        idle(page)
        current = request(url,f"/api/projects/{project['id']}/screening-sessions/current")
        assert len(current['actions'])==1
        page.locator('#finish-screening-btn').click()
        page.locator('[name=hypothesis]').check()
        page.locator('[name=apply_choice][value=true]').check()
        latest = request(url,'/api/references/'+ref['id'])
        request(url,'/api/references/'+ref['id'],'PATCH',{'expected_revision':latest['revision'],'decision':'maybe'})
        page.locator('#session-confirm-form button[type=submit]').click()
        expect(page.locator('#toast')).to_contain_text('筛选总结已过期')
        assert page.locator('#editor').is_visible()
        profile = request(url,'/api/profile')
        assert profile['version']==before['version']
        assert len(profile['project_use_exemplars'])==1
        assert profile['project_use_exemplars'][0]['learning_eligible'] is False
