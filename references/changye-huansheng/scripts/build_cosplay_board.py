#!/usr/bin/env python3
"""Build interactive Review Board & Contact Sheets for the 102 Anime & Honor of Kings Cosplay References."""

import html
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "staging/cosplay_manifest.json"
OUTPUT_HTML = ROOT / "dist/review_cosplay_batch.html"
CONTACT_DIR = ROOT / "dist/cosplay_contact_sheets"

OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
CONTACT_DIR.mkdir(parents=True, exist_ok=True)

CAT_INFO = {
    "WANG_ZHAOJUN_HOK": {
        "title": "王者荣耀·王昭君及同系法师神女 (Honor of Kings Cos)",
        "badge": "王者荣耀",
        "desc": "王昭君、乞巧织情、西施、貂蝉、大乔、甄姬高冷神女漫展与正片出片姿态"
    },
    "ANIME_SCEPTER_GODDESS": {
        "title": "二次元动漫法杖/神女高冷Cos (Anime Goddess & Scepter)",
        "badge": "动漫神女/法杖",
        "desc": "申鹤、芙宁娜手杖、镜流冷冽剑姿及二次元高雅持杖姿态"
    },
    "CONVENTION_FIELD_POSES": {
        "title": "漫展现场实战出片姿势 (Convention Field Photography)",
        "badge": "漫展实战",
        "desc": "漫展现场避开人流的低机位大仰拍、背身回眸、斗篷布料甩动实战姿势"
    }
}

def build_board():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    cards_html = []
    cat_counts = {}
    for item in items:
        cat = item.get("category", "UNKNOWN")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

        cid = item["id"]
        rel_file = item["file"]
        web_src = f"../{rel_file}"
        w = item.get("width", 0)
        h = item.get("height", 0)
        query = item.get("query", "")
        url = item.get("url", "#")
        pin_href = item.get("pin_href", "#")
        cat_meta = CAT_INFO.get(cat, {"title": cat, "badge": cat, "desc": ""})

        card = f"""
        <div class="cand-card" id="card-{cid}" data-id="{cid}" data-category="{cat}">
            <div class="card-img-wrap" onclick="viewLightbox('{web_src}', '{cid}', '{cat_meta['title']}', '{query}', '{w}×{h}')">
                <img src="{web_src}" alt="{cid}" loading="lazy">
                <span class="badge-id">{cid}</span>
                <span class="badge-cat">{cat_meta['badge']}</span>
                <span class="badge-res">{w}×{h}</span>
                <div class="user-choice-badge" id="badge-choice-{cid}"></div>
            </div>
            <div class="card-meta">
                <div class="cat-title">{cat_meta['title']}</div>
                <div class="query-text">🔍 检索来源: {html.escape(query)}</div>
                <div class="links-group">
                    <a href="{web_src}" target="_blank" class="meta-link">查看本地高清大图</a>
                    <a href="{url}" target="_blank" rel="noopener noreferrer" class="meta-link">CDN 原图</a>
                </div>
                <div class="action-buttons">
                    <button class="btn-decision btn-keep" onclick="setDecision('{cid}', 'KEEP')">✓ 保留 (KEEP)</button>
                    <button class="btn-decision btn-maybe" onclick="setDecision('{cid}', 'MAYBE')">? 待定 (MAYBE)</button>
                    <button class="btn-decision btn-reject" onclick="setDecision('{cid}', 'REJECT')">✕ 淘汰 (REJECT)</button>
                </div>
            </div>
        </div>
        """
        cards_html.append(card)

    total_count = len(items)

    tab_buttons = ['<button class="tab-btn active" onclick="filterCategory(\'ALL\', this)">全部 ALL (' + str(total_count) + ')</button>']
    for cat, meta in CAT_INFO.items():
        cnt = cat_counts.get(cat, 0)
        tab_buttons.append(f'<button class="tab-btn" onclick="filterCategory(\'{cat}\', this)">{meta["badge"]} ({cnt})</button>')

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王者荣耀与动漫 Cosplay 专精摄影参考审核看板 (Anime & HOK Cosplay Board)</title>
    <style>
        :root {{
            --bg: #07090e;
            --surface: #0f141f;
            --surface-hover: #182032;
            --primary: #00f2ff;
            --text-main: #f1f5f9;
            --text-dim: #94a3b8;
            --border: #1e293b;
            --keep-color: #10b981;
            --maybe-color: #f59e0b;
            --reject-color: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-title h1 {{
            font-size: 20px;
            font-weight: 700;
            color: var(--primary);
            letter-spacing: 0.5px;
        }}
        .header-title p {{
            font-size: 13px;
            color: var(--text-dim);
            margin-top: 4px;
        }}
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .stats-badge {{
            background: #182032;
            border: 1px solid var(--border);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .stats-badge span {{ font-weight: 700; }}
        .badge-keep-stat {{ color: var(--keep-color); }}
        .badge-maybe-stat {{ color: var(--maybe-color); }}
        .badge-reject-stat {{ color: var(--reject-color); }}
        .btn-export {{
            background: linear-gradient(135deg, #00f2ff, #0284c7);
            color: #000;
            border: none;
            padding: 8px 18px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-export:hover {{
            filter: brightness(1.15);
            transform: translateY(-1px);
        }}
        .filter-bar {{
            background: #0b0f17;
            border-bottom: 1px solid var(--border);
            padding: 10px 24px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .tab-btn {{
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab-btn:hover {{
            background: var(--surface);
            color: var(--text-main);
        }}
        .tab-btn.active {{
            background: var(--primary);
            color: #000;
            border-color: var(--primary);
            font-weight: 700;
        }}
        .grid-container {{
            padding: 24px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            flex: 1;
        }}
        .cand-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }}
        .cand-card:hover {{
            border-color: #3b82f6;
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        }}
        .cand-card.state-keep {{
            border: 2px solid var(--keep-color);
            background: #061912;
        }}
        .cand-card.state-maybe {{
            border: 2px solid var(--maybe-color);
            background: #1c1503;
        }}
        .cand-card.state-reject {{
            border: 2px solid var(--reject-color);
            opacity: 0.35;
        }}
        .card-img-wrap {{
            width: 100%;
            height: 380px;
            background: #000;
            position: relative;
            cursor: pointer;
            overflow: hidden;
        }}
        .card-img-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }}
        .card-img-wrap:hover img {{
            transform: scale(1.04);
        }}
        .badge-id {{
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(0,0,0,0.85);
            border: 1px solid rgba(255,255,255,0.2);
            color: #fff;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
        .badge-cat {{
            position: absolute;
            bottom: 8px;
            left: 8px;
            background: rgba(0,242,255,0.85);
            color: #000;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
        .badge-res {{
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0,0,0,0.8);
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .user-choice-badge {{
            position: absolute;
            bottom: 8px;
            right: 8px;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            display: none;
        }}
        .state-keep .user-choice-badge {{
            display: block;
            background: var(--keep-color);
            color: #fff;
        }}
        .state-maybe .user-choice-badge {{
            display: block;
            background: var(--maybe-color);
            color: #000;
        }}
        .state-reject .user-choice-badge {{
            display: block;
            background: var(--reject-color);
            color: #fff;
        }}
        .card-meta {{
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            flex: 1;
        }}
        .cat-title {{
            font-size: 12.5px;
            font-weight: 700;
            color: var(--primary);
        }}
        .query-text {{
            font-size: 11px;
            color: var(--text-dim);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .links-group {{
            display: flex;
            gap: 12px;
            font-size: 12px;
        }}
        .meta-link {{
            color: #38bdf8;
            text-decoration: none;
        }}
        .meta-link:hover {{
            text-decoration: underline;
        }}
        .action-buttons {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 6px;
            margin-top: 8px;
        }}
        .btn-decision {{
            border: 1px solid var(--border);
            padding: 6px 0;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            background: #141c2c;
            color: #e2e8f0;
            transition: all 0.15s;
        }}
        .btn-decision:hover {{
            filter: brightness(1.25);
        }}
        .btn-keep:hover, .state-keep .btn-keep {{
            background: var(--keep-color);
            color: #fff;
            border-color: var(--keep-color);
        }}
        .btn-maybe:hover, .state-maybe .btn-maybe {{
            background: var(--maybe-color);
            color: #000;
            border-color: var(--maybe-color);
        }}
        .btn-reject:hover, .state-reject .btn-reject {{
            background: var(--reject-color);
            color: #fff;
            border-color: var(--reject-color);
        }}

        /* Lightbox */
        #lightbox {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.94);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            padding: 20px;
        }}
        #lightbox.active {{
            display: flex;
        }}
        #lightbox-img {{
            max-width: 90vw;
            max-height: 85vh;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            object-fit: contain;
        }}
        #lightbox-info {{
            margin-top: 14px;
            font-size: 14px;
            color: #cbd5e1;
            text-align: center;
        }}
        .lightbox-close {{
            position: absolute;
            top: 24px;
            right: 28px;
            color: #fff;
            font-size: 32px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>👑 王者荣耀与动漫 Cosplay 专精摄影参考审核看板</h1>
            <p>102 张 100% 动漫 & 王者女角色 Cosplay 单人高清单图 | 彻底剔除欧美商业大片 | 聚焦漫展实战出片</p>
        </div>
        <div class="header-actions">
            <div class="stats-badge">已选: <span id="stat-keep" class="badge-keep-stat">0</span> KEEP | <span id="stat-maybe" class="badge-maybe-stat">0</span> MAYBE | <span id="stat-reject" class="badge-reject-stat">0</span> REJECT</div>
            <button class="btn-export" onclick="exportDecisions()">📥 导出审核决策 (JSON)</button>
        </div>
    </header>

    <div class="filter-bar">
        {''.join(tab_buttons)}
    </div>

    <div class="grid-container" id="cards-grid">
        {''.join(cards_html)}
    </div>

    <div id="lightbox" onclick="closeLightbox(event)">
        <span class="lightbox-close" onclick="closeLightbox(event)">&times;</span>
        <img id="lightbox-img" src="" alt="Full view">
        <div id="lightbox-info"></div>
    </div>

    <script>
        const decisions = {{}};
        const LOCAL_STORAGE_KEY = 'cosplay_pose_decisions';

        try {{
            const cached = localStorage.getItem(LOCAL_STORAGE_KEY);
            if (cached) {{
                Object.assign(decisions, JSON.parse(cached));
                applyAllDecisions();
            }}
        }} catch(e) {{}}

        function setDecision(cid, choice) {{
            if (decisions[cid] === choice) {{
                delete decisions[cid];
            }} else {{
                decisions[cid] = choice;
            }}
            updateCardUI(cid);
            saveDecisions();
            updateStats();
        }}

        function updateCardUI(cid) {{
            const card = document.getElementById('card-' + cid);
            if (!card) return;
            card.classList.remove('state-keep', 'state-maybe', 'state-reject');
            const choice = decisions[cid];
            const badge = document.getElementById('badge-choice-' + cid);
            if (choice) {{
                card.classList.add('state-' + choice.toLowerCase());
                badge.innerText = choice;
            }} else {{
                badge.innerText = '';
            }}
        }}

        function applyAllDecisions() {{
            for (const cid of Object.keys(decisions)) {{
                updateCardUI(cid);
            }}
            updateStats();
        }}

        function updateStats() {{
            let k = 0, m = 0, r = 0;
            for (const c of Object.values(decisions)) {{
                if (c === 'KEEP') k++;
                if (c === 'MAYBE') m++;
                if (c === 'REJECT') r++;
            }}
            document.getElementById('stat-keep').innerText = k;
            document.getElementById('stat-maybe').innerText = m;
            document.getElementById('stat-reject').innerText = r;
        }}

        function saveDecisions() {{
            try {{
                localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(decisions));
            }} catch(e) {{}}
        }}

        function filterCategory(cat, btn) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cards = document.querySelectorAll('.cand-card');
            cards.forEach(card => {{
                if (cat === 'ALL' || card.dataset.category === cat) {{
                    card.style.display = 'flex';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function viewLightbox(src, cid, catTitle, query, res) {{
            document.getElementById('lightbox-img').src = src;
            document.getElementById('lightbox-info').innerHTML = `<strong>${{cid}}</strong> [${{catTitle}}] | 分辨率: ${{res}}<br><span style="color:#38bdf8;">检索词: ${{query}}</span>`;
            document.getElementById('lightbox').classList.add('active');
        }}

        function closeLightbox(e) {{
            if (e.target.id === 'lightbox' || e.target.classList.contains('lightbox-close')) {{
                document.getElementById('lightbox').classList.remove('active');
            }}
        }}

        function exportDecisions() {{
            const keeps = [];
            const maybes = [];
            const rejects = [];
            for (const [id, choice] of Object.entries(decisions)) {{
                if (choice === 'KEEP') keeps.push(id);
                if (choice === 'MAYBE') maybes.push(id);
                if (choice === 'REJECT') rejects.push(id);
            }}
            const data = {{
                exported_at: new Date().toISOString(),
                summary: {{ keep: keeps.length, maybe: maybes.length, reject: rejects.length }},
                keep_ids: keeps,
                maybe_ids: maybes,
                reject_ids: rejects,
                all_decisions: decisions
            }};
            const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cosplay_pose_decisions.json';
            a.click();
            URL.revokeObjectURL(url);
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                document.getElementById('lightbox').classList.remove('active');
            }}
        }});
    </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Generated review HTML: {OUTPUT_HTML}")

    # Build 3 category contact sheets
    render_contact_sheets(items)

def render_contact_sheets(items):
    by_cat = {}
    for it in items:
        cat = it.get("category", "UNKNOWN")
        by_cat.setdefault(cat, []).append(it)

    thumb_w = 360
    thumb_h = 520
    pad = 20
    header_h = 90
    slot_h = 45

    try:
        font_title = ImageFont.truetype("msyh.ttc", 28)
        font_badge = ImageFont.truetype("msyh.ttc", 11)
        font_sub = ImageFont.truetype("msyh.ttc", 13)
    except:
        font_title = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    for cat, sub_items in by_cat.items():
        meta = CAT_INFO.get(cat, {"title": cat, "badge": cat, "desc": ""})
        n = len(sub_items)
        cols = 4
        rows = math.ceil(n / cols)

        tw = cols * thumb_w + (cols + 1) * pad
        th = header_h + rows * (thumb_h + slot_h) + pad

        sheet = Image.new("RGB", (tw, th), color=(7, 9, 14))
        draw = ImageDraw.Draw(sheet)

        draw.text((pad, 22), f"{meta['title']} ({n} 张单人高清单图)", fill=(0, 242, 255), font=font_title)
        draw.text((pad, 60), f"专为漫展实战摄影精选 | 杜绝拼图裁切 | 打开 dist/review_cosplay_batch.html 进行在线点选", fill=(148, 163, 184), font=font_badge)

        for i, it in enumerate(sub_items):
            col = i % cols
            row = i // cols
            x = pad + col * (thumb_w + pad)
            y = header_h + row * (thumb_h + slot_h)

            img_p = ROOT / it["file"]
            if img_p.exists():
                try:
                    with Image.open(img_p) as im:
                        rgb = im.convert("RGB")
                        cr = rgb.width / rgb.height
                        tr = thumb_w / thumb_h
                        if cr > tr:
                            nw = int(rgb.height * tr)
                            off = (rgb.width - nw) // 2
                            crop = rgb.crop((off, 0, off + nw, rgb.height))
                        else:
                            nh = int(rgb.width / tr)
                            off = (rgb.height - nh) // 2
                            crop = rgb.crop((0, off, rgb.width, off + nh))
                        resz = crop.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                        sheet.paste(resz, (x, y))
                except:
                    pass

            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(30, 41, 59), width=1)

            # Badges
            cid = it["id"]
            draw.rectangle([x + 6, y + 6, x + 160, y + 26], fill=(0, 0, 0, 210))
            draw.text((x + 10, y + 8), cid, fill=(255, 255, 255), font=font_badge)

            res_str = f"{it['width']}x{it['height']}"
            draw.rectangle([x + thumb_w - 74, y + 6, x + thumb_w - 6, y + 26], fill=(0, 242, 255, 40), outline=(0, 242, 255), width=1)
            draw.text((x + thumb_w - 70, y + 8), res_str, fill=(0, 242, 255), font=font_badge)

            # Footer text
            ty = y + thumb_h + 6
            q_short = it.get("query", "")[:28]
            draw.text((x, ty), f"🔍 {q_short}", fill=(226, 232, 240), font=font_sub)
            draw.text((x, ty + 20), f"ID: {cid}", fill=(100, 116, 139), font=font_badge)

        out_file = CONTACT_DIR / f"cosplay_contact_{cat}.jpg"
        sheet.save(out_file, quality=92)
        print(f"Rendered: {out_file.name}")

if __name__ == "__main__":
    build_board()
