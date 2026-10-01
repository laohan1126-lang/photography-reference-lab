#!/usr/bin/env python3
"""Diagnostic script to sample 100 images for the ultra-popular topic: JK (JK制服 / 日系人像摄影)
from Xiaohongshu via BrowserSkill, evaluated using the cosplay-reference-curator skill rules,
and generate an interactive review dashboard to inspect the yield rate (良率).
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

from collect_adapter import select_browserskill

# Negative markers tailored for JK photography (purging clothes sales, genuine/replica debates, buyer rants)
JK_NEGATIVE_MARKERS = (
    "山正", "正统", "盗版", "店铺推荐", "哪家好", "避雷", "测评", "店铺",
    "出格裙", "转单", "闲鱼", "出租", "出物", "求物", "换物", "拼单", "包邮", "预售", "现货",
    "打版", "材料", "做衣服", "收纳", "教程", "怎么穿", "领结推荐", "裙长",
    "大家都在搜", "开箱", "对比", "详细对比", "盘点", "版型", "骗钱", "跑路", "挂人",
    "商品图", "人台", "假人", "平铺", "白底图"
)

# Positive markers indicating real photography / pose / mood references
JK_POSITIVE_MARKERS = (
    "摄影", "客片", "拍照姿势", "动作参考", "正片", "写真", "外景", "情绪", "日系",
    "胶片", "光影", "校园", "教室", "逆光", "出片", "拍了", "📷", "姿势", "摆姿",
    "放学", "夏日", "雨天", "天台", "操场", "互勉", "约拍", "成片", "速报"
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


def evaluate_jk_candidate(title: str, author: str, full_text: str, img_bytes: bytes) -> tuple[bool, str, str, str, str]:
    combined = f" {title.lower()} {author.lower()} {full_text.lower()} "

    # 1. Negative gate: Purge sales, buyer reviews, shop comparisons
    for marker in JK_NEGATIVE_MARKERS:
        if marker in combined:
            return False, f"负向杂质排除: {marker}", "dropped", "negative", "无"

    # 2. Physical & Quality gate
    dim_str = ""
    try:
        with Image.open(io.BytesIO(img_bytes)) as pil_img:
            w, h = pil_img.width, pil_img.height
            dim_str = f"{w}x{h}"
            if max(w, h) < 600 or min(w, h) < 240:
                return False, f"尺寸不合规范/广告条: {dim_str}", "dropped", dim_str, "无"
    except Exception:
        return False, "无效图片格式", "dropped", "", "无"

    # 3. Positive Aesthetic & Photography Value
    aesthetic_tag = "基础参考"
    has_photo_signal = any(m in combined for m in JK_POSITIVE_MARKERS)
    
    if any(m in combined for m in ("拍照姿势", "动作参考", "姿势", "摆姿", "动态感")):
        aesthetic_tag = "动作姿势参考"
    elif any(m in combined for m in ("逆光", "光影", "胶片", "夜景", "天台", "蓝天", "雨天")):
        aesthetic_tag = "场景光影大片"
    elif any(m in combined for m in ("情绪", "特写", "日系写真", "神态")):
        aesthetic_tag = "情绪日系写真"
    elif has_photo_signal:
        aesthetic_tag = "真实摄影成片"

    if has_photo_signal or "jk" in combined:
        return True, f"符合摄影参考规则（{aesthetic_tag}）", "kept", dim_str, aesthetic_tag
    else:
        return False, "缺少摄影或出片特征", "dropped", dim_str, "无"


def sample_jk(target_count: int = 100):
    output_dir = Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-jk-100")
    images_dir = output_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    queries = [
        "jk 拍照姿势 摄影",
        "jk 动作参考",
        "jk 正片 摄影",
        "jk 日系写真 客片",
        "jk 外景 摄影",
        "jk 情绪摄影",
        "jk 校园摄影 出片",
        "jk 胶片 逆光",
        "jk 摄影参考"
    ]

    bsk_bin, browser_id = select_browserskill()
    if not bsk_bin or not browser_id:
        print("Error: No connected browser found via BrowserSkill.")
        return

    print(f"==================================================")
    print(f"开始大热门话题抽样: JK制服 / 日系摄影 (目标: {target_count} 张)")
    print(f"输出目录: {output_dir}")
    print(f"==================================================")

    env = {**os.environ, "BSK_AUTO_START": "0"}
    start_p = subprocess.run([bsk_bin, "session", "start", "--browser", browser_id, "--json"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10)
    session_id = json.loads(start_p.stdout).get("session_id")
    if not session_id:
        print("Failed to start session:", start_p.stdout)
        return

    seen_urls: set[str] = set()
    seen_tokens: set[str] = set()
    seen_shas: set[str] = set()
    seen_dhashes: list[str] = []
    records: list[dict] = []

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
            if len(records) >= target_count:
                break
            print(f"\n[{q_idx}/{len(queries)}] 搜索小红书: {query} (当前进度: {len(records)}/{target_count})")
            xhs_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}"
            subprocess.run(
                [bsk_bin, "navigate", xhs_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=30
            )
            time.sleep(3.0)

            for scroll_round in range(5):
                if len(records) >= target_count:
                    break

                eval_p = subprocess.run([bsk_bin, "evaluate", "--session", session_id, "--json", extract_js],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=15)
                try:
                    raw = json.loads(eval_p.stdout)
                    cards = raw.get("value", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
                except Exception:
                    cards = []

                for card in cards:
                    if len(records) >= target_count:
                        break

                    img_url = card.get("image_url", "")
                    purl = card.get("purl", "")
                    if not img_url or img_url in seen_urls:
                        continue
                    token_m = re.search(r'([0-9a-zA-Z]{32,})', img_url)
                    img_token = token_m.group(1) if token_m else img_url.split("?")[0]
                    if img_token in seen_tokens:
                        continue
                    seen_tokens.add(img_token)

                    title = card.get("title", "")
                    author = card.get("author", "")
                    full_text = card.get("full_text", "")

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

                    from collect_adapter import compute_dhash, hamming_distance
                    try:
                        with Image.open(io.BytesIO(img_bytes)) as pil_chk:
                            cur_dh = compute_dhash(pil_chk)
                            if any(hamming_distance(cur_dh, pdh) <= 4 for pdh in seen_dhashes):
                                continue
                            seen_dhashes.append(cur_dh)
                    except Exception:
                        pass

                    is_kept, verdict_desc, verdict_class, dim_str, tag = evaluate_jk_candidate(title, author, full_text, img_bytes)
                    verdict = "KEPT" if is_kept else "DROPPED"

                    sample_idx = len(records) + 1
                    img_filename = f"sample_{sample_idx:03d}_{sha[:8]}.jpg"
                    (images_dir / img_filename).write_bytes(img_bytes)

                    record_entry = {
                        "index": sample_idx,
                        "filename": img_filename,
                        "title": title or "未命名笔记",
                        "author": author,
                        "page_url": purl,
                        "image_url": img_url,
                        "dimensions": dim_str,
                        "verdict": verdict,
                        "verdict_desc": verdict_desc,
                        "verdict_class": verdict_class,
                        "tag": tag,
                        "query": query
                    }
                    records.append(record_entry)
                    print(f"[{sample_idx:03d}/{target_count}] {verdict} [{tag}] - {title[:22]} | {verdict_desc}")

                subprocess.run(
                    [bsk_bin, "evaluate", "--session", session_id, "--json", "window.scrollBy(0, 1600)"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10
                )
                time.sleep(2.5)

    finally:
        subprocess.run([bsk_bin, "session", "stop", session_id], capture_output=True, env=env)

    generate_jk_html(records, output_dir)
    print(f"\n完成 JK 抽样: 共 {len(records)} 张图片已保存至 {output_dir}")


def generate_jk_html(records: list[dict], output_dir: Path):
    kept_count = sum(1 for r in records if r["verdict"] == "KEPT")
    dropped_count = sum(1 for r in records if r["verdict"] == "DROPPED")
    yield_rate = f"{(kept_count / len(records) * 100):.1f}%" if records else "0%"

    cards_html = []
    for r in records:
        badge_style = "background: #2e7d32; color: white;" if r["verdict"] == "KEPT" else "background: #c62828; color: white;"
        tag_badge = f'<span style="background: #e3f2fd; color: #1565c0; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px;">{r["tag"]}</span>' if r["tag"] != "无" else ""
        card = f"""
        <div class="card {r['verdict_class']}" id="card-{r['index']}">
            <div class="card-header">
                <div>
                    <span class="index-badge">#{r['index']:03d}</span>
                    {tag_badge}
                </div>
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
                <p class="verdict-reason"><strong>Skill判定:</strong> {html.escape(r['verdict_desc'])}</p>
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
    <title>JK制服 / 日系摄影 实测 100 张良率检验看板</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f8; margin: 0; padding: 20px; color: #222; }}
        header {{ max-width: 1500px; margin: 0 auto 20px; background: white; padding: 20px 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); position: sticky; top: 10px; z-index: 100; }}
        h1 {{ margin: 0 0 10px; font-size: 22px; }}
        p.subtitle {{ margin: 0 0 12px; color: #666; font-size: 14px; line-height: 1.5; }}
        .stats-bar {{ display: flex; gap: 25px; font-size: 15px; padding: 10px 18px; background: #f0f4f8; border-radius: 8px; margin-bottom: 12px; }}
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
        <h1>JK制服 / 日系日常人像摄影 实测 100 张良率检验看板</h1>
        <p class="subtitle">
            检验基于【四层漏斗摄影审美引擎】在大热门、大流量人像摄影品类下的实际表现与良率。<br>
            观察其对“商业买家秀/转单测评/山正争端”等杂质的净化能力，以及对“动态摆姿/光影氛围/情绪写真”的提纯效果。
        </p>
        <div class="stats-bar">
            <span>总抽样样本: <strong>{len(records)}</strong> 张</span>
            <span style="color: #2e7d32;">Skill 判定保留: <strong>{kept_count}</strong> 张</span>
            <span style="color: #c62828;">Skill 判定淘汰: <strong>{dropped_count}</strong> 张</span>
            <span style="color: #1565c0; font-weight: bold;">综合良率 (Yield Rate): <strong>{yield_rate}</strong></span>
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
            <button class="filter-btn active" onclick="filterDisplay('all', this)">显示全部 ({len(records)})</button>
            <button class="filter-btn" onclick="filterDisplay('kept', this)">只看 Skill 保留 ({kept_count})</button>
            <button class="filter-btn" onclick="filterDisplay('dropped', this)">只看 Skill 淘汰 ({dropped_count})</button>
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
    sample_jk(count)

