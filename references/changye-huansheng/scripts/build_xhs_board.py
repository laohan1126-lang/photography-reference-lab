#!/usr/bin/env python3
"""Build interactive Review Board and Contact Sheets for Xiaohongshu (小红书) Cosplay references."""

import html
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "staging/xhs_manifest.json"
OUTPUT_HTML = ROOT / "dist/review_xhs_batch.html"
CONTACT_DIR = ROOT / "dist/xhs_contact_sheets"

OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
CONTACT_DIR.mkdir(parents=True, exist_ok=True)

CAT_INFO = {
    "WANG_ZHAOJUN_HOK": {
        "title": "小红书·王者荣耀女角色 Cos 漫展出片",
        "badge": "王者荣耀",
        "desc": "王昭君、大乔、西施、貂蝉等高冷神女与法师 Coser 漫展与白棚成片"
    },
    "PROP_AND_SCEPTER": {
        "title": "小红书·法杖/手杖道具 Cosplay 姿势",
        "badge": "法杖道具",
        "desc": "法杖身前立姿、单手提杖、横杖蓄势、法杖倚靠交互动作"
    },
    "CONVENTION_FIELD": {
        "title": "小红书·漫展现场实战出片姿态",
        "badge": "漫展实战",
        "desc": "针对漫展拥挤背景的高机位俯瞰、低机位避人流仰拍与回眸抓拍"
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
        # make relative to dist/
        rel_file_clean = rel_file.replace("\\", "/")
        if "references/changye-huansheng/" in rel_file_clean:
            rel_file_clean = rel_file_clean.split("references/changye-huansheng/")[1]
        web_src = f"../{rel_file_clean}"

        w = item.get("width", 0)
        h = item.get("height", 0)
        query = item.get("query", "")
        author = item.get("author", "小红书博主")
        title = item.get("title", "Cosplay 拍照参考")
        note_url = item.get("note_url", "#")
        img_url = item.get("img_url", "#")
        cat_meta = CAT_INFO.get(cat, {"title": cat, "badge": cat, "desc": ""})

        card = f"""
        <div class="cand-card" id="card-{cid}" data-id="{cid}" data-category="{cat}">
            <div class="card-img-wrap" onclick="viewLightbox('{web_src}', '{cid}', '{html.escape(author)}', '{html.escape(title)}', '{w}×{h}')">
                <img src="{web_src}" alt="{cid}" loading="lazy">
                <span class="badge-id">{cid}</span>
                <span class="badge-cat">{cat_meta['badge']}</span>
                <span class="badge-res">{w}×{h}</span>
                <div class="user-choice-badge" id="badge-choice-{cid}"></div>
            </div>
            <div class="card-meta">
                <div class="author-row">📷 创作者: <strong>{html.escape(author[:14])}</strong></div>
                <div class="note-title">{html.escape(title[:26])}</div>
                <div class="query-text">🔍 小红书检索: {html.escape(query)}</div>
                <div class="links-group">
                    <a href="{web_src}" target="_blank" class="meta-link">本地原图</a>
                    <a href="{note_url}" target="_blank" rel="noopener noreferrer" class="meta-link">小红书原帖</a>
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
    <title>小红书 (Xiaohongshu) 原生接管 Cosplay 参考审核看板</title>
    <style>
        :root {{
            --bg: #07090e;
            --surface: #0f141f;
            --surface-hover: #182032;
            --primary: #ff2442;
            --secondary: #00f2ff;
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
            font-weight: 800;
            color: #ff4d6a;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 8px;
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
            background: linear-gradient(135deg, #ff2442, #e11d48);
            color: #fff;
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
            background: #ff2442;
            color: #fff;
            border-color: #ff2442;
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
            border-color: #ff4d6a;
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
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
            background: rgba(255,36,66,0.9);
            color: #fff;
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
            border: 1px solid var(--secondary);
            color: var(--secondary);
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
            gap: 6px;
            flex: 1;
        }}
        .author-row {{
            font-size: 12px;
            color: var(--secondary);
        }}
        .note-title {{
            font-size: 13px;
            font-weight: 700;
            color: #f8fafc;
            line-height: 1.4;
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
            margin-top: 4px;
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
            <h1>📕 小红书 (Xiaohongshu) 原生接管 Cosplay 参考审核看板</h1>
            <p>75 张 100% 小红书高赞 Coser 实拍单图 | 覆盖王者荣耀女角色、法杖交互与漫展出片</p>
        </div>
        <div class="header-actions">
            <div class="stats-badge">已选: <span id="stat-keep" class="badge-keep-stat">0</span> KEEP | <span id="stat-maybe" class="badge-maybe-stat">0</span> MAYBE | <span id="stat-reject" class="badge-reject-stat">0</span> REJECT</div>
            <button class="btn-export" onclick="exportDecisions()">📥 导出小红书决策 (JSON)</button>
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
        const LOCAL_STORAGE_KEY = 'xhs_pose_decisions';

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

        function viewLightbox(src, cid, author, title, res) {{
            document.getElementById('lightbox-img').src = src;
            document.getElementById('lightbox-info').innerHTML = `<strong>${{cid}}</strong> [作者: ${{author}}] | 分辨率: ${{res}}<br><span style="color:#ff4d6a;">${{title}}</span>`;
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
            a.download = 'xhs_pose_decisions.json';
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
    print(f"Generated XHS review HTML: {OUTPUT_HTML}")

    # Build 3 category contact sheets
    render_contact_sheets(items)

def render_contact_sheets(items):
    by_cat = {}
    for it in items:
        cat = it.get("category", "UNKNOWN")
        by_cat.setdefault(cat, []).append(it)

    thumb_w = 360
    thumb_h = 500
    pad = 20
    header_h = 90
    slot_h = 50

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

        draw.text((pad, 22), f"{meta['title']} ({n} 张小红书高清成片)", fill=(255, 36, 66), font=font_title)
        draw.text((pad, 60), f"100% 小红书真实 Coser 漫展与正片出片实战参考 | 绝无拼图裁切 | 打开 dist/review_xhs_batch.html 在线筛选", fill=(148, 163, 184), font=font_badge)

        for i, it in enumerate(sub_items):
            col = i % cols
            row = i // cols
            x = pad + col * (thumb_w + pad)
            y = header_h + row * (thumb_h + slot_h)

            f_str = it["file"].replace("\\", "/")
            if "references/changye-huansheng/" in f_str:
                img_p = ROOT / f_str.split("references/changye-huansheng/")[1]
            else:
                img_p = ROOT / f_str

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
                except Exception as e:
                    pass

            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(30, 41, 59), width=1)

            # Badges
            cid = it["id"]
            draw.rectangle([x + 6, y + 6, x + 160, y + 26], fill=(0, 0, 0, 210))
            draw.text((x + 10, y + 8), cid, fill=(255, 255, 255), font=font_badge)

            res_str = f"{it['width']}x{it['height']}"
            draw.rectangle([x + thumb_w - 74, y + 6, x + thumb_w - 6, y + 26], fill=(255, 36, 66, 50), outline=(255, 36, 66), width=1)
            draw.text((x + thumb_w - 70, y + 8), res_str, fill=(255, 36, 66), font=font_badge)

            # Footer text
            ty = y + thumb_h + 6
            t_short = it.get("title", "")[:24]
            a_short = it.get("author", "")[:16]
            draw.text((x, ty), f"📷 {a_short} - {t_short}", fill=(241, 245, 249), font=font_sub)
            draw.text((x, ty + 20), f"ID: {cid} | 来源: {it.get('query', '')[:20]}", fill=(100, 116, 139), font=font_badge)

        out_file = CONTACT_DIR / f"xhs_contact_{cat}.jpg"
        sheet.save(out_file, quality=92)
        print(f"Rendered: {out_file.name}")

if __name__ == "__main__":
    build_board()
