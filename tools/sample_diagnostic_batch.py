#!/usr/bin/env python3
"""Diagnostic script to sample up to 30 candidate images from Xiaohongshu
and record the exact filter decisions (kept vs dropped and why) into a standalone review folder.
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
    build_policy, build_queries, select_browserskill,
    result_metadata_allowed,
    validate_downloaded_image, wait_for_cards,
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

def run_diagnostic_sampling(target_sample_count: int = 30, output_dir: Path | None = None):
    output_dir = output_dir or Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-changye-huansheng")
    images_dir = output_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    job = {
        "project_snapshot": {
            "character": "王昭君",
            "costume": "长夜焕生",
            "work": "王者荣耀"
        },
        "notes": "只找王昭君长夜焕生这个皮肤的真人COS正片。不要游戏截图、特效图、立绘、插画、C服商品展示、人台、制作教程、服装求助、店铺测评。"
    }
    policy = build_policy(job)
    browser_queries = build_queries(job, for_browser=True)

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
    seen_urls = set()
    seen_shas = set()

    try:
        for query in browser_queries:
            if len(sampled_records) >= target_sample_count:
                break
            print(f"\n--- Searching: {query} ---")
            xhs_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}"
            subprocess.run(
                [bsk_bin, "navigate", xhs_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=30
            )
            time.sleep(3.5)

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
                        if (src.includes('xhscdn.com') && !src.includes('avatar') && img.naturalWidth >= 150) {
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

            cards = wait_for_cards(bsk_bin, session_id, extract_js, env)
            print(f"Observed {len(cards)} cards on page.")

            for card in cards:
                if len(sampled_records) >= target_sample_count:
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
                if not allowed and reason == "needs_detail_evidence" and purl:
                    body, tags = fetch_xhs_detail_metadata(bsk_bin, session_id, purl, env)
                    detail_evidence = f"tags: {tags}, body: {body[:100]}"
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

                # Evaluate image dimension filter
                valid_img, ext, dhash_or_err = validate_downloaded_image(img_bytes, policy)
                
                # Image dimensions
                img_dim_str = ""
                try:
                    with Image.open(io.BytesIO(img_bytes)) as pil_img:
                        img_dim_str = f"{pil_img.width}x{pil_img.height}"
                except Exception:
                    pass

                # Final verdict under current system
                if allowed and valid_img:
                    verdict = "KEPT"
                    verdict_desc = "符合当前规则，会被保留进参考池"
                    verdict_class = "kept"
                else:
                    verdict = "DROPPED"
                    verdict_class = "dropped"
                    reasons = []
                    if not allowed:
                        reasons.append(f"文本初筛排除: {reason}")
                    if not valid_img:
                        reasons.append(f"图像尺寸/比例不符: {dhash_or_err} ({img_dim_str})")
                    verdict_desc = "；".join(reasons)

                sample_idx = len(sampled_records) + 1
                img_filename = f"sample_{sample_idx:02d}_{sha[:8]}.{ext or 'jpg'}"
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
                print(f"[{sample_idx:02d}/{target_sample_count}] {verdict} - {title[:20]} | {verdict_desc}")

    finally:
        subprocess.run([bsk_bin, "session", "stop", session_id], capture_output=True, env=env)

    # Generate HTML review page
    generate_html_report(sampled_records, output_dir)
    print(f"\nFinished sampling {len(sampled_records)} images.")
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
                <span class="index-badge">#{r['index']:02d}</span>
                <span class="status-badge" style="{badge_style}">【系统判定: {r['verdict']}】</span>
            </div>
            <div class="img-box">
                <a href="images/{r['filename']}" target="_blank">
                    <img src="images/{r['filename']}" alt="{html.escape(r['title'])}" loading="lazy" />
                </a>
            </div>
            <div class="info">
                <h4 title="{html.escape(r['title'])}">{html.escape(r['title'])}</h4>
                <p class="meta"><strong>作者:</strong> {html.escape(r['author'])} | <strong>尺寸:</strong> {r['dimensions']}</p>
                <p class="verdict-reason"><strong>系统原因:</strong> {html.escape(r['verdict_desc'])}</p>
                <div class="links">
                    <a href="{html.escape(r['page_url'])}" target="_blank" class="xhs-link">打开小红书原笔记 ↗</a>
                </div>
                <div class="feedback-box">
                    <label>
                        <input type="checkbox" class="should-keep-check" data-index="{r['index']}"> <strong>这张应该保留</strong>
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
    <title>小红书搜图实物诊断抽样（王昭君·长夜焕生）</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; margin: 0; padding: 20px; color: #222; }}
        header {{ max-width: 1400px; margin: 0 auto 20px; background: white; padding: 20px 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        h1 {{ margin: 0 0 10px; font-size: 22px; }}
        p.subtitle {{ margin: 0 0 15px; color: #666; font-size: 14px; line-height: 1.5; }}
        .stats-bar {{ display: flex; gap: 20px; font-size: 14px; padding: 10px 15px; background: #f0f4f8; border-radius: 8px; margin-bottom: 15px; }}
        .feedback-summary {{ background: #fff8e1; border: 1px solid #ffe082; padding: 12px 18px; border-radius: 8px; font-size: 14px; margin-top: 10px; }}
        .grid {{ max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; border: 2px solid transparent; transition: transform 0.15s; }}
        .card:hover {{ transform: translateY(-2px); }}
        .card.kept {{ border-color: #a5d6a7; }}
        .card.dropped {{ border-color: #ffcdd2; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: #fafafa; border-bottom: 1px solid #eee; }}
        .index-badge {{ font-weight: bold; font-size: 15px; color: #333; }}
        .status-badge {{ font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; }}
        .img-box {{ height: 320px; background: #111; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
        .img-box img {{ max-width: 100%; max-height: 100%; object-fit: contain; cursor: pointer; }}
        .info {{ padding: 12px; flex: 1; display: flex; flex-direction: column; }}
        .info h4 {{ margin: 0 0 6px; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .meta {{ margin: 0 0 8px; font-size: 12px; color: #777; }}
        .verdict-reason {{ margin: 0 0 10px; font-size: 12px; color: #444; background: #f8f9fa; padding: 6px 8px; border-radius: 6px; line-height: 1.4; flex: 1; }}
        .links {{ margin-bottom: 10px; }}
        .xhs-link {{ font-size: 12px; color: #1976d2; text-decoration: none; }}
        .xhs-link:hover {{ text-decoration: underline; }}
        .feedback-box {{ border-top: 1px dashed #ddd; padding-top: 8px; }}
        .feedback-box label {{ cursor: pointer; font-size: 13px; color: #d32f2f; }}
    </style>
</head>
<body>
    <header>
        <h1>王昭君·长夜焕生 真实搜图样本诊断清单 (共 {len(records)} 张)</h1>
        <p class="subtitle">
            本批次完全通过 Edge 与小红书真实搜索抓取，保存在本地诊断文件夹中（未混入正式角色库）。<br>
            您可以在下方查验每一张图，并勾选您认为<b>“本应保留但被系统筛除”</b>的图片。页面底部会实时生成所选编号，您直接发给 Agent 即可快速排查优化！
        </p>
        <div class="stats-bar">
            <span>总抓取样本: <strong>{len(records)}</strong> 张</span>
            <span style="color: #2e7d32;">当前规则判定保留: <strong>{kept_count}</strong> 张</span>
            <span style="color: #c62828;">当前规则判定排除: <strong>{dropped_count}</strong> 张</span>
        </div>
        <div class="feedback-summary" id="feedback-bar">
            <strong>已选应保留项：</strong> <span id="selected-list">尚未勾选</span>
            <button onclick="copyFeedback()" style="margin-left: 15px; padding: 4px 10px; cursor: pointer;">复制编号清单</button>
        </div>
    </header>

    <div class="grid">
        {''.join(cards_html)}
    </div>

    <script>
        function updateFeedback() {{
            const checked = Array.from(document.querySelectorAll('.should-keep-check:checked')).map(el => '#' + el.dataset.index.padStart(2, '0'));
            const text = checked.length > 0 ? checked.join(', ') : '尚未勾选';
            document.getElementById('selected-list').textContent = text;
        }}
        document.querySelectorAll('.should-keep-check').forEach(el => {{
            el.addEventListener('change', updateFeedback);
        }});
        function copyFeedback() {{
            const text = document.getElementById('selected-list').textContent;
            navigator.clipboard.writeText(text).then(() => alert('已复制：' + text));
        }}
    </script>
</body>
</html>
"""
    (output_dir / "index.html").write_text(html_content, encoding="utf-8")
    (output_dir / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_diagnostic_sampling(count)

