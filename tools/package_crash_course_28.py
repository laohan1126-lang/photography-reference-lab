"""Package the 28 'Crash Course' Training Set images into structured folders,
generate contact sheet PDF, standalone HTML gallery, manifest, and ZIP archive.
"""
import os
import sys
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "library.sqlite3"
MANIFEST_PATH = ROOT / "batches" / "verified_library_export" / "library_manifest.json"
OUTPUT_DIR = ROOT / "training_sets" / "28_临时抱佛脚训练集"
ZIP_PATH = ROOT / "training_sets" / "28_临时抱佛脚训练集.zip"

CATEGORIES = [
    ("01_人体结构与引导", "人体结构 / 引导", [
        "JK_0009", "JK_0015", "JK_0031", "JK_0043", "JK_0052", "JK_0057",
        "KANA_0005", "XISHI_0005", "XISHI_0009", "XISHI_0015"
    ]),
    ("02_机位与透视前景", "机位 / 透视 / 前景", [
        "JK_0005", "JK_0011", "JK_0012", "JK_0029", "JK_0039", "JK_0045"
    ]),
    ("03_动态与moment瞬间", "动态 / moment", [
        "JK_0004", "JK_0018", "JK_0041", "JK_0047", "KANA_0004", "XISHI_0008"
    ]),
    ("04_光线与环境处理", "光线 / 环境处理", [
        "JK_0014", "JK_0038", "KANA_0006", "XISHI_0013", "INSP_0004", "INSP_0021"
    ]),
]

FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD_PATH = "C:/Windows/Fonts/msyhbd.ttc"
if not os.path.exists(FONT_BOLD_PATH):
    FONT_BOLD_PATH = FONT_PATH

def load_font(size, bold=False):
    path = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def collect_items():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    assets_by_id = {}
    for cat_val in manifest.get("categories", {}).values():
        for aid, ainfo in cat_val.get("assets", {}).items():
            assets_by_id[aid] = ainfo

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    items = []
    for dir_name, display_cat, id_list in CATEGORIES:
        for idx, aid in enumerate(id_list, 1):
            if aid not in assets_by_id:
                raise KeyError(f"Asset ID not found in library manifest: {aid}")
            ainfo = assets_by_id[aid]
            sha = ainfo["sha"]
            ext = ainfo["filename"].split(".")[-1]
            src_file = ROOT / "data" / "assets" / sha[:2] / sha / f"original.{ext}"
            preview_file = ROOT / "data" / "assets" / sha[:2] / sha / "preview.jpg"
            if not src_file.exists():
                raise FileNotFoundError(f"Original file not found: {src_file}")

            # Get title and note
            row = cur.execute("SELECT data FROM refs WHERE asset_sha=?", (sha,)).fetchone()
            if not row:
                row = cur.execute("SELECT data FROM inspirations WHERE asset_sha=?", (sha,)).fetchone()
            rdata = json.loads(row[0]) if row else {}
            title = rdata.get("title") or ainfo.get("title") or "（无标题）"

            items.append({
                "group_dir": dir_name,
                "group_label": display_cat,
                "group_idx": idx,
                "asset_id": aid,
                "filename": f"{aid}.{ext}",
                "src_path": src_file,
                "preview_path": preview_file if preview_file.exists() else src_file,
                "sha": sha,
                "ext": ext,
                "width": ainfo.get("width", 0),
                "height": ainfo.get("height", 0),
                "role": ainfo.get("role", ""),
                "title": title,
                "drive_file_id": ainfo.get("drive_file_id", "")
            })

    conn.close()
    return items

def render_contact_sheet(items, out_pdf_path):
    page_w, page_h = 2480, 3508
    margin_x, margin_top, margin_bottom = 120, 180, 120
    cols, rows = 2, 3
    per_page = cols * rows
    total_pages = (len(items) + per_page - 1) // per_page

    cell_w = (page_w - margin_x * 2 - 80) // cols
    cell_h = (page_h - margin_top - margin_bottom - 80) // rows

    title_font = load_font(44, bold=True)
    header_font = load_font(34, bold=True)
    body_font = load_font(26, bold=False)
    small_font = load_font(22, bold=False)

    pages = []
    for p_idx in range(total_pages):
        page_img = Image.new("RGB", (page_w, page_h), "#121316")
        draw = ImageDraw.Draw(page_img)

        # Header banner
        draw.rectangle([(margin_x, 60), (page_w - margin_x, 140)], fill="#1f2228")
        draw.text(
            (margin_x + 30, 80),
            "摄影参考实验室 · 28张「临时抱佛脚训练集」",
            font=title_font,
            fill="#f3f4f6"
        )
        page_str = f"第 {p_idx+1} / {total_pages} 页 (图片 {p_idx*per_page+1} - {min((p_idx+1)*per_page, len(items))} / 共 {len(items)} 张)"
        draw.text(
            (page_w - margin_x - 580, 88),
            page_str,
            font=body_font,
            fill="#9ca3af"
        )

        page_items = items[p_idx * per_page : (p_idx + 1) * per_page]
        for i, item in enumerate(page_items):
            c = i % cols
            r = i // cols
            x0 = margin_x + c * (cell_w + 80)
            y0 = margin_top + r * (cell_h + 40)
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            draw.rectangle([(x0, y0), (x1, y1)], fill="#1a1c22", outline="#2e333d", width=2)

            bar_h = 60
            draw.rectangle([(x0, y0), (x1, y0 + bar_h)], fill="#252932")
            draw.rectangle([(x0 + 10, y0 + 10), (x0 + 260, y0 + bar_h - 10)], fill="#0f1115", outline="#3f4553", width=1)
            draw.text((x0 + 25, y0 + 14), item["asset_id"], font=header_font, fill="#ffffff")

            # Category pill
            cat_tag = item["group_label"]
            pill_w = 280
            draw.rounded_rectangle([(x1 - pill_w - 15, y0 + 10), (x1 - 15, y0 + bar_h - 10)], radius=6, fill="#1e3a5f")
            draw.text((x1 - pill_w, y0 + 16), cat_tag, font=small_font, fill="#60a5fa")

            img_area_top = y0 + bar_h + 15
            img_area_bottom = y1 - 95
            img_area_w = cell_w - 30
            img_area_h = img_area_bottom - img_area_top

            try:
                with Image.open(item["src_path"]) as raw_img:
                    raw_rgb = ImageOps.exif_transpose(raw_img).convert("RGB")
                    raw_rgb.thumbnail((img_area_w, img_area_h), Image.Resampling.LANCZOS)
                    paste_x = x0 + 15 + (img_area_w - raw_rgb.width) // 2
                    paste_y = img_area_top + (img_area_h - raw_rgb.height) // 2
                    page_img.paste(raw_rgb, (paste_x, paste_y))
            except Exception as e:
                draw.text((x0 + 30, img_area_top + 100), f"Image load error: {e}", font=body_font, fill="#f87171")

            foot_y = y1 - 85
            meta_line1 = f"类别: {item['group_label']} | 尺寸: {item['width']}x{item['height']} | 格式: {item['ext'].upper()}"
            title_clean = item['title'][:28] if len(item['title']) > 28 else item['title']
            meta_line2 = f"标题: {title_clean}"
            draw.text((x0 + 15, foot_y), meta_line1, font=small_font, fill="#9ca3af")
            draw.text((x0 + 15, foot_y + 36), meta_line2, font=small_font, fill="#d1d5db")

        pages.append(page_img)

    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        out_pdf_path,
        "PDF",
        resolution=300.0,
        save_all=True,
        append_images=pages[1:]
    )
    print(f"  + Generated contact sheet: {out_pdf_path.name} ({len(pages)} pages)")

def generate_html_gallery(items, out_html_path):
    # Generates a standalone visual inspection gallery with dark aesthetic
    cards_html = []
    
    current_group = ""
    for it in items:
        if it["group_label"] != current_group:
            current_group = it["group_label"]
            cards_html.append(f"""
            <div class="category-header">
                <h2>{current_group}</h2>
                <span class="count-badge">{len([x for x in items if x['group_label'] == current_group])} 张</span>
            </div>
            """)
        rel_img_path = f"{it['group_dir']}/{it['filename']}"
        cards_html.append(f"""
        <div class="card">
            <div class="card-head">
                <span class="asset-id">{it['asset_id']}</span>
                <span class="tag">{it['group_label']}</span>
            </div>
            <div class="img-wrap">
                <a href="{rel_img_path}" target="_blank" title="点击查看原图">
                    <img src="{rel_img_path}" alt="{it['asset_id']}" loading="lazy" />
                </a>
            </div>
            <div class="card-meta">
                <div class="title" title="{it['title']}">{it['title']}</div>
                <div class="specs">
                    <span>{it['width']} × {it['height']}</span>
                    <span>{it['ext'].upper()}</span>
                    <span>{it['role']}</span>
                </div>
            </div>
        </div>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>摄影参考实验室 · 28张「临时抱佛脚训练集」</title>
<style>
:root {{
    --bg-base: #0f1115;
    --bg-surface: #181a20;
    --bg-elevated: #22252c;
    --border-subtle: #2b2f38;
    --border-strong: #3d4350;
    --text-primary: #f3f4f6;
    --text-secondary: #9ca3af;
    --text-muted: #6b7280;
    --accent-blue: #3b82f6;
    --accent-blue-bg: #1e3a5f;
    --accent-green: #10b981;
    --accent-green-bg: #064e3b;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: var(--bg-base);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
    padding: 32px 40px;
    line-height: 1.5;
}}
header {{
    max-width: 1400px;
    margin: 0 auto 32px;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 24px;
}}
h1 {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
}}
.subtitle {{
    color: var(--text-secondary);
    font-size: 14px;
}}
.category-header {{
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 24px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-subtle);
}}
.category-header h2 {{
    font-size: 18px;
    color: var(--text-primary);
    font-weight: 600;
}}
.count-badge {{
    background: var(--bg-elevated);
    color: var(--accent-blue);
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}}
.grid {{
    max-width: 1400px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
    gap: 20px;
}}
.card {{
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.15s ease, border-color 0.15s ease;
}}
.card:hover {{
    transform: translateY(-2px);
    border-color: var(--border-strong);
}}
.card-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-subtle);
}}
.asset-id {{
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.5px;
    font-family: monospace;
}}
.tag {{
    font-size: 11px;
    background: var(--accent-blue-bg);
    color: #93c5fd;
    padding: 2px 8px;
    border-radius: 4px;
}}
.img-wrap {{
    background: #000;
    width: 100%;
    height: 380px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}}
.img-wrap img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: opacity 0.2s ease;
}}
.card-meta {{
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.title {{
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.specs {{
    display: flex;
    gap: 8px;
    font-size: 11px;
    color: var(--text-muted);
}}
.specs span {{
    background: var(--bg-elevated);
    padding: 2px 6px;
    border-radius: 4px;
}}
</style>
</head>
<body>
<header>
    <h1>28 张「临时抱佛脚训练集」原图画廊</h1>
    <div class="subtitle">已按 4 大核心维度（人体结构与引导、机位透视前景、动态瞬间、光线环境）归类归档 · 保留原始未经转码原图字节</div>
</header>
<div class="grid">
    {''.join(cards_html)}
</div>
</body>
</html>
"""
    out_html_path.write_text(html_content, encoding="utf-8")
    print(f"  + Generated HTML gallery: {out_html_path.name}")

def main():
    print("=== Processing 28 Crash Course Images ===")
    items = collect_items()
    print(f"Total items fetched: {len(items)}")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy files to categorized folders
    copied_count = 0
    for it in items:
        cat_dir = OUTPUT_DIR / it["group_dir"]
        cat_dir.mkdir(parents=True, exist_ok=True)
        dest_file = cat_dir / it["filename"]
        shutil.copy2(it["src_path"], dest_file)
        copied_count += 1

    print(f"Copied {copied_count} original images into categorized subfolders.")

    # 2. Generate contact sheet PDF
    pdf_path = OUTPUT_DIR / "contact_sheet.pdf"
    render_contact_sheet(items, pdf_path)

    # 3. Generate HTML gallery
    html_path = OUTPUT_DIR / "preview_gallery.html"
    generate_html_gallery(items, html_path)

    # 4. Generate README.md manifest
    readme_lines = [
        "# 28 张「临时抱佛脚训练集」原图索引清单",
        "",
        "> 本批次由 GPT 依据 Google Drive 确认保留资产筛选，专供人像/Cosplay实拍前突击复习。",
        "> 原图字节完整无损归档，分类清晰，附带接触印相表 PDF 与双击即可浏览的交互式 HTML 画廊。",
        "",
        "## 目录结构",
        "```",
        "28_临时抱佛脚训练集/",
        "├── 01_人体结构与引导/     (10 张: JK×6, KANA×1, XISHI×3)",
        "├── 02_机位与透视前景/     (6 张:  JK×6)",
        "├── 03_动态与moment瞬间/   (6 张:  JK×4, KANA×1, XISHI×1)",
        "├── 04_光线与环境处理/     (6 张:  JK×2, KANA×1, XISHI×1, INSP×2)",
        "├── contact_sheet.pdf      (高清接触印相表，可直接打印或手机/平板阅览)",
        "├── preview_gallery.html   (双击用浏览器打开，黑夜暗黑模式大图画廊)",
        "└── README.md              (详细元数据索引清单)",
        "```",
        "",
        "---",
        "",
        "## 详细图片清单",
        ""
    ]

    current_group = ""
    for it in items:
        if it["group_label"] != current_group:
            current_group = it["group_label"]
            readme_lines.extend([
                f"### {current_group}",
                "| 编号 | Asset ID | 角色 | 尺寸 | 格式 | 标题/主题 |",
                "| :--- | :--- | :--- | :---: | :---: | :--- |"
            ])
        readme_lines.append(
            f"| `{it['group_idx']:02d}` | **`{it['asset_id']}`** | {it['role']} | {it['width']}x{it['height']} | {it['ext'].upper()} | {it['title']} |"
        )

    readme_path = OUTPUT_DIR / "README.md"
    readme_path.write_text("\n".join(readme_lines), encoding="utf-8")
    print(f"  + Generated manifest: {readme_path.name}")

    # 5. Pack into ZIP
    print(f"\nCompressing into {ZIP_PATH.name}...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(OUTPUT_DIR.parent)
                zipf.write(full_path, rel_path)

    zip_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"  + Created ZIP: {ZIP_PATH} ({zip_size_mb:.2f} MB)")

    print("\n" + "="*70)
    print("ALL 28 IMAGES PACKED SUCCESSFULLY!")
    print(f"Folder Path: {OUTPUT_DIR}")
    print(f"ZIP Path   : {ZIP_PATH} ({zip_size_mb:.2f} MB)")
    print("="*70)

if __name__ == "__main__":
    main()
