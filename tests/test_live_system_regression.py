"""Historical pixels are real; this module NEVER fabricates visual/source approval.

Self-contained migration from tracked historical manifests, not a developer's
/tmp database. Acceptance gates and offline cards use explicitly synthetic
fixtures in test_browser.py. Screenshots of history remain private, not CI uploads.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import threading
import time
from collections import Counter
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import expect
from browser_assertions import wait_until
from conftest import TOKEN
from test_browser import browser_page, unlock  # shared real-HTTP browser fixture
from ref_lab.api import create_app
from ref_lab.config import Settings
from ref_lab.db import SCHEMA
from ref_lab.imports import migrate_legacy
from ref_lab.cli import doctor, backup
from ref_lab.service import Library

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def migrated_history(tmp_path_factory):
    work=tmp_path_factory.mktemp('real-history')
    settings=Settings(work/'data',TOKEN,public_origin='http://testserver')
    library=Library(settings)
    first=migrate_legacy(library,ROOT/'references/changye-huansheng')
    with library.db.read() as con:
        originals={row['id']:json.loads(row['data']) for row in con.execute('SELECT id,data FROM refs')}
        alias_count=con.execute('SELECT COUNT(*) FROM aliases').fetchone()[0]
        old=sqlite3.connect(work/'v1.sqlite3')
        old.executescript(SCHEMA)
        # Use actual schema-1 tables and historical choices, without v2 catalog tables.
        for table in ('projects','assets','refs','aliases','jobs','notes','events'):
            for row in con.execute(f'SELECT * FROM {table}').fetchall():
                old.execute(f"INSERT INTO {table} VALUES({','.join('?' for _ in row)})",tuple(row))
        old.execute('PRAGMA user_version=1');old.commit();old.close()
    for suffix in ('','-wal','-shm'): Path(str(library.db.path)+suffix).unlink(missing_ok=True)
    (work/'v1.sqlite3').rename(library.db.path)
    upgraded=Library(settings)
    migration=upgraded.db.migration_report
    yield upgraded,originals,alias_count,first,migration


def test_real_history_migration_upgrade_and_idempotence(migrated_history,tmp_path):
    library,originals,alias_count,first,migration=migrated_history
    assert (first['created'],first['existing'],first['missing'],first['errors'])==(435,53,0,[])
    assert Counter(r['decision'] for r in originals.values())=={'keep':47,'pending':255,'reject':133}
    assert migration['from']==1 and Path(migration['backup']).is_file()
    with library.db.read() as con:
        assert con.execute('SELECT COUNT(*) FROM aliases').fetchone()[0]==alias_count==488
    for ident,old in originals.items():
        new=library.reference(ident)
        for key in ('asset_sha','decision','lane','preference','borrow','source','legacy_notes','review','card','revision','accepted_fingerprint'):
            assert new[key]==old[key], (ident,key)
        assert new['review'] is None and new['card'] is None and not new['field_ready']
        assert library.assets.verify(new['asset'])
    second=migrate_legacy(library,ROOT/'references/changye-huansheng')
    assert (second['created'],second['existing'],second['missing'],second['errors'])==(0,488,0,[])
    assert library.references('legacy-changye-huansheng')['total']==302
    assert library.references('legacy-changye-huansheng',decision='reject')['total']==133
    report=doctor(library);assert report['ok'] and report['assets_checked']==435
    assert Library(library.settings).db.migration_report is None
    # New discoveries are provenance only; historical annotations never become observations.
    with library.db.read() as con:
        assert con.execute('SELECT COUNT(*) FROM asset_observations').fetchone()[0]==0
    receipt={'first':first,'second':second,'schema_upgrade':'1 -> 2',
        'references':435,'assets':435,'aliases':488,'normal_candidates':302,
        'choices':dict(Counter(r['decision'] for r in originals.values())),
        'all_original_hashes_verified':True,'all_choices_and_revisions_preserved':True,'invented_reviews_or_cards':0,'doctor':report}
    folder=Path(os.environ.get('LAB_TEST_REPORTS',str(tmp_path)))
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'historical-migration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))


def real_curation_journey(page,library):
    """Same GUI journey can run over HTTP or an explicitly labeled DOM bridge."""
    expect(page.locator('#page-count')).to_have_text('1–60 / 302')
    wait_until(page, 'document.querySelector("#main-image").naturalWidth>0')
    page.locator('#view-original').click()
    wait_until(page, 'document.querySelector("#lightbox-image").naturalWidth>0')
    page.locator('#lightbox-close').click()
    target=page.evaluate('''()=>{const s=document.querySelector('#filmstrip');window.oldStrip=s;s.scrollLeft=2500;
        const b=s.getBoundingClientRect();window.oldScroll=s.scrollLeft;
        return [...s.children].find(n=>n.getBoundingClientRect().left>b.left+120&&n.getBoundingClientRect().right<b.right-100).dataset.ref;}''')
    page.locator(f'#filmstrip [data-ref="{target}"]').click()
    assert page.evaluate("oldStrip===document.querySelector('#filmstrip')&&oldStrip.scrollLeft===oldScroll")
    page.get_by_label('选择状态',exact=True).select_option('pending')
    expect(page.locator('#page-count')).to_have_text('1–60 / 255')
    selected=page.evaluate('state.activeId')
    page.locator('#auto-advance').uncheck()
    page.locator('[data-decision=inspiration]').click()
    wait_until(page, '!state.busy')
    assert library.inspirations()['total']==1
    assert library.reference(selected)['review'] is None
    page.get_by_role('button',name='新建角色项目',exact=True).click()
    page.get_by_label('角色名 *',exact=True).fill('隔离验收用第二项目')
    page.get_by_label('补充要求',exact=True).fill('仅验证引用关系，不做真实图像判断')
    page.get_by_role('button',name='建立项目',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    second=library.projects()[0]
    page.get_by_role('button',name='♡ 我的审美库',exact=True).click()
    page.get_by_role('button',name='引用到拍摄项目',exact=True).click()
    page.get_by_label('拍摄项目',exact=True).select_option(second['id'])
    page.get_by_role('button',name='引用并查看',exact=True).click()
    page.locator('#editor').wait_for(state='hidden')
    expect(page.locator('#page-count')).to_have_text('1–1 / 1')
    ref=library.references(second['id'])['items'][0]
    assert ref['asset_sha']==library.reference(selected)['asset_sha']
    assert ref['review'] is None and ref['card'] is None and not ref['field_ready']
    page.locator('[data-decision=reject]').click();wait_until(page, '!state.busy')
    assert library.references(second['id'])['total']==0
    assert library.inspirations()['total']==1
    page.get_by_role('button',name='已淘汰 / 恢复',exact=True).click()
    page.get_by_role('button',name='恢复这张图片',exact=True).click();wait_until(page, '!state.busy')
    assert library.references(second['id'])['total']==1
    page.get_by_role('button',name='角色精选',exact=True).click()
    page.get_by_role('button',name='制作现场卡',exact=True).click()
    page.locator('#download-task').wait_for()
    assert library.jobs(second['id'])[0]['status']=='blocked'
    page.locator('#editor-close').click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    with library.db.read() as con:
        assert con.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==435
        assert con.execute('SELECT COUNT(*) FROM asset_observations').fetchone()[0]==0
    return {'actual_historical_images_opened':True,'strip_node_and_visible_scroll_preserved':True,
        'global_save_multi_project_reject_restore':True,'card_job_created_not_falsely_completed':True,
        'mobile_width':390,'duplicate_files_created':0,'invented_observations':0}


def test_real_history_http_curation(migrated_history,browser_page,tmp_path):
    original,*_=migrated_history
    work=tmp_path/'http-data'
    # Snapshot all bytes in an isolated test directory, never mutate the base or user data.
    import zipfile
    bundle=tmp_path/'backup.zip';backup(original,bundle)
    with zipfile.ZipFile(bundle) as archive: archive.extractall(work)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    settings=Settings(work,TOKEN,public_origin=f'http://127.0.0.1:{port}')
    app=create_app(settings);library=app.state.library
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        for _ in range(150):
            if server.started:break
            time.sleep(.02)
        assert server.started
        page,_=browser_page;unlock(page,settings.public_origin)
        receipt=real_curation_journey(page,library)
        page.reload()
        expect(page.locator('#detail-panel')).to_contain_text('待 Agent 接手')
        assert library.stats(library.projects()[0]['id'])['ready']==0
        assert doctor(library)['ok']
        receipt['transport']='real HTTP + Chromium session cookie'
        receipt['refresh_preserves_selection_and_waiting_job']=True
        folder=Path(os.environ.get('LAB_TEST_REPORTS',str(tmp_path)));folder.mkdir(parents=True,exist_ok=True)
        (folder/'historical-http-ui.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    finally:
        server.should_exit=True;thread.join(timeout=8);sock.close()
