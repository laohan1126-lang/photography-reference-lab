#!/usr/bin/env python3
"""Build interactive Pose Candidate Review Board (dist/review_pose_candidates.html)."""

import html
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CAND_YAML = ROOT / "data/pose_candidates.yaml"
OUTPUT_HTML = ROOT / "dist/review_pose_candidates.html"
OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

def build_review_board():
    with open(CAND_YAML, "r", encoding="utf-8") as f:
        candidates = yaml.safe_load(f)

    cards_html = []
    for c in candidates:
        cid = c["candidate_id"]
        rel_file = c["file"] # e.g. candidates/CAND_001.webp
        img_src = f"../{rel_file}"
        w = c.get("width", 0)
        h = c.get("height", 0)
        obs = c.get("observed_pose", "")
        direction = c.get("direction", "")
        tags = c.get("tags", [])
        q_flag = c.get("quality_flag", "HQ")
        status = c.get("review_status", "CANDIDATE")
        author = c.get("author", "未知")
        url = c.get("source_url", "#")

        tags_html = " ".join(f'<span class="tag-pill">#{html.escape(t)}</span>' for t in tags)

        card = f"""
        <div class="cand-card" id="card-{cid}" data-id="{cid}" data-direction="{direction}" data-status="{status}" data-quality="{q_flag}">
            <div class="card-img-wrap" onclick="viewFullImage('{img_src}', '{cid}')">
                <img src="{img_src}" alt="{cid}" loading="lazy">
                <span class="badge-id">{cid}</span>
                <span class="badge-status status-{status}">{status}</span>
                <span class="badge-q q-{q_flag}">{q_flag} ({w}×{h})</span>
                <div class="user-choice-badge" id="badge-choice-{cid}"></div>
            </div>
            <div class="card-meta">
                <div class="direction-tag">{direction.replace('_', ' ')}</div>
                <div class="tags-row">{tags_html}</div>
                <div class="obs-text">{html.escape(obs)}</div>
                <div class="author-row">
                    <span>📷 {html.escape(author[:16])}</span>
                    <div class="links-group">
                        <a href="{url}" target="_blank" rel="noopener noreferrer" class="meta-link">来源原帖</a>
                        <a href="{img_src}" target="_blank" class="meta-link">原图</a>
                    </div>
                </div>
                <div class="action-buttons">
                    <button class="btn-decision btn-keep" onclick="setDecision('{cid}', 'KEEP')">✓ KEEP 保留</button>
                    <button class="btn-decision btn-maybe" onclick="setDecision('{cid}', 'MAYBE')">? MAYBE 待定</button>
                    <button class="btn-decision btn-reject" onclick="setDecision('{cid}', 'REJECT')">✕ 淘汰</button>
                </div>
            </div>
        </div>
        """
        cards_html.append(card)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王昭君·长夜焕生 漫展姿势候选人工评审板 (POSE CANDIDATE REVIEW)</title>
    <style>
        :root {{
            --bg-main: #060c18;
            --bg-card: #0b1528;
            --bg-nav: #0d1a33;
            --border: #1e293b;
            --cyan: #00f2ff;
            --blue: #38bdf8;
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-main);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            padding: 20px;
            min-height: 100vh;
        }}
        /* Sticky Top Navigation & Review Header */
        .top-nav {{
            position: sticky;
            top: 10px;
            z-index: 100;
            background: rgba(13, 26, 51, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid #1e3a5f;
            border-radius: 12px;
            padding: 14px 20px;
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        }}
        .nav-row-1 {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .brand-box {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-title {{
            font-size: 18px;
            font-weight: 800;
            color: var(--cyan);
            letter-spacing: 0.5px;
        }}
        .nav-links {{
            display: flex;
            gap: 8px;
        }}
        .nav-btn {{
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 6px;
            text-decoration: none;
            color: var(--text-muted);
            border: 1px solid var(--border);
            background: #101e38;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .nav-btn:hover {{ color: #fff; border-color: var(--cyan); }}
        .nav-btn.active {{ background: #0369a1; color: #fff; border-color: var(--cyan); }}

        /* Counters & Export */
        .review-stats {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .stat-badge {{
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            border: 1px solid transparent;
        }}
        .stat-keep {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.4); }}
        .stat-maybe {{ background: rgba(234, 179, 8, 0.15); color: #facc15; border-color: rgba(234, 179, 8, 0.4); }}
        .stat-reject {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.4); }}
        .stat-unreviewed {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border-color: rgba(148, 163, 184, 0.3); }}

        .btn-export {{
            background: linear-gradient(135deg, #0284c7, #00f2ff);
            color: #041026;
            font-weight: 800;
            border: none;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            transition: opacity 0.2s, transform 0.1s;
        }}
        .btn-export:hover {{ opacity: 0.9; transform: scale(1.02); }}

        /* Filters Row */
        .filters-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            padding-top: 4px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }}
        .filter-label {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
            margin-right: 4px;
        }}
        .btn-dir {{
            background: #111d33;
            color: #94a3b8;
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: 0.2s;
        }}
        .btn-dir:hover {{ color: #fff; border-color: var(--cyan); }}
        .btn-dir.active {{ background: #0284c7; color: #fff; border-color: var(--cyan); font-weight: 700; }}

        /* Main Grid */
        .grid-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 16px;
        }}
        .cand-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
            position: relative;
        }}
        .cand-card:hover {{
            transform: translateY(-3px);
            border-color: #38bdf8;
        }}
        .cand-card.decision-KEEP {{
            border: 2px solid var(--green) !important;
            box-shadow: 0 0 16px rgba(34, 197, 94, 0.25);
        }}
        .cand-card.decision-MAYBE {{
            border: 2px solid var(--yellow) !important;
            box-shadow: 0 0 16px rgba(234, 179, 8, 0.2);
        }}
        .cand-card.decision-REJECT {{
            opacity: 0.45;
            border: 1px solid var(--red) !important;
            filter: grayscale(40%);
        }}

        .card-img-wrap {{
            position: relative;
            width: 100%;
            height: 380px;
            background: #020617;
            cursor: pointer;
            overflow: hidden;
        }}
        .card-img-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center top;
            transition: transform 0.3s;
        }}
        .card-img-wrap:hover img {{
            transform: scale(1.04);
        }}
        .badge-id {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(6, 12, 24, 0.88);
            border: 1px solid var(--cyan);
            color: var(--cyan);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 800;
        }}
        .badge-status {{
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 3px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            background: rgba(6, 12, 24, 0.85);
        }}
        .status-PRESELECTED {{ color: #38bdf8; border: 1px solid #0284c7; }}
        .status-CANDIDATE {{ color: #94a3b8; border: 1px solid #475569; }}
        .badge-q {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            background: rgba(6, 12, 24, 0.8);
            color: #94a3b8;
            border: 1px solid #334155;
        }}
        .q-HQ {{ color: #4ade80; border-color: rgba(74, 222, 128, 0.4); }}
        .q-LOW_RES_CANDIDATE {{ color: #fbbf24; border-color: rgba(251, 191, 36, 0.4); }}

        .user-choice-badge {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 800;
            display: none;
        }}

        .card-meta {{
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            flex: 1;
        }}
        .direction-tag {{
            font-size: 11px;
            font-weight: 700;
            color: #38bdf8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .tags-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .tag-pill {{
            font-size: 11px;
            background: #111e38;
            padding: 2px 6px;
            border-radius: 4px;
            color: #94a3b8;
            border: 1px solid #1e293b;
        }}
        .obs-text {{
            font-size: 12px;
            line-height: 1.5;
            color: #e2e8f0;
            background: #081124;
            padding: 8px 10px;
            border-radius: 6px;
            border: 1px solid #162544;
            min-height: 52px;
        }}
        .author-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: auto;
        }}
        .links-group {{
            display: flex;
            gap: 8px;
        }}
        .meta-link {{
            color: #38bdf8;
            text-decoration: none;
        }}
        .meta-link:hover {{ text-decoration: underline; }}

        /* Action Buttons */
        .action-buttons {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 6px;
            margin-top: 4px;
            padding-top: 10px;
            border-top: 1px solid var(--border);
        }}
        .btn-decision {{
            padding: 8px 4px;
            border-radius: 6px;
            border: 1px solid transparent;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s;
            text-align: center;
        }}
        .btn-keep {{
            background: rgba(34, 197, 94, 0.12);
            color: #4ade80;
            border-color: rgba(34, 197, 94, 0.3);
        }}
        .btn-keep:hover, .btn-keep.active {{
            background: var(--green);
            color: #041026;
            border-color: var(--green);
        }}
        .btn-maybe {{
            background: rgba(234, 179, 8, 0.12);
            color: #facc15;
            border-color: rgba(234, 179, 8, 0.3);
        }}
        .btn-maybe:hover, .btn-maybe.active {{
            background: var(--yellow);
            color: #041026;
            border-color: var(--yellow);
        }}
        .btn-reject {{
            background: rgba(239, 68, 68, 0.12);
            color: #f87171;
            border-color: rgba(239, 68, 68, 0.3);
        }}
        .btn-reject:hover, .btn-reject.active {{
            background: var(--red);
            color: #fff;
            border-color: var(--red);
        }}

        /* Full Image Modal */
        .modal {{
            display: none;
            position: fixed;
            z-index: 200;
            left: 0; top: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.92);
            backdrop-filter: blur(10px);
            align-items: center;
            justify-content: center;
        }}
        .modal-inner {{
            position: relative;
            max-width: 90vw;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .modal-inner img {{
            max-width: 90vw;
            max-height: 80vh;
            object-fit: contain;
            border-radius: 8px;
            border: 1px solid var(--cyan);
        }}
        .modal-close {{
            position: absolute;
            top: -36px;
            right: 0;
            color: #fff;
            font-size: 28px;
            cursor: pointer;
        }}
        .export-modal-box {{
            background: #0d1a33;
            border: 1px solid var(--cyan);
            border-radius: 12px;
            padding: 24px;
            max-width: 650px;
            width: 90vw;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .export-textarea {{
            width: 100%;
            height: 180px;
            background: #060c18;
            color: #4ade80;
            font-family: monospace;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #1e3a5f;
            font-size: 13px;
        }}
    </style>
</head>
<body>

    <!-- Sticky Navigation & Review Tool -->
    <header class="top-nav">
        <div class="nav-row-1">
            <div class="brand-box">
                <div class="brand-title">🎯 王昭君·长夜焕生 漫展姿势候选挑选板</div>
                <div class="nav-links">
                    <a href="index.html" class="nav-btn">📚 资料总库 (Library)</a>
                    <a href="review_pose_candidates.html" class="nav-btn active">🎯 姿势筛选 (Review)</a>
                </div>
            </div>
            <div class="review-stats">
                <span class="stat-badge stat-keep" id="count-keep">KEEP: 0</span>
                <span class="stat-badge stat-maybe" id="count-maybe">MAYBE: 0</span>
                <span class="stat-badge stat-reject" id="count-reject">REJECT: 0</span>
                <span class="stat-badge stat-unreviewed" id="count-unreviewed">未评: {len(candidates)}</span>
                <button class="btn-export" onclick="exportDecisions()">📥 导出评审结果 (EXPORT)</button>
            </div>
        </div>

        <div class="filters-row">
            <span class="filter-label">重点方向:</span>
            <button class="btn-dir active" onclick="filterDir('ALL')">全部 ({len(candidates)})</button>
            <button class="btn-dir" onclick="filterDir('A_STANDING')">A. 柔和站姿</button>
            <button class="btn-dir" onclick="filterDir('B_TURN_BACK')">B. 回眸背身</button>
            <button class="btn-dir" onclick="filterDir('C_HANDS_FACE')">C. 手势面部</button>
            <button class="btn-dir" onclick="filterDir('D_LOW_STOOL')">D. 小凳坐姿</button>
            <button class="btn-dir" onclick="filterDir('E_PROP')">E. 长柄道具</button>
            <button class="btn-dir" onclick="filterDir('F_LOW_ANGLE')">F. 柔和低机位</button>
            <button class="btn-dir" onclick="filterDir('G_DYNAMIC')">G. 小幅动态</button>
            <span class="filter-label" style="margin-left:12px;">状态过滤:</span>
            <button class="btn-dir" onclick="filterStatus('PRESELECTED')">仅看旧库预选</button>
            <button class="btn-dir" onclick="filterChoice('KEEP')">仅看已选 KEEP</button>
            <button class="btn-dir" onclick="filterChoice('MAYBE')">仅看 MAYBE</button>
            <button class="btn-dir" onclick="filterChoice('UNREVIEWED')">仅看未评审</button>
        </div>
    </header>

    <!-- Cards Grid -->
    <main class="grid-container" id="grid">
        {"".join(cards_html)}
    </main>

    <!-- Image Modal -->
    <div class="modal" id="imgModal" onclick="closeImgModal()">
        <div class="modal-inner" onclick="event.stopPropagation()">
            <span class="modal-close" onclick="closeImgModal()">&times;</span>
            <img id="modalImg" src="" alt="Full view">
            <div id="modalCap" style="color:#38bdf8;margin-top:10px;font-weight:700;"></div>
        </div>
    </div>

    <!-- Export Modal -->
    <div class="modal" id="exportModal" onclick="closeExportModal()">
        <div class="export-modal-box" onclick="event.stopPropagation()">
            <h3 style="color:var(--cyan);">📥 评审结果已导出并复制</h3>
            <p style="font-size:13px;color:var(--text-muted);">
                结果已自动保存到浏览器本地 (localStorage)，并生成了标准化 JSON。您可以直接复制下方文本发给 Agent，或下载 JSON 文件：
            </p>
            <textarea class="export-textarea" id="exportText" readonly></textarea>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <button class="btn-export" onclick="downloadJSON()">💾 下载 pose_review_decisions.json</button>
                <button class="nav-btn" onclick="copyExportText()">📋 复制文本到剪贴板</button>
                <button class="nav-btn" onclick="closeExportModal()">关闭</button>
            </div>
        </div>
    </div>

    <script>
        const STORAGE_KEY = 'zhaojun_pose_review_v2';
        let decisions = {{}};
        let currentDir = 'ALL';
        let currentFilterStatus = 'ALL';
        let currentFilterChoice = 'ALL';

        // Load saved decisions from localStorage
        function loadDecisions() {{
            try {{
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved) {{
                    decisions = JSON.parse(saved);
                }}
            }} catch(e) {{
                console.warn('Failed to parse localStorage decisions', e);
            }}
            applyAllDecisionsToUI();
            updateCounters();
        }}

        function setDecision(cid, choice) {{
            if (decisions[cid] === choice) {{
                delete decisions[cid]; // toggle off
            }} else {{
                decisions[cid] = choice;
            }}
            saveDecisions();
            updateCardUI(cid);
            updateCounters();
        }}

        function saveDecisions() {{
            try {{
                localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
            }} catch(e) {{
                console.warn('LocalStorage save failed', e);
            }}
        }}

        function updateCardUI(cid) {{
            const card = document.getElementById('card-' + cid);
            if (!card) return;
            const choice = decisions[cid];
            card.classList.remove('decision-KEEP', 'decision-MAYBE', 'decision-REJECT');
            const btns = card.querySelectorAll('.btn-decision');
            btns.forEach(b => b.classList.remove('active'));

            const badge = document.getElementById('badge-choice-' + cid);

            if (choice === 'KEEP') {{
                card.classList.add('decision-KEEP');
                card.querySelector('.btn-keep').classList.add('active');
                badge.style.display = 'block';
                badge.style.background = '#22c55e';
                badge.style.color = '#041026';
                badge.textContent = '✓ KEEP';
            }} else if (choice === 'MAYBE') {{
                card.classList.add('decision-MAYBE');
                card.querySelector('.btn-maybe').classList.add('active');
                badge.style.display = 'block';
                badge.style.background = '#eab308';
                badge.style.color = '#041026';
                badge.textContent = '? MAYBE';
            }} else if (choice === 'REJECT') {{
                card.classList.add('decision-REJECT');
                card.querySelector('.btn-reject').classList.add('active');
                badge.style.display = 'block';
                badge.style.background = '#ef4444';
                badge.style.color = '#fff';
                badge.textContent = '✕ REJECT';
            }} else {{
                badge.style.display = 'none';
            }}
        }}

        function applyAllDecisionsToUI() {{
            const cards = document.querySelectorAll('.cand-card');
            cards.forEach(card => {{
                updateCardUI(card.dataset.id);
            }});
        }}

        function updateCounters() {{
            let k = 0, m = 0, r = 0;
            const total = document.querySelectorAll('.cand-card').length;
            for (let id in decisions) {{
                if (decisions[id] === 'KEEP') k++;
                else if (decisions[id] === 'MAYBE') m++;
                else if (decisions[id] === 'REJECT') r++;
            }}
            document.getElementById('count-keep').textContent = `KEEP: ${{k}}`;
            document.getElementById('count-maybe').textContent = `MAYBE: ${{m}}`;
            document.getElementById('count-reject').textContent = `REJECT: ${{r}}`;
            document.getElementById('count-unreviewed').textContent = `未评: ${{total - (k + m + r)}}`;
        }}

        function filterDir(dir) {{
            currentDir = dir;
            currentFilterStatus = 'ALL';
            currentFilterChoice = 'ALL';
            applyFilters();
            document.querySelectorAll('.filters-row .btn-dir').forEach(b => {{
                b.classList.toggle('active', b.textContent.includes(dir) || (dir==='ALL' && b.textContent.startsWith('全部')));
            }});
        }}

        function filterStatus(stat) {{
            currentFilterStatus = (currentFilterStatus === stat) ? 'ALL' : stat;
            applyFilters();
        }}

        function filterChoice(choice) {{
            currentFilterChoice = (currentFilterChoice === choice) ? 'ALL' : choice;
            applyFilters();
        }}

        function applyFilters() {{
            const cards = document.querySelectorAll('.cand-card');
            cards.forEach(c => {{
                const id = c.dataset.id;
                const dir = c.dataset.direction;
                const status = c.dataset.status;
                const choice = decisions[id];

                let matchDir = (currentDir === 'ALL' || dir === currentDir);
                let matchStatus = (currentFilterStatus === 'ALL' || status === currentFilterStatus);
                let matchChoice = true;
                if (currentFilterChoice === 'KEEP') matchChoice = (choice === 'KEEP');
                else if (currentFilterChoice === 'MAYBE') matchChoice = (choice === 'MAYBE');
                else if (currentFilterChoice === 'UNREVIEWED') matchChoice = (!choice);

                c.style.display = (matchDir && matchStatus && matchChoice) ? 'flex' : 'none';
            }});
        }}

        function viewFullImage(src, id) {{
            document.getElementById('modalImg').src = src;
            document.getElementById('modalCap').textContent = id;
            document.getElementById('imgModal').style.display = 'flex';
        }}

        function closeImgModal() {{
            document.getElementById('imgModal').style.display = 'none';
        }}

        function exportDecisions() {{
            const keepList = [];
            const maybeList = [];
            const rejectList = [];
            for (let id in decisions) {{
                if (decisions[id] === 'KEEP') keepList.push(id);
                else if (decisions[id] === 'MAYBE') maybeList.push(id);
                else if (decisions[id] === 'REJECT') rejectList.push(id);
            }}

            const summary = {{
                "timestamp": new Date().toISOString(),
                "keep_count": keepList.length,
                "maybe_count": maybeList.length,
                "reject_count": rejectList.length,
                "decisions": decisions,
                "lists": {{
                    "KEEP": keepList,
                    "MAYBE": maybeList,
                    "REJECT": rejectList
                }}
            }};

            document.getElementById('exportText').value = JSON.stringify(summary, null, 2);
            document.getElementById('exportModal').style.display = 'flex';
        }}

        function closeExportModal() {{
            document.getElementById('exportModal').style.display = 'none';
        }}

        function copyExportText() {{
            const ta = document.getElementById('exportText');
            ta.select();
            document.execCommand('copy');
            alert('已复制到剪贴板！');
        }}

        function downloadJSON() {{
            const text = document.getElementById('exportText').value;
            const blob = new Blob([text], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pose_review_decisions.json';
            a.click();
            URL.revokeObjectURL(url);
        }}

        // Initialize on load
        window.addEventListener('DOMContentLoaded', loadDecisions);
    </script>
</body>
</html>
"""
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"Generated {OUTPUT_HTML} successfully.")

if __name__ == "__main__":
    build_review_board()
