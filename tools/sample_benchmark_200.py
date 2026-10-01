#!/usr/bin/env python3
"""Diagnostic script to sample 100 images for 有马加奈 and 100 images for 王者荣耀·西施
from Xiaohongshu via BrowserSkill, evaluated using the cosplay-reference-curator skill rules,
and generate interactive review boards for the user.
"""
from __future__ import annotations

import argparse
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
from collect_adapter import select_browserskill, compute_dhash

NEGATIVE_TYPE_MARKERS = (
    "游戏截图", "游戏画面", "游戏cg", "游戏 cg", "皮肤特效", "特效设计", "技能特效",
    "官方立绘", "立绘", "插画", "同人图", "同人画", "原画", "壁纸", "海报",
    "concept art", "illustration", "fanart", "fan art", "wallpaper", "render",
    "3d model", "3d模型", "建模", "模型展示", "皮肤展示", "角色展示",
    "商品图", "商品展示", "服装展示", "人台", "假人", "mannequin",
    "cos服", "c服", "出服", "求服", "转单", "闲鱼", "出租", "出物",
    "裙撑", "做裙", "做衣服", "打版", "材料", "剪裁", "缝纫", "代工", "假发",
    "求助", "怎么整理", "如何整理", "难打理", "整理教程", "穿戴教程",
    "制作教程", "改造教程", "收纳教程", "怎么穿", "怎么做",
    "哪家好", "避雷", "测评", "店铺", "手办", "雕像", "粘土",
    "大家都在搜", "连招", "出装", "铭文", "上分", "对局",
    "大全套", "换物", "免押金", "同人", "恶搞", "段子",
    "对比", "详细对比", "盘点", "版型", "体验馆", "一条龙", "骗钱", "跑路", "拍的什么东西", "挂人", "三视图", "各家"
)

POSITIVE_COSPLAY_MARKERS = (
    "cosplay", "coser", " cos ", "cos正片", "cos 正片", "正片", "场照",
    "返图", "出镜", "写真", "棚拍", "摄影", "漫展", "自拍", "出片", "拍了",
    "📷", "动作参考", "妆面", "毛娘", "试衣", "后期", "成片", "出cos",
    "姿势分享", "姿势", "捞捞", "客片", "约拍", "同框", "速报", "打卡"
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


def evaluate_candidate(title: str, author: str, full_text: str, img_bytes: bytes, target_config: dict) -> tuple[bool, str, str, str]:
    """Evaluates candidate against cosplay-reference-curator skill rules."""
    combined = f" {title.lower()} {author.lower()} {full_text.lower()} "
    
    # 1. Negative checks
    for marker in NEGATIVE_TYPE_MARKERS:
        if marker in combined:
            return False, f"负向标记排除: {marker}", "dropped", "negative"

    # 2. Image dimension checks (640x427, 640x360 landscape covers allowed; narrow banners rejected)
    dim_str = ""
    try:
        with Image.open(io.BytesIO(img_bytes)) as pil_img:
            w, h = pil_img.width, pil_img.height
            dim_str = f"{w}x{h}"
            if max(w, h) < 600 or min(w, h) < 240:
                return False, f"尺寸过小或为广告条: {dim_str}", "dropped", dim_str
    except Exception:
        return False, "无效图片格式", "dropped", ""

    # 3. Positive signal checks
    # Check character aliases / role lines
    has_char = any(alias.lower() in combined for alias in target_config["aliases"])
    has_line = any(line.lower() in combined for line in target_config.get("lines", []))
    has_cosplay = any(marker in combined for marker in POSITIVE_COSPLAY_MARKERS) or "cos" in combined

    if has_char or has_line:
        # If character or line is present, it's a solid candidate
        return True, "符合规则（命中角色/台词语义与画幅）", "kept", dim_str
    elif has_cosplay:
        # Search query already constrained the topic, so explicit cos/photo marker in query feed is accepted
        return True, "符合规则（搜索上下文+出片标记）", "kept", dim_str
    else:
        return False, "缺少角色或出片线索", "dropped", dim_str


def sample_target(target_key: str, count: int = 100):
    TARGETS = {
        "kana": {
            "name": "有马加奈",
            "work": "我推的孩子",
            "aliases": ["有马加奈", "加奈", "帽皇", "小苏打", "arima kana", "kana"],
            "lines": ["成为你的推之子", "十手巨星", "闪耀的红", "b小町", "苏打", "童星", "舔苏打"],
            "queries": [
                "我推的孩子 有马加奈 cos",
                "我推的孩子 有马加奈 cosplay",
                "有马加奈 cos 正片",
                "有马加奈 coser 摄影",
                "有马加奈 场照",
                "有马加奈 cos 返图",
                "有马加奈 B小町 cos",
                "有马加奈 漫展",
                "有马加奈 cos 姿势",
                "有马加奈 制服 cos"
            ],
            "output_dir": Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-arima-kana-100")
        },
        "xishi": {
            "name": "西施",
            "work": "王者荣耀",
            "aliases": ["西施", "施施", "西施王", "施宝", "西施妹妹", "诗语江南", "游龙清影", "乘鲤谣"],
            "lines": ["沉鱼", "寻宝", "听到了水的呼唤", "所有的相遇", "看更美的风景", "命中注定", "少女的秘密"],
            "queries": [
                "王者荣耀 西施 cos",
                "王者荣耀 西施 cosplay",
                "王者荣耀 西施 cos 正片",
                "西施 coser 摄影",
                "王者荣耀 西施 场照",
                "王者荣耀 西施 返图",
                "西施 诗语江南 cos",
                "西施 游龙清影 cos",
                "西施 cos 漫展",
                "王者荣耀 西施 摄影"
            ],
            "output_dir": Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-xishi-100")
        }
    }

    cfg = TARGETS[target_key]
    out_dir = cfg["output_dir"]
    img_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    bsk_bin, browser_id = select_browserskill()
    if not bsk_bin or not browser_id:
        print("Error: No BrowserSkill instance found.")
        return

    print(f"\n==================================================")
    print(f"开始采集: {cfg['name']} ({cfg['work']}) - 目标 {count} 张")
    print(f"输出目录: {out_dir}")
    print(f"==================================================")

    env = {**os.environ, "BSK_AUTO_START": "0"}
    start_p = subprocess.run([bsk_bin, "session", "start", "--browser", browser_id, "--json"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10)
    session_id = json.loads(start_p.stdout).get("session_id")
    if not session_id:
        print("Failed to start BrowserSkill session")
        return

    seen_urls: set[str] = set()
    seen_shas: set[str] = set()
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
        for q_idx, query in enumerate(cfg["queries"], 1):
            if len(records) >= count:
                break
            print(f"\n[{q_idx}/{len(cfg['queries'])}] 搜索小红书: {query} (当前已抓取: {len(records)}/{count})")
            xhs_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}"
            subprocess.run(
                [bsk_bin, "navigate", xhs_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=30
            )
            time.sleep(3.0)

            for scroll_round in range(5):
                if len(records) >= count:
                    break

                eval_p = subprocess.run([bsk_bin, "evaluate", "--session", session_id, "--json", extract_js],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=15)
                try:
                    raw = json.loads(eval_p.stdout)
                    cards = raw.get("value", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
                except Exception:
                    cards = []

                for card in cards:
                    if len(records) >= count:
                        break

                    img_url = card.get("image_url", "")
                    purl = card.get("purl", "")
                    if not img_url or img_url in seen_urls:
                        continue
                    seen_urls.add(img_url)

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

                    # Skill-based evaluation
                    is_kept, verdict_desc, verdict_class, dim_str = evaluate_candidate(title, author, full_text, img_bytes, cfg)
                    verdict = "KEPT" if is_kept else "DROPPED"

                    sample_idx = len(records) + 1
                    ext = "jpg"
                    img_filename = f"sample_{sample_idx:03d}_{sha[:8]}.{ext}"
                    (img_dir / img_filename).write_bytes(img_bytes)

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
                        "query": query
                    }
                    records.append(record_entry)
                    print(f"[{sample_idx:03d}/{count}] {verdict} - {title[:20]} | {verdict_desc} ({dim_str})")

                # Scroll down
                subprocess.run(
                    [bsk_bin, "evaluate", "--session", session_id, "--json", "window.scrollBy(0, 1600)"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10
                )
                time.sleep(2.5)

    finally:
        subprocess.run([bsk_bin, "session", "stop", session_id], capture_output=True, env=env)

    # Write manifest & index.html
    generate_board_html(records, out_dir, cfg["name"], cfg["work"])
    print(f"\n完成目标 [{cfg['name']}] 抽样: 共 {len(records)} 张图片已保存至 {out_dir}")


def generate_board_html(records: list[dict], output_dir: Path, target_name: str, target_work: str):
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
                <p class="verdict-reason"><strong>Skill裁决:</strong> {html.escape(r['verdict_desc'])}</p>
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
    <title>小红书采选 Skill 实测抽样（{target_name} · {target_work}）</title>
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
        <h1>{target_name}（{target_work}）小红书搜图实测样本（100 张）</h1>
        <p class="subtitle">
            基于新沉淀的 <code>cosplay-reference-curator</code> 审美法则进行全量抓取与裁决。<br>
            请勾选您认为<b>“应该被保留”</b>的图片，点击右侧按钮复制编号清单即可直接发给我，检验 Skill 的迁移准确度！
        </p>
        <div class="stats-bar">
            <span>总抽样样本: <strong>{len(records)}</strong> 张</span>
            <span style="color: #2e7d32;">Skill 判定保留: <strong>{kept_count}</strong> 张</span>
            <span style="color: #c62828;">Skill 判定排除: <strong>{dropped_count}</strong> 张</span>
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["kana", "xishi", "all"], default="all")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()

    if args.target == "all":
        sample_target("kana", args.count)
        sample_target("xishi", args.count)
    else:
        sample_target(args.target, args.count)

