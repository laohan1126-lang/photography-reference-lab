"""Browser workflows use explicitly synthetic fixtures, not claims about real cosplay images."""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import socket
import threading
import time
import zipfile
from pathlib import Path
import pytest
import uvicorn
from playwright.sync_api import expect
from browser_assertions import wait_until
from ref_lab.api import create_app
from ref_lab.config import Settings
from ref_lab.models import CandidateInput, Card, ProjectInput, ReferenceEdit, Source, VisualReview
from conftest import TOKEN, card_data, image_bytes, review_data
from test_ui_components import advanced, choose, idle, exercise_stable_strip
from test_personal_library import candidate_zip


@pytest.fixture
def live_site(tmp_path):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    settings = Settings(tmp_path / "data", TOKEN, public_origin=f"http://127.0.0.1:{port}")
    app = create_app(settings)
    library = app.state.library
    project = library.create_project(ProjectInput(character="王昭君", work="王者荣耀", costume="长夜焕生", brief="漫展实用；以站姿、回眸与自然互动为主。"))
    for index in range(3):
        asset = library.ingest_asset(image_bytes(index))
        library.add_candidate(project["id"], CandidateInput(asset_sha=asset["id"], title=f"独立参考 {index+1}"))
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    for _ in range(150):
        if server.started: break
        time.sleep(.02)
    assert server.started
    yield settings.public_origin, library, project
    server.should_exit = True
    thread.join(timeout=8)
    sock.close()


@pytest.fixture
def browser_page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as engine:
        executable = os.environ.get("LAB_CHROMIUM") or shutil.which("chromium") or shutil.which("chromium-browser")
        if not executable and not Path(engine.chromium.executable_path).exists():
            pytest.skip("Chromium not installed; run python -m playwright install chromium")
        browser = engine.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        yield page, errors
        browser.close()
        assert not errors, errors


def unlock(page, url):
    page.goto(url)
    page.get_by_label("访问口令").fill(TOKEN)
    page.get_by_role("button", name="进入我的参考库").click()
    page.locator("#main-image").wait_for()


def artifact(page, name):
    folder = Path(os.environ.get("LAB_TEST_ARTIFACTS", ".local/test-artifacts"))
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / name), full_page=True)


def test_browser_select_persist_filter_and_mobile(live_site, browser_page):
    url, library, project = live_site
    page, errors = browser_page
    unlock(page, url)
    advanced(page)
    page.get_by_label('喜欢什么／准备借鉴什么').fill('只借鉴动作，不借鉴服装')
    choose(page,'keep')
    ref=library.references(project['id'],decision='keep')['items'][0]
    assert ref['preference']=='只借鉴动作，不借鉴服装'
    page.get_by_label('选择状态',exact=True).select_option('keep')
    expect(page.locator('#page-count')).to_have_text('1–1 / 1')
    page.reload()
    expect(page.locator('#page-count')).to_have_text('1–1 / 1')
    advanced(page)
    assert page.get_by_label('喜欢什么／准备借鉴什么').input_value()==ref['preference']
    artifact(page,'desktop-synthetic-reference.png')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    artifact(page,'mobile-synthetic-reference.png')
    page.locator('#view-original').click()
    wait_until(page, 'document.querySelector("#lightbox-image").naturalWidth>0')
    page.locator('#lightbox-close').click()
    page.get_by_role('button',name='现场卡',exact=True).click()
    page.get_by_text('还没有已确认的现场卡',exact=True).wait_for()


def test_browser_agent_result_accept_and_offline_pack(live_site,browser_page,tmp_path):
    url,library,project=live_site
    page,errors=browser_page
    unlock(page,url)
    page.locator('#auto-advance').uncheck();choose(page,'keep')
    page.get_by_role('button',name='制作现场卡',exact=True).click()
    page.locator('#download-task').wait_for()
    job=library.jobs()[0]
    with page.expect_download() as info:
        page.locator('#download-task').click()
    task_path=tmp_path/'job.zip';info.value.save_as(task_path)
    with zipfile.ZipFile(task_path) as archive:
        bundle=json.loads(archive.read('job.json'))
        assert 'AGENT_TASK.md' in archive.namelist()
        instructions=archive.read('AGENT_TASK.md').decode()
        assert job['id'] in instructions and '不代替用户确认' in instructions
        assert len(bundle['references'])==1
        ref=bundle['references'][0]
        assert hashlib.sha256(archive.read(ref['bundle_image'])).hexdigest()==ref['asset_sha']
    assert library.stats(project['id'])['ready']==0
    card=card_data();card['retouch']['route']='cleanup';card['retouch']['steps']=['只清理合成测试背景，不重绘人物。']
    result={'schema_version':1,'job_id':job['id'],'items':[{'reference_id':ref['id'],
        'expected_revision':ref['revision'],'producer':'synthetic-browser-test-NOT-vision',
        'result':{'review':review_data(ref['asset_sha']),'card':card}}]}
    page.locator('#import-task-result').click()
    page.locator('#import-files').set_input_files({'name':'analysis.json','mimeType':'application/json','buffer':json.dumps(result).encode()})
    page.get_by_role('button',name='开始导入',exact=True).click()
    page.locator('#close-receipt').click()
    assert library.stats(project['id'])['ready']==0
    page.get_by_role('button',name='检查草稿并确认',exact=True).click()
    page.get_by_label('来源／权利说明',exact=True).select_option('owned')
    page.get_by_label('自有作品或来源说明',exact=True).fill('Synthetic pixels generated by this test, not a real photograph')
    page.get_by_label('我已核对图片、口令、安全与来源；不是仅依据搜索标题',exact=True).check()
    page.locator('#accept-card').click()
    page.locator('#editor').wait_for(state='hidden')
    expect(page.locator('.next-step')).to_contain_text('这张卡已由你确认')
    assert library.stats(project['id'])['ready']==1
    page.locator('.project-tools summary').click()
    page.get_by_role('button',name='离线拍摄包',exact=True).click()
    with page.expect_download() as info:
        page.get_by_role('button',name='生成并下载',exact=True).click()
    pack=tmp_path/'pack.zip';info.value.save_as(pack);extracted=tmp_path/'offline'
    with zipfile.ZipFile(pack) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert len(manifest['references'])==1
        entry=manifest['references'][0]
        assert hashlib.sha256(archive.read(entry['offline_original'])).hexdigest()==entry['asset_sha']
        archive.extractall(extracted) # Trusted output produced by this test.
    page.context.set_offline(True)
    page.goto((extracted/'index.html').as_uri())
    wait_until(page, 'document.querySelector("#photo").naturalWidth>0')
    guide=page.locator('#guide').text_content()
    assert '身体先朝那边' in guide and '现有器材方案' in guide
    assert '后期路线：cleanup' in guide and '只清理合成测试背景' in guide
    artifact(page,'offline-synthetic-field-card.png')
    page.context.set_offline(False)
    page.goto(url)
    page.locator('.project-tools summary').click()
    page.get_by_role('button',name='角色与要求',exact=True).click()
    page.get_by_label('补充要求').fill('Changed constraints: indoor reference only')
    page.get_by_role('button',name='保存修改',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    assert library.stats(project['id'])['ready']==0
    assert library.reference(ref['id'])['card'] is not None


def test_browser_notes_collection_download_import(live_site,browser_page,tmp_path):
    url,library,project=live_site
    page,errors=browser_page;unlock(page,url)
    page.get_by_role('button',name='新建角色项目',exact=True).click()
    page.get_by_label('角色名 *',exact=True).fill('有马加奈')
    page.get_by_label('补充要求',exact=True).fill('自然动作，服装版本以后再补')
    page.get_by_role('button',name='建立项目',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    page.get_by_role('button',name='摄影笔记',exact=True).click()
    page.get_by_role('button',name='＋ 写摄影笔记',exact=True).click()
    page.get_by_label('笔记标题 *',exact=True).fill('引导笔记')
    page.get_by_label('正文（支持保留 Markdown）',exact=True).fill('# 观察\n<script>window.evil=1</script>\n先沟通。')
    page.get_by_role('button',name='保存笔记',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    page.locator('[data-note]').first.click();assert page.evaluate('window.evil') is None
    page.locator('#editor-close').click()
    page.get_by_role('button',name='采集任务',exact=True).click()
    page.get_by_role('button',name='＋ 建立采集任务',exact=True).click()
    page.get_by_label('本轮自由要求').fill('先同角色真人图，再补可迁移动作与电影光影')
    page.get_by_role('button',name='建立采集任务',exact=True).click()
    page.locator('#download-task').wait_for();job=library.jobs()[0]
    assert job['status']=='blocked'
    with page.expect_download() as info: page.locator('#download-task').click()
    job_path=tmp_path/'collection.zip';info.value.save_as(job_path)
    with zipfile.ZipFile(job_path) as archive:
        bundle=json.loads(archive.read('job.json'))
        assert bundle['job']['notes']=='先同角色真人图，再补可迁移动作与电影光影'
        assert 'candidate-package.schema.json' in archive.namelist()
    page.locator('#import-task-result').click()
    page.locator('#import-files').set_input_files({'name':'candidates.zip','mimeType':'application/zip','buffer':candidate_zip(job)})
    page.get_by_role('button',name='开始导入',exact=True).click()
    expect(page.locator('#editor')).to_contain_text('新增 1，已有 0')
    assert library.references(job['project_id'])['total']==1
    ref=library.references(job['project_id'])['items'][0]
    assert ref['decision']=='pending' and ref['review'] is None
    assert library.job(job['id'])['status']=='succeeded'


@pytest.mark.parametrize('auto',[False,True])
def test_browser_stable_strip_and_recovery(live_site,browser_page,auto):
    url,library,project=live_site
    for i in range(3,72):
        asset=library.ingest_asset(image_bytes(i))
        library.add_candidate(project['id'],CandidateInput(asset_sha=asset['id'],title=f'Synthetic {i}'))
    page,errors=browser_page;unlock(page,url)
    exercise_stable_strip(page,library,project,auto)
