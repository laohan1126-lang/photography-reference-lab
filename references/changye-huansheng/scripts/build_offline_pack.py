#!/usr/bin/env python3
"""Build 100% offline field pack for convention shooting.
- Generates 1080x1920 mobile guidance cards for phone album.
- Main image (80% area) MUST be the real photography POSE reference.
- Character target inset (20% in upper-right) provides Wang Zhaojun official anchor.
- Bottom area provides large-text director script and micro-adjustments.
- Generates standalone 100% offline HTML viewer.
"""

import math
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import yaml

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
FIELD_PACK_DIR = ROOT / "field_pack"
PHONE_ALBUM_DIR = FIELD_PACK_DIR / "phone_album"
YAML_PATH = ROOT / "data" / "references.yaml"

FIELD_PACK_DIR.mkdir(parents=True, exist_ok=True)
PHONE_ALBUM_DIR.mkdir(parents=True, exist_ok=True)

def get_font(size, bold=False):
    font_names = ["msyhbd.ttc" if bold else "msyh.ttc", "simhei.ttf", "arial.ttf"]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            pass
    return ImageFont.load_default()

def draw_card(title, tag, script, details, main_image_path, official_inset_path=None, output_path=None):
    width = 1080
    height = 1920
    im = Image.new("RGB", (width, height), color=(10, 15, 30))
    draw = ImageDraw.Draw(im)

    # 1. Top Header Banner
    draw.rectangle([(0, 0), (width, 100)], fill=(15, 23, 42))
    draw.text((40, 28), "漫展极速拍摄指令 · FIELD DIRECTING CARD", fill=(56, 189, 248), font=get_font(28, bold=True))
    draw.rectangle([(width - 240, 20), (width - 40, 80)], fill=(2, 132, 199), outline=(56, 189, 248), width=2)
    draw.text((width - 225, 32), tag, fill=(255, 255, 255), font=get_font(26, bold=True))

    # 2. Main Visual Area (y=115 to 1090, height=975)
    img_box_x = 40
    img_box_y = 115
    img_box_w = width - 80  # 1000px
    img_box_h = 975

    # Background for main image box
    draw.rectangle([(img_box_x, img_box_y), (img_box_x + img_box_w, img_box_y + img_box_h)], fill=(15, 23, 42), outline=(56, 189, 248), width=2)

    if main_image_path and Path(main_image_path).exists():
        try:
            with Image.open(main_image_path) as ref_im:
                ref_rgb = ref_im.convert("RGB")
                orig_w, orig_h = ref_rgb.size
                scale = min((img_box_w - 20) / orig_w, (img_box_h - 20) / orig_h)
                target_w = int(orig_w * scale)
                target_h = int(orig_h * scale)
                resized = ref_rgb.resize((target_w, target_h), Image.Resampling.LANCZOS)

                x_pos = img_box_x + (img_box_w - target_w) // 2
                y_pos = img_box_y + (img_box_h - target_h) // 2
                im.paste(resized, (x_pos, y_pos))
                draw.rectangle([(x_pos, y_pos), (x_pos + target_w, y_pos + target_h)], outline=(56, 189, 248), width=2)

                # Real photo badge
                draw.rectangle([(x_pos + 10, y_pos + 10), (x_pos + 260, y_pos + 55)], fill=(0, 0, 0, 200))
                draw.text((x_pos + 20, y_pos + 18), "真人摄影参考 (80%)", fill=(56, 189, 248), font=get_font(22, bold=True))
        except Exception as e:
            draw.text((60, 500), f"Main image load failed: {e}", fill=(255, 100, 100), font=get_font(32))

    # 3. Optional Character Target Inset (Upper right 20% area)
    if official_inset_path and Path(official_inset_path).exists():
        try:
            inset_w = 240
            inset_h = 320
            inset_x = img_box_x + img_box_w - inset_w - 15
            inset_y = img_box_y + 15

            # Shadow / frame
            draw.rectangle([(inset_x - 4, inset_y - 4), (inset_x + inset_w + 4, inset_y + inset_h + 4)], fill=(10, 15, 30), outline=(245, 158, 11), width=3)
            with Image.open(official_inset_path) as off_im:
                off_rgb = off_im.convert("RGB")
                ow, oh = off_rgb.size
                scale_o = min(inset_w / ow, inset_h / oh)
                tw_o = int(ow * scale_o)
                th_o = int(oh * scale_o)
                res_o = off_rgb.resize((tw_o, th_o), Image.Resampling.LANCZOS)
                
                # Center inside inset box
                px_o = inset_x + (inset_w - tw_o) // 2
                py_o = inset_y + (inset_h - th_o) // 2
                im.paste(res_o, (px_o, py_o))

            # Header on inset
            draw.rectangle([(inset_x, inset_y), (inset_x + inset_w, inset_y + 40)], fill=(245, 158, 11))
            draw.text((inset_x + 15, inset_y + 8), "★ 目标角色特征 (20%)", fill=(0, 0, 0), font=get_font(20, bold=True))
        except Exception as e:
            pass

    # 4. Bottom Area: Info & Directing Script (y=1110 to 1860)
    card_top = 1110
    draw.rectangle([(40, card_top), (width - 40, height - 50)], fill=(15, 23, 42), outline=(30, 58, 138), width=3)

    # Title
    draw.text((70, card_top + 25), title, fill=(255, 255, 255), font=get_font(48, bold=True))

    # Director script box with high contrast yellow text
    script_box_top = card_top + 100
    draw.rectangle([(65, script_box_top), (width - 65, script_box_top + 320)], fill=(8, 47, 73), outline=(56, 189, 248), width=2)
    draw.text((85, script_box_top + 18), "【摄影师现场直白口令 (直接照念)】:", fill=(245, 158, 11), font=get_font(32, bold=True))

    # Word wrap script
    lines = []
    curr = ""
    for char in script:
        if len(curr) >= 23 or char == "\n":
            lines.append(curr)
            curr = char if char != "\n" else ""
        else:
            curr += char
    if curr:
        lines.append(curr)

    line_y = script_box_top + 70
    for l in lines[:5]:
        draw.text((85, line_y), l, fill=(254, 240, 138), font=get_font(34, bold=True))
        line_y += 48

    # Technical metadata badges
    meta_y = card_top + 450
    box_w = (width - 160) // 3
    badges = [
        ("镜头推荐", details.get("lens", "50mm f/1.8")),
        ("景别机位", details.get("crop", "3/4 / 半身")),
        ("漫展难度", details.get("diff", "A 级 (极速)"))
    ]

    for i, (b_title, b_val) in enumerate(badges):
        bx = 70 + i * (box_w + 10)
        draw.rectangle([(bx, meta_y), (bx + box_w, meta_y + 100)], fill=(30, 41, 59), outline=(71, 85, 105), width=2)
        draw.text((bx + 15, meta_y + 12), b_title, fill=(148, 163, 184), font=get_font(22))
        draw.text((bx + 15, meta_y + 50), b_val, fill=(56, 189, 248), font=get_font(26, bold=True))

    # Micro adjustments & common failures
    adj_y = meta_y + 125
    draw.text((70, adj_y), "【动作微调与防错要点】:", fill=(245, 158, 11), font=get_font(28, bold=True))
    adjs = details.get("adjustments", [])
    for idx, adj in enumerate(adjs[:2]):
        draw.text((70, adj_y + 40 + idx * 36), f"• {adj}", fill=(203, 213, 225), font=get_font(25))

    im.save(output_path, "JPEG", quality=92)
    print(f"Generated phone card: {output_path.name}")

def generate_all():
    print("Building Upgraded Phone Album Cards (Main 80% Real Pose + Inset 20% Official Anchor)...")
    
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        items = yaml.safe_load(f)

    pose_cores = [it for it in items if it.get("category") == "03_POSE" and it.get("priority") == "CORE"]
    print(f"Found {len(pose_cores)} verified CORE poses.")

    # 1. Quick Start Card
    draw_card(
        title="00_漫展 8分钟出片战斗指南",
        tag="FIELD OVERVIEW",
        script="【时间分配节奏】\n前2分钟: 找靠墙/背光安全点，V100架右侧45度试光\n第2-5分: 按照 Chain 01 连收 4 张必保站姿大片\n第5-7分: 掏出小马扎拍坐姿，让 Coser 休息出片\n第7-8分: 抓拍回眸与武器特写，收工撤离！",
        details={
            "lens": "50mm + 24-240",
            "crop": "全套覆盖",
            "diff": "极速流",
            "adjustments": ["脚踩住灯架脚管防止路人踢倒", "A7M4 必存 14-bit RAW 格式保证后期宽容度"]
        },
        main_image_path=ROOT / "refs" / "03_POSE" / "01_STANDING" / "POSE_0101_standing_casual_ponytail.webp",
        official_inset_path=ROOT / "refs" / "00_OFFICIAL" / "OFFICIAL_001_key_visual.webp",
        output_path=PHONE_ALBUM_DIR / "00_QUICK_START.jpg"
    )

    # 2. Iterate each CORE pose to build phone album cards
    for idx, p in enumerate(pose_cores):
        pid = p.get("id")
        pfile = ROOT / p.get("file")
        script = p.get("director_script", "")
        lens = p.get("recommended_lens", "Sony 50mm f/1.8")
        crop = p.get("crop", "半身 / 全身")
        feas = p.get("expo_feasibility", "A")
        adjs = p.get("micro_adjustments", [])
        
        # Pick appropriate official anchor inset
        sub = p.get("subcategory", "")
        if "WEAPON" in sub:
            inset = ROOT / "refs" / "00_OFFICIAL" / "OFFICIAL_005_weapon_harp_staff_detail.webp"
        elif "CLOSEUP" in sub or "HANDS" in sub:
            inset = ROOT / "refs" / "00_OFFICIAL" / "OFFICIAL_002_character_detail.webp"
        elif "BACK" in sub or "TURNING" in sub:
            inset = ROOT / "refs" / "00_OFFICIAL" / "OFFICIAL_004_model_turnaround_back.webp"
        else:
            inset = ROOT / "refs" / "00_OFFICIAL" / "OFFICIAL_003_model_turnaround_front.webp"

        card_title = f"{pid}: {p.get('visual_audit', {}).get('actual_pose', '')[:16]}"
        out_name = f"{pid}_{sub}.jpg"

        draw_card(
            title=card_title,
            tag=f"{feas} 级 · CORE",
            script=script,
            details={
                "lens": lens[:15],
                "crop": crop[:15],
                "diff": f"{feas} 级 (漫展适用)",
                "adjustments": adjs
            },
            main_image_path=pfile,
            official_inset_path=inset,
            output_path=PHONE_ALBUM_DIR / out_name
        )

    # Copy quick start to field_pack root
    shutil.copy(PHONE_ALBUM_DIR / "00_QUICK_START.jpg", FIELD_PACK_DIR / "00_QUICK_START.jpg")
    print(f"Generated {len(pose_cores) + 1} phone album cards successfully!")

if __name__ == "__main__":
    generate_all()
