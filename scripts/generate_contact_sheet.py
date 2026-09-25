#!/usr/bin/env python3
"""Generate HTML gallery and visual contact sheets for photography reference library."""

import csv
import html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REF_DIR = ROOT / "references" / "changye-huansheng"
INDEX_CSV = REF_DIR / "index.csv"
OUTPUT_DIR = REF_DIR / "contact_sheets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    with open(INDEX_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)

def generate_html_gallery(rows):
    categories = sorted(list(set(r["category"] for r in rows)))
    
    cards_html = []
    for r in rows:
        rel_path = r["filename"]
        img_src = f"../{rel_path}"
        suitable_tags = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in r["suitable_for"].split(";") if t)
        
        card = f"""
        <div class="card" data-category="{html.escape(r['category'])}">
            <div class="card-img-wrap" onclick="openModal('{img_src}', '{html.escape(r['ID'])}', '{html.escape(r['author'])}', '{html.escape(r['value_notes'])}')">
                <img src="{img_src}" alt="{html.escape(r['ID'])}" loading="lazy">
                <span class="badge badge-{html.escape(r['category'])}">{html.escape(r['category'])}</span>
                <span class="res-badge">{html.escape(r['resolution'])}</span>
            </div>
            <div class="card-body">
                <div class="card-header">
                    <span class="card-id">{html.escape(r['ID'])}</span>
                    <span class="author">📷 {html.escape(r['author'])}</span>
                </div>
                <div class="tags">{suitable_tags}</div>
                <p class="notes">{html.escape(r['value_notes'])}</p>
                <div class="card-footer">
                    <a href="{html.escape(r['source_url'])}" target="_blank" class="link-btn">源笔记 ↗</a>
                    <a href="{img_src}" target="_blank" class="link-btn">原图 ↗</a>
                </div>
            </div>
        </div>
        """
        cards_html.append(card)

    filter_buttons = ['<button class="filter-btn active" onclick="filterCat(\'ALL\')">全部 (ALL) <span class="count">' + str(len(rows)) + '</span></button>']
    for cat in categories:
        cnt = sum(1 for r in rows if r["category"] == cat)
        filter_buttons.append(f'<button class="filter-btn" onclick="filterCat(\'{cat}\')">{cat} <span class="count">{cnt}</span></button>')

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王昭君·长夜焕生 摄影参考视觉大板 (Visual Reference Board)</title>
    <style>
        :root {{
            --bg-deep: #070d1e;
            --bg-card: #0d1730;
            --bg-card-hover: #142347;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --accent-cyan: #00f2ff;
            --accent-gold: #ffb74d;
            --border-color: rgba(0, 242, 255, 0.15);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: linear-gradient(180deg, #050b18 0%, #081226 50%, #050b18 100%);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            min-height: 100vh;
            padding: 30px 20px 80px 20px;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        header {{
            text-align: center;
            margin-bottom: 35px;
            padding-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
        }}
        h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: 2px;
            background: linear-gradient(90deg, #e0f2fe, var(--accent-cyan), var(--accent-gold));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 1rem;
            max-width: 800px;
            margin: 0 auto;
            line-height: 1.6;
        }}
        .nav-links {{
            margin-top: 18px;
            display: flex;
            justify-content: center;
            gap: 15px;
        }}
        .nav-link {{
            color: var(--accent-cyan);
            text-decoration: none;
            font-size: 0.9rem;
            padding: 6px 14px;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            background: rgba(0, 242, 255, 0.05);
            transition: all 0.2s;
        }}
        .nav-link:hover {{
            background: rgba(0, 242, 255, 0.2);
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.3);
        }}
        .filter-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
        }}
        .filter-btn {{
            background: var(--bg-card);
            color: var(--text-muted);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.88rem;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{
            color: var(--text-main);
            border-color: var(--accent-cyan);
        }}
        .filter-btn.active {{
            background: rgba(0, 242, 255, 0.15);
            color: var(--accent-cyan);
            border-color: var(--accent-cyan);
            font-weight: 600;
        }}
        .filter-btn .count {{
            font-size: 0.75rem;
            opacity: 0.7;
            margin-left: 4px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 25px;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
        }}
        .card:hover {{
            transform: translateY(-5px);
            border-color: var(--accent-cyan);
            box-shadow: 0 12px 30px rgba(0, 242, 255, 0.15);
        }}
        .card-img-wrap {{
            position: relative;
            width: 100%;
            height: 380px;
            background: #040813;
            overflow: hidden;
            cursor: pointer;
        }}
        .card-img-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}
        .card:hover .card-img-wrap img {{
            transform: scale(1.03);
        }}
        .badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(5, 11, 24, 0.85);
            backdrop-filter: blur(8px);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--accent-cyan);
            border: 1px solid var(--border-color);
        }}
        .res-badge {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.75);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            color: #cbd5e1;
        }}
        .card-body {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            flex: 1;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .card-id {{
            font-weight: 700;
            color: var(--accent-cyan);
            font-size: 0.95rem;
        }}
        .author {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 12px;
        }}
        .tag {{
            background: rgba(255, 183, 77, 0.12);
            color: var(--accent-gold);
            font-size: 0.7rem;
            padding: 2px 7px;
            border-radius: 4px;
            font-weight: 500;
        }}
        .notes {{
            font-size: 0.85rem;
            color: #cbd5e1;
            line-height: 1.5;
            margin-bottom: 16px;
            flex: 1;
        }}
        .card-footer {{
            display: flex;
            gap: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            padding-top: 12px;
        }}
        .link-btn {{
            flex: 1;
            text-align: center;
            padding: 6px 0;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.78rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            transition: all 0.2s;
        }}
        .link-btn:hover {{
            background: rgba(0, 242, 255, 0.2);
            color: var(--accent-cyan);
        }}
        /* Modal */
        #modal {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        #modal-img {{
            max-width: 90vw;
            max-height: 85vh;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 0 30px rgba(0, 242, 255, 0.3);
        }}
        #modal-close {{
            position: absolute;
            top: 25px;
            right: 35px;
            color: #fff;
            font-size: 32px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>王昭君·长夜焕生 摄影参考视觉大板</h1>
            <p class="subtitle">为《王者荣耀》王昭君 FMVP 皮肤线下实拍打造的视觉基因库与参考指南。涵盖官方设定、高定时尚置景、仿水下动态、实战灯位图解与后期合成规范。</p>
            <div class="nav-links">
                <a href="../VISUAL_DNA.md" target="_blank" class="nav-link">📖 角色视觉 DNA</a>
                <a href="../REFERENCE_ANALYSIS.md" target="_blank" class="nav-link">🔬 核心参考深度解析</a>
                <a href="../SHOT_PLAN.md" target="_blank" class="nav-link">🎬 10套实拍分镜方案</a>
                <a href="../index.csv" target="_blank" class="nav-link">📊 结构化目录 CSV</a>
            </div>
        </header>

        <div class="filter-bar">
            {''.join(filter_buttons)}
        </div>

        <div class="grid" id="cardGrid">
            {''.join(cards_html)}
        </div>
    </div>

    <div id="modal" onclick="closeModal()">
        <span id="modal-close">&times;</span>
        <img id="modal-img" src="" alt="Zoomed view">
    </div>

    <script>
        function filterCat(cat) {{
            const cards = document.querySelectorAll('.card');
            const btns = document.querySelectorAll('.filter-btn');
            btns.forEach(b => {{
                if (b.innerText.startsWith(cat) || (cat === 'ALL' && b.innerText.startsWith('全部'))) {{
                    b.classList.add('active');
                }} else {{
                    b.classList.remove('active');
                }}
            }});
            cards.forEach(c => {{
                if (cat === 'ALL' || c.getAttribute('data-category') === cat) {{
                    c.style.display = 'flex';
                }} else {{
                    c.style.display = 'none';
                }}
            }});
        }}

        function openModal(src, id, author, notes) {{
            const modal = document.getElementById('modal');
            const modalImg = document.getElementById('modal-img');
            modalImg.src = src;
            modal.style.display = 'flex';
        }}

        function closeModal() {{
            document.getElementById('modal').style.display = 'none';
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>
"""
    output_html = OUTPUT_DIR / "index.html"
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML gallery at: {output_html}")

def generate_image_contact_sheets(rows):
    # Generate combined grid contact sheet
    thumb_w, thumb_h = 360, 480
    cols = 5
    padding = 20
    header_h = 100
    
    n = len(rows)
    import math
    rows_cnt = math.ceil(n / cols)
    
    total_w = cols * thumb_w + (cols + 1) * padding
    total_h = header_h + rows_cnt * (thumb_h + 40) + padding
    
    sheet = Image.new("RGB", (total_w, total_h), color=(7, 13, 30))
    draw = ImageDraw.Draw(sheet)
    
    # Try load font or default
    try:
        font_title = ImageFont.truetype("msyh.ttc", 36)
        font_sub = ImageFont.truetype("msyh.ttc", 20)
        font_label = ImageFont.truetype("msyh.ttc", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_label = ImageFont.load_default()

    draw.text((padding, 25), "王昭君·长夜焕生 摄影参考联系图 (CONTACT SHEET)", fill=(0, 242, 255), font=font_title)
    draw.text((padding, 68), f"Total References: {n} | 涵盖 00_OFFICIAL ~ 05_POSTPRODUCTION", fill=(148, 163, 184), font=font_sub)
    
    for i, r in enumerate(rows):
        col = i % cols
        row_idx = i // cols
        
        x = padding + col * (thumb_w + padding)
        y = header_h + row_idx * (thumb_h + 40)
        
        img_path = REF_DIR / r["filename"]
        if img_path.exists():
            try:
                with Image.open(img_path) as im:
                    im_rgb = im.convert("RGB")
                    # Crop to thumb_w, thumb_h center
                    im_ratio = im_rgb.width / im_rgb.height
                    target_ratio = thumb_w / thumb_h
                    if im_ratio > target_ratio:
                        new_w = int(im_rgb.height * target_ratio)
                        offset = (im_rgb.width - new_w) // 2
                        im_cropped = im_rgb.crop((offset, 0, offset + new_w, im_rgb.height))
                    else:
                        new_h = int(im_rgb.width / target_ratio)
                        offset = (im_rgb.height - new_h) // 2
                        im_cropped = im_rgb.crop((0, offset, im_rgb.width, offset + new_h))
                    im_thumb = im_cropped.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(im_thumb, (x, y))
            except Exception as e:
                draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(20, 30, 50))
                draw.text((x + 10, y + 10), f"Error: {e}", fill=(255, 100, 100), font=font_label)
        
        # Label below image
        label_text = f"[{r['ID']}] {r['category']} ({r['resolution']})"
        draw.text((x, y + thumb_h + 6), label_text, fill=(226, 232, 240), font=font_label)
        author_text = f"📷 {r['author'][:18]}"
        draw.text((x, y + thumb_h + 24), author_text, fill=(148, 163, 184), font=font_label)

    output_jpg = OUTPUT_DIR / "contact_sheet_all.jpg"
    sheet.save(output_jpg, "JPEG", quality=90)
    print(f"Generated image contact sheet at: {output_jpg}")

if __name__ == "__main__":
    data = load_data()
    generate_html_gallery(data)
    generate_image_contact_sheets(data)
