#!/usr/bin/env python3
"""Diagnostic script to sample 100 NEW unique images for 王昭君·长夜焕生
from Xiaohongshu (and Pinterest if needed), strictly excluding the previous 30 samples,
and generate a rich interactive review dashboard for the user.
"""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import quote

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import collect_adapter
from collect_adapter import (
    build_policy, select_browserskill,
    result_metadata_allowed,
    validate_downloaded_image,
    compute_dhash, hamming_distance,
    fetch_xhs_detail_metadata
)

def fetch_image_in_browser(bsk_bin: str, session_id: str, img_url: str, env: dict) -> str | None:
    fetch_js = f"""(async () => {{
        try {{
            const resp = await fetch("{img_url}");
            const blob = await resp.blob();
            const reader = new FileReader();
            return await new Promise((resolve) => {{
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            }});
        }} catch (e) {{
            return null;
        }}
    }})()"""
    fetch_p = subprocess.run(
        [bsk_bin, "evaluate", "--session", session_id, "--json", fetch_js],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=12
    )
    try:
        val = json.loads(fetch_p.stdout).get("value")
        return val if (val and "," in val) else None
    except Exception:
        return None


def run_100_sampling(target_count: int = 100):
    output_dir = Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-changye-huansheng-100")
    images_dir = output_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load seen items from previous 30 batch to avoid ANY repetition
    seen_urls: set[str] = set()
    seen_shas: set[str] = set()
    seen_dhashes: list[str] = []

    prev_batch_file = Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-changye-huansheng\manifest.json")
    if prev_batch_file.is_file():
        try:
            prev_records = json.loads(prev_batch_file.read_text(encoding="utf-8"))
            for r in prev_records:
                if r.get("image_url"):
                    seen_urls.add(r["image_url"])
                if r.get("filename"):
                    # get sha if in name
                    f_parts = r["filename"].split("_")
                    if len(f_parts) >= 3:
                        seen_shas.add(f_parts[2].split(".")[0])
            print(f"Loaded {len(prev_records)} items from previous batch to exclude duplicates.")
        except Exception as e:
            print("Notice: could not load previous batch:", e)

    job = {
        "project_snapshot": {
            "character": "王昭君",
            "costume": "长夜焕生",
            "work": "王者荣耀"
        },
        "notes": "只找王昭君长夜焕生这个皮肤的真人COS正片。不要游戏截图、特效图、立绘、插画、C服商品展示、人台、制作教程、服装求助、店铺测评。"
    }
    policy = build_policy(job)

    queries = [
        "王者荣耀 王昭君 长夜焕生 cosplay 正片",
        "王者荣耀 王昭君 长夜焕生 coser 摄影",
        "王者荣耀 王昭君 长夜焕生 cos 返图",
        "王者荣耀 王昭君 长夜焕生 cos 场照",
        "王昭君 长夜焕生 cos",
        "王昭君 长夜焕生 cosplay",
        "长夜焕生 王昭君 正片",
        "长夜焕生 cos",
        "长夜焕生 王昭君 场照",
        "王昭君 长夜焕生 漫展",
        "王者荣耀 长夜焕生 cos"
    ]

    bsk_bin, browser_id = select_browserskill()
    if not bsk_bin or not browser_id:
        print("Error: No connected browser found via BrowserSkill.")
        return

    print(f"Using BrowserSkill: {bsk_bin}, Browser ID: {browser_id}")
    env = {**os.environ, "BSK_AUTO_START": "0"}

    start_p = subprocess.run([bsk_bin, "session", "start", "--browser", browser_id, "--json"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10)
    sess_data = json.loads(start_p.stdout)
    session_id = sess_data.get("session_id")
    if not session_id:
        print("Failed to start session:", sess_data)
        return

    print(f"Started session: {session_id}")
    sampled_records = []

    extract_js = """(() => {
        const cards = [];
        const items = document.querySelectorAll('section, div.note-item, div.search-card');
        for (const item of items) {
            const img = item.querySelector('img');
            const link = item.querySelector('a[href*="xsec_token"]')
                || item.querySelector('a[href*="/explore/"]')
                || item.querySelector('a[href*="/search_result/"]');
            const titleEl = item.querySelector('.title, .desc, a.title span, span.title') || item.querySelector('a:not(.user) span');
            const authorEl = item.querySelector('.author, .name, .user-name, a.user span');
            if (img && (img.currentSrc || img.src)) {
                const src = img.currentSrc || img.src;
                if (src.includes('xhscdn.com') && !src.includes('avatar') && img.naturalWidth >= 120) {
                    cards.push({
                        title: titleEl?.innerText?.trim() || img.alt?.trim() || '',
                        author: authorEl?.innerText?.trim() || '',
                        full_text: item.innerText?.trim() || '',
                        desc: titleEl?.innerText?.trim() || img.alt?.trim() || '',
                        purl: link?.href || location.href,
                        image_url: src,
                        width: img.naturalWidth,
                        height: img.naturalHeight
                    });
                }
            }
        }
        return cards;
    })()"""

    try:
        for q_idx, query in enumerate(queries, 1):
            if len(sampled_records) >= target_count:
                break
            print(f"\n[{q_idx}/{len(queries)}] 搜索小红书: {query} (当前进度: {len(sampled_records)}/{target_count})")
            xhs_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}"
            subprocess.run(
                [bsk_bin, "navigate", xhs_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=30
            )
            time.sleep(3.0)

            # Scroll multiple times to trigger lazy-loading of 60+ cards per query
            for scroll_round in range(5):
                if len(sampled_records) >= target_count:
                    break

                eval_p = subprocess.run([bsk_bin, "evaluate", "--session", session_id, "--json", extract_js],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=15)
                try:
                    raw = json.loads(eval_p.stdout)
                    cards = raw.get("value", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
                except Exception:
                    cards = []

                new_on_page = 0
                for card in cards:
                    if len(sampled_records) >= target_count:
                        break

                    img_url = card.get("image_url", "")
                    purl = card.get("purl", "")
                    if not img_url or img_url in seen_urls:
                        continue
                    seen_urls.add(img_url)

                    title = card.get("title", "")
                    author = card.get("author", "")
                    record = {
                        "t": title,
                        "desc": card.get("desc", ""),
                        "author": author,
                        "full_text": card.get("full_text", ""),
                        "purl": purl,
                    }

                    # Evaluate metadata filter under current rules
                    allowed, reason = result_metadata_allowed(record, policy)
                    detail_evidence = ""
                    # If ambiguous voiceline, check detail page if note url exists
                    if not allowed and reason == "needs_detail_evidence" and purl:
                        body, tags = fetch_xhs_detail_metadata(bsk_bin, session_id, purl, env)
                        detail_evidence = f"tags: {tags}, body: {body[:80]}"
                        record["detail_body"] = body
                        record["detail_tags"] = tags
                        allowed, reason = result_metadata_allowed(record, policy)

                    # Fetch image bytes
                    fetch_val = fetch_image_in_browser(bsk_bin, session_id, img_url, env)
                    if not fetch_val or not fetch_val.startswith("data:"):
                        continue

                    try:
                        img_bytes = base64.b64decode(fetch_val.split(",", 1)[1])
                    except Exception:
                        continue

                    sha = hashlib.sha256(img_bytes).hexdigest()
                    if sha in seen_shas:
                        continue
                    seen_shas.add(sha)

                    # Evaluate image validation
                    valid_img, ext, dhash_or_err = validate_downloaded_image(img_bytes, policy)
                    img_dim_str = ""
                    try:
                        with Image.open(io.BytesIO(img_bytes)) as pil_img:
                            img_dim_str = f"{pil_img.width}x{pil_img.height}"
                    except Exception:
                        pass

                    if allowed and valid_img:
                        verdict = "KEPT"
                        verdict_desc = "符合当前规则（入选）"
                        verdict_class = "kept"
                    else:
                        verdict = "DROPPED"
                        verdict_class = "dropped"
                        reasons = []
                        if not allowed:
                            reasons.append(f"文本排除: {reason}")
                        if not valid_img:
                            reasons.append(f"尺寸/画幅排除: {dhash_or_err} ({img_dim_str})")
                        verdict_desc = "；".join(reasons)

                    sample_idx = len(sampled_records) + 1
                    img_filename = f"sample_{sample_idx:03d}_{sha[:8]}.{ext or 'jpg'}"
                    img_path = images_dir / img_filename
                    img_path.write_bytes(img_bytes)

                    sample_entry = {
                        "index": sample_idx,
                        "filename": img_filename,
                        "title": title or "未命名笔记",
                        "author": author,
                        "page_url": purl,
                        "image_url": img_url,
                        "dimensions": img_dim_str,
                        "verdict": verdict,
                        "verdict_desc": verdict_desc,
                        "verdict_class": verdict_class,
                        "meta_reason": reason,
                        "detail_evidence": detail_evidence,
                        "query": query
                    }
                    sampled_records.append(sample_entry)
                    new_on_page += 1
                    print(f"[{sample_idx:03d}/{target_count}] {verdict} - {title[:20]} | {verdict_desc}")

                # Scroll down to load more cards
                subprocess.run(
                    [bsk_bin, "evaluate", "--session", session_id, "--json", "window.scrollBy(0, 1600)"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10
                )
                time.sleep(2.5)

    finally:
        subprocess.run([bsk_bin, "session", "stop", session_id], capture_output=True, env=env)

    # Generate rich HTML report
    generate_html_report(sampled_records, output_dir)
    print(f"\nFinished sampling {len(sampled_records)} new images.")
    print(f"Review report saved to: {output_dir / 'index.html'}")


def generate_html_report(records: list[dict], output_dir: Path):
    kept_count = sum(1 for r in records if r["verdict"] == "KEPT")
    dropped_count = sum(1 for r in records if r["verdict"] == "DROPPED")

    cards_html = []
    for r in records:
        badge_style = "background: #2e7d32; color: white;" if r["verdict"] == "KEPT" else "background: #c62828; color: white;"
        card = f"""
        <div class="card {r['verdict_class']}" id="card-{r['index']}">
            <div class="card-header">
                <span class="index-badge">#{r['index']:03d}</span>
                <span class="status-badge" style="{badge_style}">【{r['verdict']}】</span>
            </div>
            <div class="img-box">
                <a href="images/{r['filename']}" target="_blank">
                    <img src="images/{r['filename']}" alt="{html.escape(r['title'])}" loading="lazy" />
                </a>
            </div>
            <div class="info">
                <h4 title="{html.escape(r['title'])}">{html.escape(r['title'])}</h4>
                <p class="meta"><strong>作者:</strong> {html.escape(r['author'])} | <strong>尺寸:</strong> {r['dimensions']}</p>
                <p class="verdict-reason"><strong>系统判定:</strong> {html.escape(r['verdict_desc'])}</p>
                <div class="links">
                    <a href="{html.escape(r['page_url'])}" target="_blank" class="xhs-link">打开小红书原笔记 ↗</a>
                </div>
                <div class="feedback-box">
                    <label>
                        <input type="checkbox" class="should-keep-check" data-index="{r['index']}"> <strong>保留这张</strong>
                    </label>
                </div>
            </div>
        </div>
        """
        cards_html.append(card)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>小红书搜图实物 100 张诊断抽样（王昭君·长夜焕生）</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; margin: 0; padding: 20px; color: #222; }}
        header {{ max-width: 1500px; margin: 0 auto 20px; background: white; padding: 20px 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); position: sticky; top: 10px; z-index: 100; }}
        h1 {{ margin: 0 0 10px; font-size: 22px; }}
        p.subtitle {{ margin: 0 0 12px; color: #666; font-size: 14px; line-height: 1.5; }}
        .stats-bar {{ display: flex; gap: 20px; font-size: 14px; padding: 8px 15px; background: #f0f4f8; border-radius: 8px; margin-bottom: 12px; }}
        .feedback-summary {{ background: #fff8e1; border: 1px solid #ffe082; padding: 12px 18px; border-radius: 8px; font-size: 14px; display: flex; align-items: center; justify-content: space-between; }}
        .filter-toggles {{ margin-top: 10px; display: flex; gap: 10px; }}
        .filter-btn {{ padding: 6px 14px; border: 1px solid #ccc; background: white; border-radius: 6px; cursor: pointer; font-size: 13px; }}
        .filter-btn.active {{ background: #1976d2; color: white; border-color: #1976d2; }}
        .grid {{ max-width: 1500px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }}
        .card {{ background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; border: 2px solid transparent; }}
        .card.kept {{ border-color: #a5d6a7; }}
        .card.dropped {{ border-color: #ffcdd2; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #fafafa; border-bottom: 1px solid #eee; }}
        .index-badge {{ font-weight: bold; font-size: 15px; color: #333; }}
        .status-badge {{ font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; }}
        .img-box {{ height: 300px; background: #111; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
        .img-box img {{ max-width: 100%; max-height: 100%; object-fit: contain; cursor: pointer; }}
        .info {{ padding: 12px; flex: 1; display: flex; flex-direction: column; }}
        .info h4 {{ margin: 0 0 6px; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .meta {{ margin: 0 0 6px; font-size: 12px; color: #777; }}
        .verdict-reason {{ margin: 0 0 10px; font-size: 12px; color: #444; background: #f8f9fa; padding: 6px 8px; border-radius: 6px; line-height: 1.4; flex: 1; }}
        .links {{ margin-bottom: 8px; }}
        .xhs-link {{ font-size: 12px; color: #1976d2; text-decoration: none; }}
        .xhs-link:hover {{ text-decoration: underline; }}
        .feedback-box {{ border-top: 1px dashed #ddd; padding-top: 8px; }}
        .feedback-box label {{ cursor: pointer; font-size: 13px; color: #d32f2f; }}
    </style>
</head>
<body>
    <header>
        <h1>王昭君·长夜焕生 真实搜图样本诊断清单（100 张不重复新样本）</h1>
        <p class="subtitle">
            本批次已完全排除上一轮的 30 张图，通过滚动翻页在小红书采集了 100 张不重复新图片。<br>
            请勾选您认为<b>“应该被系统保留”</b>的图片，点击右侧按钮复制编号清单即可直接发给我！
        </p>
        <div class="stats-bar">
            <span>总抽样样本: <strong>{len(records)}</strong> 张</span>
            <span style="color: #2e7d32;">当前规则判定保留: <strong>{kept_count}</strong> 张</span>
            <span style="color: #c62828;">当前规则判定排除: <strong>{dropped_count}</strong> 张</span>
        </div>
        <div class="feedback-summary">
            <div>
                <strong>已选应保留项：</strong> <span id="selected-list" style="color: #d32f2f; font-weight: bold;">尚未勾选</span>
            </div>
            <div>
                <button onclick="copyFeedback()" style="padding: 6px 14px; background: #1976d2; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">一键复制选中的编号</button>
            </div>
        </div>
        <div class="filter-toggles">
            <button class="filter-btn active" onclick="filterDisplay('all', this)">显示全部 (100)</button>
            <button class="filter-btn" onclick="filterDisplay('dropped', this)">只看系统淘汰 ({dropped_count})</button>
            <button class="filter-btn" onclick="filterDisplay('kept', this)">只看系统保留 ({kept_count})</button>
        </div>
    </header>

    <div class="grid" id="card-grid">
        {''.join(cards_html)}
    </div>

    <script>
        function updateFeedback() {{
            const checked = Array.from(document.querySelectorAll('.should-keep-check:checked')).map(el => '#' + el.dataset.index.padStart(3, '0'));
            const text = checked.length > 0 ? checked.join(', ') : '尚未勾选';
            document.getElementById('selected-list').textContent = text;
        }}
        document.querySelectorAll('.should-keep-check').forEach(el => {{
            el.addEventListener('change', updateFeedback);
        }});
        function copyFeedback() {{
            const text = document.getElementById('selected-list').textContent;
            if (text === '尚未勾选') {{
                alert('请先勾选您认为应该保留的图片');
                return;
            }}
            navigator.clipboard.writeText(text).then(() => alert('已复制选中的编号：' + text));
        }}
        function filterDisplay(mode, btn) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                if (mode === 'all') card.style.display = 'flex';
                else if (mode === 'kept') card.style.display = card.classList.contains('kept') ? 'flex' : 'none';
                else if (mode === 'dropped') card.style.display = card.classList.contains('dropped') ? 'flex' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
    (output_dir / "index.html").write_text(html_content, encoding="utf-8")
    (output_dir / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_100_sampling(count)

