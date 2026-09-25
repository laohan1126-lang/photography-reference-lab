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
from playwright.sync_api import expect, sync_playwright

from ref_lab.api import create_app
from ref_lab.config import Settings
from ref_lab.models import ProjectInput, Source, VisualReview, Card, ReferenceEdit
from ref_lab.service import Library

TOKEN = "test-live-system-token-xyz-12345"

def unlock(page, url):
    page.goto(url)
    page.get_by_label("访问口令").fill(TOKEN)
    page.get_by_role("button", name="进入我的参考库").click()
    page.locator("#main-image").wait_for()

def test_full_live_system_regression(tmp_path):
    """Tests the full system using migrated real historical database."""
    migrated_dir = Path("/tmp/regression-real-data-test")
    assert (migrated_dir / "library.sqlite3").is_file(), "Migrated database missing"

    # Copy migrated data to a test working dir so tests can write without mutating the base migrated copy
    work_dir = tmp_path / "live_data"
    shutil.copytree(migrated_dir, work_dir)
    (work_dir / "access-token").write_text(TOKEN, encoding="utf-8")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]

    settings = Settings(work_dir, TOKEN, public_origin=f"http://127.0.0.1:{port}")
    app = create_app(settings)
    library = app.state.library

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()

    for _ in range(150):
        if server.started:
            break
        time.sleep(0.02)
    assert server.started, "Server failed to start"
    base_url = f"http://127.0.0.1:{port}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()

        # 1. Unlock screen & enter app
        unlock(page, base_url)
        expect(page.locator(".brand-mark")).to_contain_text("R.")

        # 2. Check migrated project 王昭君
        expect(page.locator("#project-header h1")).to_contain_text("王昭君")
        # Check that we have 435 refs total
        expect(page.locator(".pagination")).to_contain_text("1–60 / 435")

        # 3. Create second character project with free-form requirements
        page.get_by_role("button", name="新建角色项目", exact=True).click()
        page.get_by_label("角色名 *", exact=True).fill("艾拉")
        page.get_by_label("出自作品（选填）", exact=True).fill("原神")
        page.get_by_label("服装／皮肤版本（选填）", exact=True).fill("常服")
        page.get_by_label("补充要求", exact=True).fill("自由要求：需要森林自然光背景，避免过度后期磨皮。")
        page.get_by_role("button", name="建立项目", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")

        expect(page.locator("#project-header h1")).to_contain_text("艾拉")
        # Check empty state for newly created project
        page.get_by_text("候选池还没有匹配的参考", exact=True).wait_for()

        # Switch back to legacy-changye-huansheng
        page.locator("#project-list button").filter(has_text="王昭君").click()
        page.locator("#main-image").wait_for()
        expect(page.locator("#project-header h1")).to_contain_text("王昭君")

        # 4. Desktop View & Lightbox (Standalone high-res image)
        evidence_dir = Path(".local/regression-evidence")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.screenshot(path=str(evidence_dir / "desktop-migrated-reference.png"), full_page=True)
        page.get_by_role("button", name="查看独立原图", exact=True).click()
        expect(page.locator("#lightbox")).to_be_visible()
        expect(page.locator("#lightbox-image")).to_have_js_property("complete", True)
        page.get_by_role("button", name="关闭", exact=True).click()
        expect(page.locator("#lightbox")).not_to_be_visible()

        # 5. Mobile View (390px width)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(100)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(evidence_dir / "mobile-migrated-reference.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 900})

        # 6. Keep / Pending / Reject & Persistence after refresh
        page.locator("#auto-advance").uncheck()
        page.get_by_label("我喜欢／不喜欢的地方").fill("姿态非常自然，重点借鉴手部支撑角度")
        page.get_by_role("button", name="✓ 保留 K", exact=True).click()
        page.reload()
        # Since reload picks first project in reverse rowid, switch back to 王昭君
        page.locator("#project-list button").filter(has_text="王昭君").click()
        page.locator("#main-image").wait_for()
        assert page.get_by_label("我喜欢／不喜欢的地方").input_value() == "姿态非常自然，重点借鉴手部支撑角度"

        # 7. Filtering & Pagination
        page.get_by_label("选择状态", exact=True).select_option("reject")
        # 133 items rejected historically
        expect(page.locator(".pagination")).to_contain_text("/ 133")
        page.get_by_label("选择状态", exact=True).select_option("keep")
        # 47 kept items historically
        expect(page.locator(".pagination")).to_contain_text("/ 47")
        page.get_by_label("选择状态", exact=True).select_option("")
        expect(page.locator(".pagination")).to_contain_text("/ 435")

        # 8. Note Editing & Persistence
        page.get_by_role("button", name="摄影笔记", exact=True).click()
        page.get_by_role("button", name="＋ 写摄影笔记", exact=True).click()
        page.get_by_label("笔记标题 *", exact=True).fill("现场布光测试备忘")
        page.get_by_label("正文（支持保留 Markdown）", exact=True).fill("# 布光要点\n- 单主灯+柔光箱\n- 轮廓反光板")
        page.get_by_role("button", name="保存笔记", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")
        expect(page.locator("[data-note]").first).to_contain_text("现场布光测试备忘")

        # Switch back to references (候选池)
        page.get_by_role("button", name="候选池", exact=True).click()
        page.locator("#main-image").wait_for()

        # 9. Audit & Invalidation Mechanism
        # Test non-real pose material cannot enter field card
        page.get_by_role("button", name="人工核验", exact=True).click()
        page.get_by_label("图片实际类型").select_option("equipment")
        page.get_by_label("看得见的事实（每行一条）*").fill("单灯器材图，非真人姿势。")
        page.get_by_role("button", name="保存人工核验", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")
        expect(page.locator(".gate-box")).to_contain_text("不是可用的真人摄影参考")
        expect(page.locator(".detail-top")).to_contain_text("器材图")

        # Change to real cosplay photo
        page.get_by_role("button", name="人工核验", exact=True).click()
        page.get_by_label("图片实际类型").select_option("cosplay_photo")
        page.get_by_label("与目标角色的关系").select_option("exact")
        for text in ("图中有明确可见的人物", "需要借鉴的肢体／动作看得清", "这是独立画面，不是多个画面的拼图", "实际清晰度足以支持动作分析"):
            page.get_by_label(text, exact=True).check()
        page.get_by_label("看得见的事实（每行一条）*").fill("真人全身站立，姿势可辨。")
        page.get_by_role("button", name="保存人工核验", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")

        # Source verification
        page.get_by_role("button", name="来源与标题", exact=True).click()
        page.get_by_label("权利状态").select_option("owned")
        page.get_by_label("使用权／来源说明").fill("自有拍摄素材或已授权")
        page.get_by_label("我已检查原发布页，或确认这是我的自有作品").check()
        page.get_by_role("button", name="保存来源", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")

        # Field Card Draft
        page.get_by_role("button", name="编写资料卡", exact=True).click()
        form = page.locator("#editor form")
        for name, value in {
            "intent": "漫展现场拍摄参考",
            "verbal_cues": "身体微侧，自然回眸微笑。",
            "static_steps": "左手轻按肩部，右脚稍前。",
            "photographer_steps": "平视角度，单灯斜上方45度柔光。",
            "safety": "注意脚下地面平整。",
            "fallback": "如果转身体力不支可改为纯正脸侧身。",
            "visible_evidence": "右上方柔光单灯，左侧环境微光充实阴影。",
            "interpretation": "原图推测为大柔光箱打亮面部。",
            "available_gear_plan": "V1闪光灯配八角柔光箱。"
        }.items():
            form.locator(f'[name="{name}"]').fill(value)
        form.locator('[name="route"]').select_option("cleanup")
        form.locator('[name="steps"]').fill("清理杂乱背景路人，微调肤色。")
        page.get_by_role("button", name="保存资料卡草稿", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")

        # Confirm field card
        page.get_by_role("button", name="我已核对，确认为现场卡", exact=True).click()
        expect(page.locator(".gate-box")).to_contain_text("已通过入库门槛，并由你确认")

        # 10. Invalidation test: changing project requirements invalidates card confirmation
        page.get_by_role("button", name="角色与要求", exact=True).click()
        page.get_by_label("补充要求").fill("修改后的自由要求：改为纯棚拍黑背景")
        page.get_by_role("button", name="保存修改", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")

        # Card confirmation should now be invalidated
        expect(page.locator(".gate-box")).to_contain_text("尚不能作为现场卡")

        # Concurrency check: Stale revision conflict test (409)
        ref_id = library.references("legacy-changye-huansheng")["items"][0]["id"]
        ref_item = library.reference(ref_id)
        # Attempt to edit with stale revision
        with pytest.raises(Exception):
            library.edit_reference(ref_id, ReferenceEdit(preference="并发测试"), expected_revision=ref_item["revision"] - 1, actor="stale_client")

        # Re-draft & re-confirm card to make it ready for offline pack
        page.locator("#edit-card").click()
        page.get_by_role("button", name="保存资料卡草稿", exact=True).click()
        page.locator("#editor").wait_for(state="hidden")
        page.get_by_role("button", name="我已核对，确认为现场卡", exact=True).click()
        expect(page.locator(".gate-box")).to_contain_text("已通过入库门槛，并由你确认")

        # 11. Offline shoot package export & offline verification
        page.get_by_role("button", name="离线拍摄包", exact=True).click()
        with page.expect_download() as download_info:
            page.get_by_role("button", name="生成并下载", exact=True).click()
        pack = tmp_path / "offline_field_pack.zip"
        download_info.value.save_as(pack)

        extracted = tmp_path / "offline_extracted"
        with zipfile.ZipFile(pack) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            entry = manifest["references"][0]
            assert hashlib.sha256(archive.read(entry["offline_original"])).hexdigest() == entry["asset_sha"]
            archive.extractall(extracted)

        # Disconnect network and open index.html
        context.set_offline(True)
        page.goto((extracted / "index.html").as_uri())
        expect(page.locator("#photo")).to_have_js_property("complete", True)
        page.screenshot(path=str(evidence_dir / "offline-field-card.png"), full_page=True)
        guide = page.locator("#guide").text_content()
        assert "身体微侧，自然回眸微笑" in guide
        assert "V1闪光灯配八角柔光箱" in guide
        assert "后期路线：cleanup" in guide
        assert "清理杂乱背景路人" in guide
        assert page.locator("#photo").evaluate("img => img.naturalWidth") > 0
        context.set_offline(False)

        # 12. Backup, Restore, Doctor Integrity Check
        from ref_lab.cli import backup, doctor
        backup_zip = tmp_path / "backup.zip"
        report = backup(library, backup_zip)
        assert backup_zip.is_file()
        assert report["assets"] > 0

        restore_dir = tmp_path / "restored_data"
        restore_dir.mkdir(parents=True)
        with zipfile.ZipFile(backup_zip) as archive:
            archive.extractall(restore_dir)
        (restore_dir / "access-token").write_text(TOKEN, encoding="utf-8")

        restore_settings = Settings(restore_dir, TOKEN, public_origin="http://127.0.0.1")
        restored_lib = Library(restore_settings)
        doctor_report = doctor(restored_lib)
        assert doctor_report["ok"] is True
        assert doctor_report["database"] == "ok"
        assert len(doctor_report["missing_or_corrupt"]) == 0

        browser.close()

    server.should_exit = True
    thread.join(timeout=3)
    sock.close()
