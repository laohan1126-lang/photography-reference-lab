#!/usr/bin/env python3
"""Build 7 clean category Contact Sheets for Pose Candidates."""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import yaml

ROOT = Path(__file__).resolve().parents[1]
CAND_YAML = ROOT / "data/pose_candidates.yaml"
DIST_DIR = ROOT / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

def render_category_sheet(items, output_path, title, cols=4, thumb_w=360, thumb_h=480):
    padding = 20
    header_h = 90
    footer_slot_h = 45
    n = len(items)
    if n == 0:
        return
    rows_cnt = math.ceil(n / cols)

    total_w = cols * thumb_w + (cols + 1) * padding
    total_h = header_h + rows_cnt * (thumb_h + footer_slot_h) + padding

    sheet = Image.new("RGB", (total_w, total_h), color=(6, 12, 24))
    draw = ImageDraw.Draw(sheet)

    try:
        font_title = ImageFont.truetype("msyh.ttc", 30)
        font_label = ImageFont.truetype("msyh.ttc", 14)
        font_badge = ImageFont.truetype("msyh.ttc", 12)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    draw.text((padding, 24), title, fill=(0, 242, 255), font=font_title)
    draw.text((padding, 62), f"Total: {n} candidates | 点击卡片在 review_pose_candidates.html 页面进行单项 KEEP / MAYBE / REJECT 选择", fill=(148, 163, 184), font=font_badge)

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
                    im_thumb = im_cropped.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(im_thumb, (x, y))
            except Exception:
                draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(15, 25, 45))

        # Top Badge: ID
        cid = r["candidate_id"]
        status = r.get("review_status", "CANDIDATE")
        q = r.get("quality_flag", "HQ")
        draw.rectangle([x + 6, y + 6, x + 90, y + 26], fill=(6, 12, 24))
        draw.text((x + 10, y + 8), cid, fill=(0, 242, 255), font=font_badge)

        # Status & Quality Badge
        status_color = (56, 189, 248) if status == "PRESELECTED" else (148, 163, 184)
        draw.rectangle([x + thumb_w - 95, y + 6, x + thumb_w - 6, y + 26], fill=(6, 12, 24))
        draw.text((x + thumb_w - 90, y + 8), f"{status[:4]}·{q[:3]}", fill=status_color, font=font_badge)

        # Labels below thumbnail
        tags_str = " ".join("#" + t for t in r.get("tags", [])[:2])
        obs = r.get("observed_pose", "")[:20]

        draw.text((x, y + thumb_h + 6), f"[{cid}] {tags_str}", fill=(241, 245, 249), font=font_label)
        draw.text((x, y + thumb_h + 24), obs, fill=(148, 163, 184), font=font_badge)

    sheet.save(output_path, "JPEG", quality=90)
    print(f"Generated {output_path} ({n} candidates)")

def build_all_candidate_sheets():
    with open(CAND_YAML, "r", encoding="utf-8") as f:
        candidates = yaml.safe_load(f)

    dir_map = {
        "A_STANDING": ("review_standing.jpg", "A. 柔和站姿 候选快速浏览板"),
        "B_TURN_BACK": ("review_turn_back.jpg", "B. 回眸 / 背身 / 侧身 候选快速浏览板"),
        "C_HANDS_FACE": ("review_hands_face.jpg", "C. 手势 / 面部 / 头纱互动 候选快速浏览板"),
        "D_LOW_STOOL": ("review_seated.jpg", "D. 小凳 / 低马扎坐姿 候选快速浏览板"),
        "E_PROP": ("review_prop.jpg", "E. 长柄道具 / 法杖 / 伞 / 乐器优雅互动 候选快速浏览板"),
        "F_LOW_ANGLE": ("review_low_angle.jpg", "F. 柔和低机位 候选快速浏览板"),
        "G_DYNAMIC": ("review_dynamic.jpg", "G. 小幅动态 候选快速浏览板")
    }

    for dir_key, (fn, title) in dir_map.items():
        items = [c for c in candidates if c.get("direction") == dir_key]
        out_fp = DIST_DIR / fn
        render_category_sheet(items, out_fp, title)

if __name__ == "__main__":
    build_all_candidate_sheets()
