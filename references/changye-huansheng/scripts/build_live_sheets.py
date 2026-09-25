#!/usr/bin/env python3
"""Build 7 clean category Contact Sheets for Live Edge / Pinterest Search Candidates."""

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "staging/live_manifest.json"
DIST_DIR = ROOT / "dist/live_contact_sheets"
DIST_DIR.mkdir(parents=True, exist_ok=True)

DIRECTION_TITLES = {
    "A_STANDING": "A 基础立姿 (Standing)",
    "B_TURN_BACK": "B 回眸/背身 (Turn Back)",
    "C_HANDS_FACE": "C 情绪/手部特写 (Hands & Face)",
    "D_LOW_STOOL": "D 矮凳/坐姿 (Low Stool)",
    "E_PROP": "E 法杖/道具交互 (Prop & Staff)",
    "F_LOW_ANGLE": "F 广角低机位 (Low Angle)",
    "G_DYNAMIC": "G 动态/披风甩动 (Dynamic & Fabric)"
}

def render_category_sheet(items, output_path, title, cols=4, thumb_w=360, thumb_h=520):
    padding = 20
    header_h = 90
    footer_slot_h = 45
    n = len(items)
    if n == 0:
        return
    rows_cnt = math.ceil(n / cols)

    total_w = cols * thumb_w + (cols + 1) * padding
    total_h = header_h + rows_cnt * (thumb_h + footer_slot_h) + padding

    sheet = Image.new("RGB", (total_w, total_h), color=(7, 9, 14))
    draw = ImageDraw.Draw(sheet)

    try:
        font_title = ImageFont.truetype("msyh.ttc", 30)
        font_label = ImageFont.truetype("msyh.ttc", 13)
        font_badge = ImageFont.truetype("msyh.ttc", 11)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    draw.text((padding, 24), title, fill=(0, 242, 255), font=font_title)
    draw.text((padding, 62), f"Total: {n} HD candidates | 打开 dist/review_live_search.html 进行交互式人工筛选与一键导出", fill=(148, 163, 184), font=font_badge)

    for i, r in enumerate(items):
        col = i % cols
        row = i // cols

        x = padding + col * (thumb_w + padding)
        y = header_h + row * (thumb_h + footer_slot_h)

        img_file = ROOT / r["file"]
        if img_file.exists():
            try:
                with Image.open(img_file) as im:
                    im_rgb = im.convert("RGB")
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

                    im_resized = im_cropped.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(im_resized, (x, y))
            except Exception as e:
                draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(20, 24, 35))
                draw.text((x + 10, y + 10), f"Error loading image", fill=(255, 100, 100), font=font_label)
        else:
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(20, 24, 35))
            draw.text((x + 10, y + 10), "File Missing", fill=(255, 100, 100), font=font_label)

        # Border around thumb
        draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(30, 41, 59), width=1)

        # ID badge in top-left
        cid = r["id"]
        draw.rectangle([x + 6, y + 6, x + 6 + 180, y + 26], fill=(0, 0, 0, 200))
        draw.text((x + 10, y + 8), cid, fill=(255, 255, 255), font=font_badge)

        # Resolution badge in top-right
        res_str = f"{r.get('width',0)}x{r.get('height',0)}"
        draw.rectangle([x + thumb_w - 76, y + 6, x + thumb_w - 6, y + 26], fill=(0, 242, 255, 50), outline=(0, 242, 255), width=1)
        draw.text((x + thumb_w - 72, y + 8), res_str, fill=(0, 242, 255), font=font_badge)

        # Text below card
        ty = y + thumb_h + 6
        query_short = r.get("query", "")[:35]
        draw.text((x, ty), f"🔍 {query_short}", fill=(203, 213, 225), font=font_label)
        draw.text((x, ty + 20), f"ID: {cid}", fill=(100, 116, 139), font=font_badge)

    sheet.save(output_path, quality=92)
    print(f"Rendered: {output_path.name} ({n} candidates)")

def main():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    by_dir = {}
    for it in items:
        d = it.get("direction", "UNKNOWN")
        by_dir.setdefault(d, []).append(it)

    for d, title in DIRECTION_TITLES.items():
        sub_items = by_dir.get(d, [])
        out_file = DIST_DIR / f"live_contact_{d}.jpg"
        render_category_sheet(sub_items, out_file, f"{d} - {title}")

if __name__ == "__main__":
    main()
