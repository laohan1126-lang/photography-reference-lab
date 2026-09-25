#!/usr/bin/env python3
"""Build modern interactive HTML board from data/references.yaml with category-specific cards."""

import html
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "data" / "references.yaml"
OUTPUT_HTML = ROOT / "dist" / "index.html"
OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

def render_category_card(r, modal_payload):
    ref_id = r["id"]
    rel_file = r["file"]
    img_src = f"../{rel_file}"
    pri = r.get("priority", "SUPPORT")
    cat = r.get("category", "")
    author = r.get("source", {}).get("author", "Unknown")
    source_url = r.get("source", {}).get("url", "#")
    review_status = r.get("review_status", "PRESELECTED")
    roles = r.get("reference_roles", [])
    roles_html = "".join(f'<span class="pill role-pill">{html.escape(ro)}</span>' for ro in roles)

    # 1. 03_POSE card
    if cat == "03_POSE":
        observed = r.get("visual_audit", {}).get("actual_pose") or "".join(r.get("observed", []))
        rec_lens = r.get("recommended_lens", "")
        director_script = r.get("director_script", "") if review_status == "APPROVED" else ""
        
        body_html = f"""
        <div class="card-section">
            <div class="obs-box">
                <strong>[ACTUAL POSE OBSERVED]</strong>
                <p>{html.escape(observed)}</p>
            </div>
            {f'<div class="director-box"><strong>🗣️ 摄影师口令 (已核准):</strong><p>"{html.escape(director_script)}"</p></div>' if director_script else ''}
        </div>
        """

    # 2. 04_LIGHTING card
    elif cat == "04_LIGHTING":
        obs = r.get("lighting_observation") or "".join(r.get("observed", []))
        s_claim = r.get("source_claim", "原帖未附带测光表数据或详细灯路光位图")
        inf = r.get("lighting_inference") or "".join(r.get("inferred", []))
        app = r.get("possible_application") or "".join(r.get("proposed", []))
        
        body_html = f"""
        <div class="card-section">
            <div class="obs-box"><strong>[LIGHTING RESULT / OBSERVED]</strong><p>{html.escape(obs)}</p></div>
            <div class="claim-box"><strong>[SOURCE CLAIM (原作者声明)]</strong><p>{html.escape(s_claim)}</p></div>
            {f'<div class="inf-box"><strong>[INFERENCE (推断分析)]</strong><p>{html.escape(inf)}</p></div>' if inf else ''}
            {f'<div class="test-box"><strong>[WHAT WE CAN TEST (现场测试)]</strong><p>{html.escape(app)}</p></div>' if app else ''}
        </div>
        """

    # 3. 07_BTS_TECHNICAL card
    elif cat == "07_BTS_TECHNICAL":
        obs = r.get("technical_observation") or "".join(r.get("observed", []))
        s_claim = r.get("source_claim", "原作者器材与场地环境记录")
        ctx = r.get("context", "")
        app = r.get("possible_application") or "".join(r.get("proposed", []))
        
        body_html = f"""
        <div class="card-section">
            <div class="obs-box"><strong>[WHAT IS ACTUALLY SHOWN]</strong><p>{html.escape(obs)}</p></div>
            {f'<div class="claim-box"><strong>[SOURCE CLAIM]</strong><p>{html.escape(s_claim)}</p></div>' if s_claim else ''}
            {f'<div class="ctx-box"><strong>[CONTEXT (实地环境)]</strong><p>{html.escape(ctx)}</p></div>' if ctx else ''}
            {f'<div class="test-box"><strong>[POSSIBLE USE (漫展参考)]</strong><p>{html.escape(app)}</p></div>' if app else ''}
        </div>
        """

    # 4. 00_OFFICIAL card
    elif cat == "00_OFFICIAL":
        feature = r.get("character_anchor") or "".join(r.get("observed", []))
        must_preserve = "".join(r.get("inferred", []))
        
        body_html = f"""
        <div class="card-section">
            <div class="obs-box"><strong>[CHARACTER FEATURE (官方锚点)]</strong><p>{html.escape(feature)}</p></div>
            {f'<div class="inf-box"><strong>[WHAT MUST BE PRESERVED (不可偏离特征)]</strong><p>{html.escape(must_preserve)}</p></div>' if must_preserve else ''}
        </div>
        """

    # 5. Default generic card (COSTUME, STYLE, POST, etc.)
    else:
        obs_items = "".join(f'<li>{html.escape(o)}</li>' for o in r.get("observed", []))
        inf_items = "".join(f'<li>{html.escape(i)}</li>' for i in r.get("inferred", []))
        dnc_items = "".join(f'<li>{html.escape(d)}</li>' for d in r.get("do_not_copy", []))
        body_html = f"""
        <div class="card-section">
            <div class="obs-box"><strong>[OBSERVED]</strong><ul>{obs_items}</ul></div>
            {f'<div class="inf-box"><strong>[INFERRED]</strong><ul>{inf_items}</ul></div>' if inf_items else ''}
            {f'<div class="dnc-box"><strong>[DO NOT COPY]</strong><ul>{dnc_items}</ul></div>' if dnc_items else ''}
        </div>
        """

    card = f"""
    <div class="ref-card" data-category="{cat}" data-priority="{pri}" data-status="{review_status}">
        <div class="card-img-container" onclick="openRefModal('{ref_id}')" id="img-meta-{ref_id}" data-meta='{modal_payload}'>
            <img src="{img_src}" alt="{html.escape(ref_id)}" loading="lazy">
            <span class="badge priority-{pri}">{pri}</span>
            <span class="badge-cat">{cat}</span>
            <span class="badge-status status-{review_status}">{review_status}</span>
        </div>
        <div class="card-content">
            <div class="card-topline">
                <span class="ref-id">{ref_id}</span>
                <span class="ref-author" title="{html.escape(author)}">{html.escape(author[:18])}</span>
            </div>
            <div class="pills-container">
                {roles_html}
            </div>
            {body_html}
            <div class="card-footer">
                <a href="{source_url}" target="_blank" rel="noopener noreferrer" class="link-btn">🔗 查看来源原帖</a>
                <a href="{img_src}" target="_blank" class="link-btn">🔍 查看大图</a>
            </div>
        </div>
    </div>
    """
    return card

def build_board():
    with open(DATA_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    categories = sorted(list(set(r["category"] for r in data)))
    priorities = ["ALL", "CORE", "SUPPORT", "OPTIONAL", "STUDIO_OPTIONAL", "REJECT"]

    cards_html = []
    for r in data:
        ref_id = r["id"]
        rel_file = r["file"]
        img_src = f"../{rel_file}"
        pri = r.get("priority", "SUPPORT")
        cat = r.get("category", "")
        author = r.get("source", {}).get("author", "Unknown")
        source_url = r.get("source", {}).get("url", "#")

        modal_payload = html.escape(json.dumps({
            "id": ref_id,
            "img": img_src,
            "category": cat,
            "priority": pri,
            "author": author,
            "url": source_url,
            "review_status": r.get("review_status", "PRESELECTED"),
            "observed": r.get("observed", []),
            "inferred": r.get("inferred", []),
            "proposed": r.get("proposed", []),
            "notes": r.get("notes", "")
        }))

        cards_html.append(render_category_card(r, modal_payload))

    cat_buttons = "".join(f'<button class="btn-filter" onclick="filterCategory(\'{c}\')">{c}</button>' for c in categories)
    pri_buttons = "".join(f'<button class="btn-filter {"active" if p=="ALL" else ""}" onclick="filterPriority(\'{p}\')">{p}</button>' for p in priorities)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王昭君·长夜焕生 摄影视觉参考系统 (LIBRARY)</title>
    <style>
        :root {{
            --bg-main: #050b18;
            --bg-card: #0a1428;
            --bg-input: #101e38;
            --border: #1e293b;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --cyan: #00f2ff;
            --blue: #38bdf8;
            --gold: #fbbf24;
            --green: #4ade80;
            --red: #f87171;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-main);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            padding: 24px;
            min-height: 100vh;
        }}
        /* Navigation Bar */
        .system-nav {{
            display: flex;
            gap: 16px;
            background: #0b1730;
            padding: 12px 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            align-items: center;
        }}
        .nav-brand {{
            font-size: 16px;
            font-weight: 700;
            color: var(--cyan);
            margin-right: 12px;
        }}
        .nav-link {{
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-muted);
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            border: 1px solid transparent;
        }}
        .nav-link:hover {{
            color: var(--text-main);
            border-color: var(--border);
        }}
        .nav-link.active {{
            background: #1e3a5f;
            color: var(--cyan);
            border-color: var(--cyan);
        }}
        .nav-link.highlight {{
            background: #0284c7;
            color: #fff;
        }}

        header {{
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
        }}
        header h1 {{
            font-size: 26px;
            color: var(--cyan);
            margin-bottom: 6px;
        }}
        header p {{
            color: var(--text-muted);
            font-size: 14px;
        }}

        /* Filters */
        .controls-panel {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 24px;
            background: var(--bg-card);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid var(--border);
            align-items: center;
        }}
        .filter-group {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .filter-group label {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 600;
        }}
        .btn-filter {{
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: 0.2s;
        }}
        .btn-filter:hover {{
            color: var(--text-main);
            border-color: var(--cyan);
        }}
        .btn-filter.active {{
            background: #0369a1;
            color: #fff;
            border-color: var(--cyan);
        }}

        /* Grid */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        .ref-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .ref-card:hover {{
            transform: translateY(-3px);
            border-color: var(--cyan);
        }}
        .card-img-container {{
            position: relative;
            width: 100%;
            height: 380px;
            background: #030712;
            cursor: pointer;
            overflow: hidden;
        }}
        .card-img-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center top;
            transition: transform 0.3s;
        }}
        .card-img-container:hover img {{
            transform: scale(1.03);
        }}
        .badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            background: rgba(5, 11, 24, 0.85);
            backdrop-filter: blur(4px);
        }}
        .priority-CORE {{ color: var(--cyan); border: 1px solid var(--cyan); }}
        .priority-SUPPORT {{ color: var(--green); border: 1px solid var(--green); }}
        .priority-OPTIONAL {{ color: var(--gold); border: 1px solid var(--gold); }}
        .priority-REJECT {{ color: var(--red); border: 1px solid var(--red); }}
        
        .badge-cat {{
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            background: rgba(5, 11, 24, 0.85);
            color: var(--text-muted);
            border: 1px solid var(--border);
        }}
        .badge-status {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            padding: 3px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            background: rgba(15, 23, 42, 0.85);
            color: #cbd5e1;
            border: 1px solid #334155;
        }}
        .status-PRESELECTED {{ color: #38bdf8; border-color: #0284c7; }}
        .status-APPROVED {{ color: #4ade80; border-color: #16a34a; }}
        .status-CANDIDATE {{ color: #fbbf24; border-color: #d97706; }}
        .status-REJECTED {{ color: #f87171; border-color: #dc2626; }}

        .card-content {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            flex: 1;
            gap: 12px;
        }}
        .card-topline {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .ref-id {{
            font-size: 14px;
            font-weight: 700;
            color: var(--cyan);
        }}
        .ref-author {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        .pills-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .pill {{
            font-size: 11px;
            padding: 3px 6px;
            border-radius: 4px;
            background: var(--bg-input);
            color: var(--text-muted);
            border: 1px solid var(--border);
        }}
        .role-pill {{ color: #7dd3fc; border-color: #0369a1; }}
        
        .card-section {{
            font-size: 12px;
            line-height: 1.5;
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: #071022;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #132240;
        }}
        .obs-box strong, .claim-box strong, .inf-box strong, .ctx-box strong, .test-box strong, .director-box strong {{
            display: block;
            font-size: 11px;
            margin-bottom: 2px;
        }}
        .obs-box strong {{ color: var(--cyan); }}
        .claim-box strong {{ color: var(--gold); }}
        .inf-box strong {{ color: #a78bfa; }}
        .ctx-box strong {{ color: #38bdf8; }}
        .test-box strong {{ color: var(--green); }}
        .director-box strong {{ color: #f43f5e; }}

        .director-box {{
            background: #1c1020;
            padding: 8px;
            border-radius: 6px;
            border-left: 3px solid #f43f5e;
            color: #ffe4e6;
        }}

        .card-footer {{
            margin-top: auto;
            display: flex;
            justify-content: space-between;
            padding-top: 10px;
            border-top: 1px solid var(--border);
        }}
        .link-btn {{
            font-size: 12px;
            color: var(--blue);
            text-decoration: none;
        }}
        .link-btn:hover {{ text-decoration: underline; }}

        /* Modal */
        .modal {{
            display: none;
            position: fixed;
            z-index: 100;
            left: 0; top: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(8px);
            align-items: center;
            justify-content: center;
        }}
        .modal-box {{
            background: var(--bg-card);
            border: 1px solid var(--cyan);
            border-radius: 12px;
            max-width: 900px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            padding: 24px;
            position: relative;
        }}
        .modal-close {{
            position: absolute;
            top: 16px; right: 16px;
            font-size: 24px;
            cursor: pointer;
            color: var(--text-muted);
        }}
        .modal-close:hover {{ color: var(--text-main); }}
    </style>
</head>
<body>

    <!-- Global Navigation -->
    <nav class="system-nav">
        <div class="nav-brand">王昭君·长夜焕生 视觉参考系统</div>
        <a href="index.html" class="nav-link active">📚 REFERENCE LIBRARY (资料总库)</a>
        <a href="review_pose_candidates.html" class="nav-link highlight">🎯 POSE CANDIDATE REVIEW (姿势候选审核板)</a>
        <span style="color:#475569;font-size:13px;margin-left:auto;">当前阶段: POSE DISCOVERY &amp; REVIEW (等待人工筛选)</span>
    </nav>

    <header>
        <h1>参考总览资料库 (Reference Library)</h1>
        <p>单向真实数据源：data/references.yaml | 覆盖官方特征、服饰材质、实战灯位、场景布置与真人姿态 | 严格类别Schema分离</p>
    </header>

    <!-- Controls -->
    <div class="controls-panel">
        <div class="filter-group">
            <label>类别分类:</label>
            <button class="btn-filter active" onclick="filterCategory('ALL')">全部 ({len(data)})</button>
            {cat_buttons}
        </div>
        <div class="filter-group">
            <label>优先级:</label>
            {pri_buttons}
        </div>
    </div>

    <!-- Cards Grid -->
    <div class="cards-grid" id="cards-grid">
        {"".join(cards_html)}
    </div>

    <!-- Modal Container -->
    <div class="modal" id="refModal" onclick="closeRefModal(event)">
        <div class="modal-box" onclick="event.stopPropagation()">
            <span class="modal-close" onclick="closeRefModal()">&times;</span>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        let currentCategory = 'ALL';
        let currentPriority = 'ALL';

        function filterCategory(cat) {{
            currentCategory = cat;
            applyFilters();
            document.querySelectorAll('.controls-panel .filter-group:nth-child(1) .btn-filter').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent.includes(cat) || (cat === 'ALL' && btn.textContent.startsWith('全部')));
            }});
        }}

        function filterPriority(pri) {{
            currentPriority = pri;
            applyFilters();
            document.querySelectorAll('.controls-panel .filter-group:nth-child(2) .btn-filter').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent === pri);
            }});
        }}

        function applyFilters() {{
            const cards = document.querySelectorAll('.ref-card');
            cards.forEach(card => {{
                const cCat = card.dataset.category;
                const cPri = card.dataset.priority;
                const matchCat = (currentCategory === 'ALL' || cCat === currentCategory);
                const matchPri = (currentPriority === 'ALL' || cPri === currentPriority);
                card.style.display = (matchCat && matchPri) ? 'flex' : 'none';
            }});
        }}

        function openRefModal(refId) {{
            const el = document.getElementById('img-meta-' + refId);
            if (!el) return;
            const meta = JSON.parse(el.dataset.meta);
            const modalBody = document.getElementById('modal-body');
            modalBody.innerHTML = `
                <h2 style="color:var(--cyan);margin-bottom:12px;">[${{meta.id}}] ${{meta.category}} (${{meta.priority}})</h2>
                <div style="text-align:center;margin-bottom:16px;">
                    <img src="${{meta.img}}" style="max-height:60vh;max-width:100%;border-radius:8px;border:1px solid var(--border);">
                </div>
                <div style="font-size:14px;color:var(--text-muted);margin-bottom:8px;">作者: ${{meta.author}} | 状态: ${{meta.review_status}}</div>
                <div style="margin-top:12px;">
                    <a href="${{meta.url}}" target="_blank" style="color:var(--blue);margin-right:16px;">查看来源原帖</a>
                    <a href="${{meta.img}}" target="_blank" style="color:var(--cyan);">打开全分辨率原图</a>
                </div>
            `;
            document.getElementById('refModal').style.display = 'flex';
        }}

        function closeRefModal(event) {{
            document.getElementById('refModal').style.display = 'none';
        }}
    </script>
</body>
</html>
"""
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"Generated {OUTPUT_HTML} successfully.")

if __name__ == "__main__":
    build_board()
