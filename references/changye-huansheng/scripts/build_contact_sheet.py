#!/usr/bin/env python3
"""Generate high-resolution contact sheets from data/references.yaml."""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "data" / "references.yaml"
DIST_DIR = ROOT / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

def render_sheet(items, output_path, title, subtitle, cols=5, thumb_w=360, thumb_h=480):
    padding = 20
    header_h = 110
    n = len(items)
    if n == 0:
        return
    rows_cnt = math.ceil(n / cols)

    total_w = cols * thumb_w + (cols + 1) * padding
    total_h = header_h + rows_cnt * (thumb_h + 50) + padding

    sheet = Image.new("RGB", (total_w, total_h), color=(5, 11, 24))
    draw = ImageDraw.Draw(sheet)

    try:
        font_title = ImageFont.truetype("msyh.ttc", 36)
        font_sub = ImageFont.truetype("msyh.ttc", 18)
        font_label = ImageFont.truetype("msyh.ttc", 15)
        font_badge = ImageFont.truetype("msyh.ttc", 13)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    draw.text((padding, 25), title, fill=(0, 242, 255), font=font_title)
    draw.text((padding, 72), subtitle, fill=(148, 163, 184), font=font_sub)

    pri_colors = {
        "CORE": (0, 242, 255),
        "SUPPORT": (74, 222, 128),
        "OPTIONAL": (255, 183, 77),
        "REJECT": (255, 82, 82)
    }

    for i, r in enumerate(items):
        col = i % cols
        row = i // cols

        x = padding + col * (thumb_w + padding)
        y = header_h + row * (thumb_h + 50)

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
                    im_thumb = im_cropped.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(im_thumb, (x, y))
            except Exception as e:
                draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(15, 25, 45))
                draw.text((x + 10, y + 10), f"Error loading image", fill=(255, 100, 100), font=font_label)

        # Draw Priority Badge on top left of thumbnail
        pri = r.get("priority", "SUPPORT")
        badge_color = pri_colors.get(pri, (200, 200, 200))
        draw.rectangle([x + 6, y + 6, x + 75, y + 26], fill=(5, 11, 24))
        draw.text((x + 12, y + 8), pri, fill=badge_color, font=font_badge)

        # Labels below thumbnail
        ref_id = r.get("id", "UNK")
        cat = r.get("category", "")
        author = r.get("source", {}).get("author", "")[:18]
        rel = int(r.get("target_relevance", 0.0) * 100)
        tech = int(r.get("technical_value", 0.0) * 100)

        draw.text((x, y + thumb_h + 6), f"[{ref_id}] {cat}", fill=(241, 245, 249), font=font_label)
        draw.text((x, y + thumb_h + 26), f"{author} (R:{rel}% T:{tech}%)", fill=(148, 163, 184), font=font_badge)

    sheet.save(output_path, "JPEG", quality=90)
    print(f"Generated: {output_path} ({n} items)")

def build_all_sheets():
    with open(DATA_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 1. Full Contact Sheet
    render_sheet(
        data,
        DIST_DIR / "contact_sheet_all.jpg",
        "王昭君·长夜焕生 摄影视觉参考总览 (FULL CONTACT SHEET)",
        f"Total: {len(data)} items | 覆盖 00_OFFICIAL ~ 07_BTS & 90_REJECTED | Single Source: data/references.yaml",
        cols=6, thumb_w=300, thumb_h=400
    )

    # 2. CORE Only Contact Sheet (High Priority on-set board)
    core_items = [r for r in data if r.get("priority") == "CORE"]
    render_sheet(
        core_items,
        DIST_DIR / "contact_sheet_core.jpg",
        "王昭君·长夜焕生 摄影现场核心板 (CORE ANCHOR SHEET)",
        f"Total: {len(core_items)} items | 仅收录高价值核心参考（官方证据、实战灯位、高定仿生与悬浮动线）",
        cols=4, thumb_w=380, thumb_h=500
    )

    # 3. CORE POSE Dedicated Sheet (Step 9 requirement)
    pose_core_items = [r for r in data if r.get("category") == "03_POSE" and r.get("priority") == "CORE"]
    render_sheet(
        pose_core_items,
        DIST_DIR / "contact_sheet_pose_core.jpg",
        "王昭君·长夜焕生 漫展实战真人姿态核心板 (10 TRUE CORE POSES)",
        f"Total: {len(pose_core_items)} items | 100% 人工视觉核对 | 短边>=1080px | 覆盖 8 大动作原型 | 9 个独立来源 | 单灯直出",
        cols=4, thumb_w=380, thumb_h=520
    )

    # 4. Category sheets
    for cat in ["00_OFFICIAL", "01_COSTUME", "04_LIGHTING", "07_BTS_TECHNICAL"]:
        cat_items = [r for r in data if r.get("category") == cat]
        if cat_items:
            render_sheet(
                cat_items,
                DIST_DIR / f"contact_sheet_{cat}.jpg",
                f"王昭君·长夜焕生 分类参考板 - {cat}",
                f"Total: {len(cat_items)} items",
                cols=4 if len(cat_items) >= 4 else len(cat_items),
                thumb_w=360, thumb_h=480
            )

if __name__ == "__main__":
    build_all_sheets()
