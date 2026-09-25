#!/usr/bin/env python3
"""Interactive Xiaohongshu (小红书) Cosplay Reference Collector via Visible Edge.

Features:
- Launches visible Microsoft Edge on your desktop using persistent profile (data/edge_xhs_profile).
- Prompts for QR scan on first run; once scanned, session is saved permanently for subsequent runs.
- Searches targeted Cosplay keywords: 王者荣耀cos, 王昭君cos, 漫展拍照姿势, 法杖cos.
- Extracts native 1080x1440+ full images (currentSrc), note title, author, and note URL without collage slicing.
"""

import base64
import io
import json
import time
import urllib.parse
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "staging/xhs_downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = ROOT / "staging/xhs_manifest.json"
PROFILE_DIR = ROOT / "data/edge_xhs_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_QUERIES = [
    "王者荣耀cos 拍照姿势",
    "王昭君cos 姿势",
    "王者荣耀cos 漫展出片",
    "法杖 cos 拍照姿势",
    "大乔 西施 cos 拍照",
    "漫展拍照姿势 女角色"
]

def check_login(page) -> bool:
    try:
        # If user avatar or user center exists, logged in
        user_element = page.query_selector(".user.side-bar-component, .avatar-wrapper, .channel-container")
        login_modal = page.query_selector(".login-container, .qrcode-img, .login-modal")
        return user_element is not None and login_modal is None
    except Exception:
        return False

def run_xhs_collector(max_notes_per_query=6, max_imgs_per_note=4):
    existing = []
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    seen_urls = {x.get("url") for x in existing}
    records = list(existing)

    print("==================================================")
    print("Launching Visible Edge for Xiaohongshu Collector")
    print(f"Profile directory: {PROFILE_DIR}")
    print("==================================================")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 950}
        )
        page = context.new_page()

        # Check explore page first
        page.goto("https://www.xiaohongshu.com/explore", timeout=40000)
        time.sleep(3)

        if not check_login(page):
            print("\n[!] 小红书当前未登录。请在打开的 Edge 浏览器窗口中使用小红书 App 扫描二维码登录...")
            print("[*] 等待扫码完成（最长等待 90 秒）...")
            start_wait = time.time()
            while time.time() - start_wait < 90:
                time.sleep(3)
                if check_login(page):
                    print("--> [✓] 登录成功！已保存会话凭据。")
                    break
            else:
                print("[!] 未检测到扫码登录，将尝试继续进行公开内容检索...")

        for q in SEARCH_QUERIES:
            print(f"\n==========================================")
            print(f"Searching Xiaohongshu: {q}")
            print(f"==========================================")
            encoded = urllib.parse.quote(q)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded}&source=web_search_result_notes"

            try:
                page.goto(search_url, timeout=30000)
                time.sleep(4)

                # Collect note cards
                note_links = page.evaluate("""
                    () => {
                        const items = [];
                        const links = document.querySelectorAll('section.note-item a, div.note-item a');
                        for (const a of links) {
                            const href = a.href || '';
                            if (href.includes('/explore/') || href.includes('/search_result/')) {
                                const titleEl = a.querySelector('.title, .desc, span');
                                const title = titleEl ? titleEl.innerText.trim() : '';
                                items.push({ href: href, title: title });
                            }
                        }
                        return items;
                    }
                """)

                print(f"Found {len(note_links)} note cards.")
                # Deduplicate by href
                unique_notes = []
                seen_notes = set()
                for n in note_links:
                    if n["href"] not in seen_notes and "/explore/" in n["href"]:
                        seen_notes.add(n["href"])
                        unique_notes.append(n)

                print(f"Unique explore notes: {len(unique_notes)}")

                for n_idx, note_info in enumerate(unique_notes[:max_notes_per_query], 1):
                    n_url = note_info["href"]
                    print(f"  --> Opening note [{n_idx}]: {n_url}")
                    try:
                        note_page = context.new_page()
                        note_page.goto(n_url, timeout=25000)
                        time.sleep(3)

                        # Extract author, note title, and image currentSrc
                        note_meta = note_page.evaluate("""
                            () => {
                                const authorEl = document.querySelector('.author .name, .username, .author-container span');
                                const author = authorEl ? authorEl.innerText.trim() : '未知作者';
                                const titleEl = document.querySelector('#detail-title, .title');
                                const title = titleEl ? titleEl.innerText.trim() : '';
                                
                                const imgs = [];
                                const imgEls = document.querySelectorAll('.media-container img, .swiper-slide img, .note-slider img, .note-content img');
                                for (const im of imgEls) {
                                    const src = im.currentSrc || im.src || '';
                                    if (src && !src.includes('avatar') && !src.includes('icon')) {
                                        imgs.push({
                                            src: src,
                                            w: im.naturalWidth || 0,
                                            h: im.naturalHeight || 0
                                        });
                                    }
                                }
                                return { author, title, imgs };
                            }
                        """)

                        author = note_meta.get("author", "未知作者")
                        title = note_meta.get("title", note_info["title"])
                        imgs = note_meta.get("imgs", [])
                        print(f"      Author: {author} | Title: {title[:25]} | Found {len(imgs)} imgs")

                        downloaded_note_imgs = 0
                        for img_item in imgs:
                            if downloaded_note_imgs >= max_imgs_per_note:
                                break
                            img_src = img_item["src"]
                            if img_src in seen_urls:
                                continue

                            # Fetch image as base64 in browser
                            b64 = note_page.evaluate("""
                                async (url) => {
                                    try {
                                        const res = await fetch(url);
                                        if (!res.ok) return null;
                                        const blob = await res.blob();
                                        return new Promise((resolve) => {
                                            const r = new FileReader();
                                            r.onloadend = () => resolve(r.result);
                                            r.readAsDataURL(blob);
                                        });
                                    } catch(e) { return null; }
                                }
                            """, img_src)

                            if not b64 or not b64.startswith("data:image"):
                                continue

                            header, enc = b64.split(",", 1)
                            bdata = base64.b64decode(enc)

                            try:
                                with Image.open(io.BytesIO(bdata)) as pimg:
                                    w, h = pimg.size
                                    if w < 400 or h < 500:
                                        continue

                                    cid = f"XHS_COS_{int(time.time()*10)%10000000}_{downloaded_note_imgs+1}"
                                    fpath = OUT_DIR / f"{cid}.jpg"
                                    pimg.convert("RGB").save(fpath, "JPEG", quality=94)

                                    rec = {
                                        "id": cid,
                                        "platform": "xiaohongshu",
                                        "query": q,
                                        "file": str(fpath.relative_to(ROOT)).replace("\\", "/"),
                                        "width": w,
                                        "height": h,
                                        "title": title,
                                        "author": author,
                                        "source_url": n_url,
                                        "img_src": img_src
                                    }
                                    records.append(rec)
                                    seen_urls.add(img_src)
                                    downloaded_note_imgs += 1
                                    print(f"      [OK] Saved: {cid}.jpg ({w}x{h})")
                            except Exception as e:
                                print(f"      [Err] Img fail: {e}")

                        note_page.close()

                    except Exception as note_err:
                        print(f"      [Err] Failed to open note: {note_err}")

            except Exception as q_err:
                print(f"    [Err] Query {q} failed: {q_err}")

        context.close()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\nCompleted! Total Xiaohongshu Cosplay records: {len(records)}")

if __name__ == "__main__":
    run_xhs_collector(max_notes_per_query=5)
