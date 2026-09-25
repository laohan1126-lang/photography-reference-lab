#!/usr/bin/env python3
"""Build interactive Review Board for Live Edge / Pinterest Search Candidates (dist/review_live_search.html)."""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "staging/live_manifest.json"
OUTPUT_HTML = ROOT / "dist/review_live_search.html"
OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

DIRECTION_NAMES = {
    "A_STANDING": "A 基础立姿 (Standing)",
    "B_TURN_BACK": "B 回眸/背身 (Turn Back)",
    "C_HANDS_FACE": "C 情绪/手部特写 (Hands & Face)",
    "D_LOW_STOOL": "D 矮凳/坐姿 (Low Stool)",
    "E_PROP": "E 法杖/道具交互 (Prop & Staff)",
    "F_LOW_ANGLE": "F 广角低机位 (Low Angle)",
    "G_DYNAMIC": "G 动态/披风甩动 (Dynamic & Fabric)"
}

def build_live_review_board():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    # Sort items by direction then id
    items.sort(key=lambda x: (x.get("direction", ""), x.get("id", "")))

    cards_html = []
    dir_counts = {}
    for item in items:
        d = item.get("direction", "UNKNOWN")
        dir_counts[d] = dir_counts.get(d, 0) + 1

        cid = item["id"]
        rel_file = item["file"] # staging/live_downloads/E_PROP/...
        img_src = f"../{rel_file}"
        w = item.get("width", 0)
        h = item.get("height", 0)
        query = item.get("query", "")
        url = item.get("url", "#")
        pin_href = item.get("pin_href", "#")
        alt = item.get("alt", "")

        card = f"""
        <div class="cand-card" id="card-{cid}" data-id="{cid}" data-direction="{d}">
            <div class="card-img-wrap" onclick="viewFullImage('{img_src}', '{cid}', '{w}x{h}', '{html.escape(query)}')">
                <img src="{img_src}" alt="{cid}" loading="lazy">
                <span class="badge-id">{cid}</span>
                <span class="badge-q">{w}×{h}</span>
                <div class="user-choice-badge" id="badge-choice-{cid}"></div>
            </div>
            <div class="card-meta">
                <div class="direction-tag">{DIRECTION_NAMES.get(d, d)}</div>
                <div class="query-text">🔍 {html.escape(query)}</div>
                <div class="links-group">
                    <a href="{img_src}" target="_blank" class="meta-link">查看本地原图</a>
                    <a href="{url}" target="_blank" rel="noopener noreferrer" class="meta-link">CDN 直链</a>
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

    tab_buttons = ['<button class="tab-btn active" onclick="filterDirection(\'ALL\', this)">全部 ALL (' + str(total_count) + ')</button>']
    for d, title in DIRECTION_NAMES.items():
        cnt = dir_counts.get(d, 0)
        tab_buttons.append(f'<button class="tab-btn" onclick="filterDirection(\'{d}\', this)">{d.replace("_", " ")} ({cnt})</button>')

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edge 实时检索候选图人工审核看板 (Live Search HD Board)</title>
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
        .cand-card.state-reject:hover {{
            opacity: 0.85;
        }}
        .card-img-wrap {{
            width: 100%;
            height: 380px;
            background: #000;
            position: relative;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}
        .card-img-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }}
        .card-img-wrap:hover img {{
            transform: scale(1.03);
        }}
        .badge-id {{
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(0,0,0,0.8);
            border: 1px solid rgba(255,255,255,0.2);
            color: #fff;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
        .badge-q {{
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0,242,255,0.2);
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
        .direction-tag {{
            font-size: 12px;
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

        /* Lightbox modal */
        #lightbox {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.92);
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
            font-weight: 300;
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>Edge 实时 Pinterest 高清摄影参考候选看板 (Live HD Search)</h1>
            <p>183 张单人高清单图 | 覆盖 7 个方向 | 平均分辨率 713×1092 px (无拼图裁切)</p>
        </div>
        <div class="header-actions">
            <div class="stats-badge">已选: <span id="stat-keep" class="badge-keep-stat">0</span> KEEP | <span id="stat-maybe" class="badge-maybe-stat">0</span> MAYBE | <span id="stat-reject" class="badge-reject-stat">0</span> REJECT</div>
            <button class="btn-export" onclick="exportDecisions()">📥 导出审核决策结果 (JSON)</button>
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
        const decisions = {{}}; // id -> 'KEEP' | 'MAYBE' | 'REJECT'
        const LOCAL_STORAGE_KEY = 'live_search_pose_decisions';

        // Load cached decisions
        try {{
            const cached = localStorage.getItem(LOCAL_STORAGE_KEY);
            if (cached) {{
                const parsed = JSON.parse(cached);
                Object.assign(decisions, parsed);
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
            for (const [cid, choice] of Object.entries(decisions)) {{
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

        function filterDirection(dir, btn) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cards = document.querySelectorAll('.cand-card');
            cards.forEach(card => {{
                if (dir === 'ALL' || card.dataset.direction === dir) {{
                    card.style.display = 'flex';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function viewFullImage(src, cid, res, query) {{
            const lb = document.getElementById('lightbox');
            const img = document.getElementById('lightbox-img');
            const info = document.getElementById('lightbox-info');
            img.src = src;
            info.innerHTML = `<strong>${{cid}}</strong> | 分辨率: ${{res}} | 检索词: ${{query}}`;
            lb.classList.add('active');
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
            a.download = 'live_pose_decisions.json';
            a.click();
            URL.revokeObjectURL(url);
        }}

        // Keyboard shortcuts
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
    print(f"Built Live Review Board successfully: {OUTPUT_HTML} ({total_count} items)")

if __name__ == "__main__":
    build_live_review_board()
