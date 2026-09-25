#!/usr/bin/env python3
"""Automated Xiaohongshu (小红书) Cosplay Reference Collector via active BrowserSkill Edge session.

Navigates the user's connected Edge browser across targeted Honor of Kings and Anime Cosplay search queries,
opens notes, extracts exact full-resolution image currentSrc, naturalWidth, naturalHeight, author, and note URL,
and downloads them with WebP/JPEG validation into staging/xhs_downloads/.
"""

import base64
import io
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "staging/xhs_downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = ROOT / "staging/xhs_manifest.json"
CANDIDATES_JSONL = ROOT / "staging/candidates_xhs.jsonl"

SEARCH_PLAN = [
    {
        "category": "WANG_ZHAOJUN_HOK",
        "title": "王者荣耀·王昭君及同系法师神女Cos",
        "queries": [
            "王昭君cos 姿势",
            "王者荣耀cos 拍照姿势",
            "王昭君 乞巧织情 cos",
            "大乔 西施 貂蝉 cos 拍照",
            "神女cos 漫展姿势"
        ]
    },
    {
        "category": "PROP_AND_SCEPTER",
        "title": "法杖/手杖/道具二次元Cosplay",
        "queries": [
            "法杖 cos 拍照姿势",
            "手杖 cos 拍照姿势",
            "申鹤 cos 拍照姿势",
            "芙宁娜 cos 拍照姿势"
        ]
    },
    {
        "category": "CONVENTION_FIELD",
        "title": "漫展现场出片动作 (低机位/回眸/防人流)",
        "queries": [
            "漫展拍照姿势 女角色",
            "漫展出片 动作 cos",
            "漫展 仰拍 姿势 cos"
        ]
    }
]

def bsk_eval(session_id: str, js_code: str):
    res = subprocess.run(
        ["bsk.exe", "evaluate", "--session", session_id, "--json", js_code],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    if res.returncode != 0:
        return None
    try:
        data = json.loads(res.stdout)
        return data.get("value")
    except Exception:
        return None

def bsk_nav(session_id: str, url: str):
    res = subprocess.run(
        ["bsk.exe", "navigate", "--session", session_id, url, "--wait-until", "load", "--timeout", "35s"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    time.sleep(2.5)
    return res.returncode == 0

def download_image(url: str, dest_path: Path):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
            "Referer": "https://www.xiaohongshu.com/"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()
    
    with Image.open(io.BytesIO(content)) as im:
        im_rgb = im.convert("RGB")
        im_rgb.save(dest_path, "JPEG", quality=94)
        return im_rgb.size

def run_collector(session_id="dywg", max_notes_per_query=5, max_imgs_per_note=4):
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
    print(f"Starting Xiaohongshu Collector via BrowserSkill (Session: {session_id})")
    print("==================================================")

    for group in SEARCH_PLAN:
        cat = group["category"]
        cat_dir = OUT_DIR / cat
        cat_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n==========================================")
        print(f"Targeting: {group['title']} ({cat})")
        print(f"==========================================")

        for query in group["queries"]:
            print(f"\n--> [Search Query]: {query}")
            enc_q = urllib.parse.quote(query)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={enc_q}&source=web_search_result_notes"

            if not bsk_nav(session_id, search_url):
                print(f"    Navigation failed for {query}")
                continue

            time.sleep(3)

            # Scroll to load more cards
            bsk_eval(session_id, "window.scrollBy(0, 800);")
            time.sleep(1.5)

            # Extract note links
            extract_links_js = """
            (() => {
                const links = [];
                const notes = document.querySelectorAll('section.note-item, div.note-item');
                for (const n of notes) {
                    const a = n.querySelector('a');
                    const titleEl = n.querySelector('.title, .desc, .footer span');
                    const authorEl = n.querySelector('.author .name, .username');
                    if (a && a.href && a.href.includes('/explore/')) {
                        links.push({
                            url: a.href,
                            title: titleEl ? titleEl.innerText.trim() : '',
                            author: authorEl ? authorEl.innerText.trim() : ''
                        });
                    }
                }
                return links;
            })()
            """
            notes_found = bsk_eval(session_id, extract_links_js) or []
            print(f"    Discovered {len(notes_found)} explore note items.")

            # Deduplicate by url
            unique_notes = []
            seen_note_urls = set()
            for n in notes_found:
                if n["url"] not in seen_note_urls:
                    seen_note_urls.add(n["url"])
                    unique_notes.append(n)

            downloaded_in_query = 0
            for note_info in unique_notes[:max_notes_per_query]:
                note_url = note_info["url"]
                print(f"    -> Opening note: {note_url}")
                if not bsk_nav(session_id, note_url):
                    continue

                time.sleep(2.5)

                # Extract note images and metadata
                extract_note_js = """
                (() => {
                    const titleEl = document.querySelector('#detail-title, .title, .note-title');
                    const authorEl = document.querySelector('.author .name, .username, .author-container span');
                    const title = titleEl ? titleEl.innerText.trim() : '';
                    const author = authorEl ? authorEl.innerText.trim() : '';

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
                    return { title, author, imgs };
                })()
                """
                detail = bsk_eval(session_id, extract_note_js) or {}
                note_title = detail.get("title") or note_info["title"] or "小红书笔记"
                note_author = detail.get("author") or note_info["author"] or "未知创作者"
                note_imgs = detail.get("imgs") or []

                print(f"       Title: {note_title[:28]} | Author: {note_author} | Images: {len(note_imgs)}")

                note_saved = 0
                for img_it in note_imgs:
                    if note_saved >= max_imgs_per_note:
                        break
                    src = img_it["src"]
                    if src in seen_urls:
                        continue

                    cid = f"XHS_{cat}_{int(time.time()*10)%10000000}_{note_saved+1}"
                    out_path = cat_dir / f"{cid}.jpg"

                    try:
                        w, h = download_image(src, out_path)
                        if w < 400 or h < 500:
                            if out_path.exists():
                                out_path.unlink()
                            continue

                        rec = {
                            "id": cid,
                            "category": cat,
                            "category_title": group["title"],
                            "query": query,
                            "file": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                            "width": w,
                            "height": h,
                            "title": note_title,
                            "author": note_author,
                            "source_url": note_url,
                            "img_url": src
                        }
                        records.append(rec)
                        seen_urls.add(src)
                        note_saved += 1
                        downloaded_in_query += 1

                        # Append to jsonl
                        with open(CANDIDATES_JSONL, "a", encoding="utf-8") as jf:
                            jf.write(json.dumps(rec, ensure_ascii=False) + "\n")

                        print(f"       [✓] Downloaded: {cid}.jpg ({w}x{h})")
                    except Exception as err:
                        print(f"       [!] Download error: {err}")

            # Save manifest progressively
            with open(MANIFEST_PATH, "w", encoding="utf-8") as mf:
                json.dump(records, mf, indent=2, ensure_ascii=False)

    print(f"\n==========================================")
    print(f"Xiaohongshu Collection Finished! Total Saved: {len(records)}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"==========================================")

if __name__ == "__main__":
    run_collector(session_id="dywg", max_notes_per_query=4, max_imgs_per_note=3)
