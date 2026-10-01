"""
tools/run_collage_demo.py
Generate sliced pose cards, overlays, and manifest for the Interactive Collage Split Demo.
"""

import os
import json
from PIL import Image
import sys
sys.path.insert(0, os.path.abspath("."))
from tools.collage_splitter import CollageSplitter

splitter = CollageSplitter()

cases = [
    {
        'id': 'case_01',
        'title': '【9组JK公园拍照万能姿势】标准 3x3 九宫格切分',
        'source_name': 'fresh_jk_11_613ef233.jpg',
        'path': 'inspections/fresh-jk-20-demo/images_kept/fresh_jk_11_613ef233.jpg'
    },
    {
        'id': 'case_02',
        'title': '【26个可爱JK坐姿参考】标准 3x3 坐姿九宫格切分',
        'source_name': 'fresh_jk_10_30b1dd44.jpg',
        'path': 'inspections/fresh-jk-20-demo/images_kept/fresh_jk_10_30b1dd44.jpg'
    },
    {
        'id': 'case_03',
        'title': '【双人拍照姿势】非对称分层（上2下3）结构切分',
        'source_name': 'fresh_jk_12_8c0a89cc.jpg',
        'path': 'inspections/fresh-jk-20-demo/images_kept/fresh_jk_12_8c0a89cc.jpg'
    },
    {
        'id': 'case_04',
        'title': '【34个学姐系JK角色通用姿势】高密度复合拼贴全景切分',
        'source_name': 'fresh_jk_03_aeec709f.jpg',
        'path': 'inspections/fresh-jk-20-demo/images_kept/fresh_jk_03_aeec709f.jpg'
    }
]

out_base = 'inspections/collage-split-demo'
os.makedirs(out_base, exist_ok=True)

manifest = []

for case in cases:
    case_id = case['id']
    case_dir = os.path.join(out_base, case_id)
    os.makedirs(case_dir, exist_ok=True)

    img = Image.open(case['path'])
    res = splitter.split(img)

    orig_rel = f"{case_id}/original.jpg"
    orig_path = os.path.join(case_dir, "original.jpg")
    img.save(orig_path, quality=95)

    overlay_rel = f"{case_id}/overlay.jpg"
    overlay_path = os.path.join(case_dir, "overlay.jpg")
    res['overlay_img'].save(overlay_path, quality=95)

    sub_cards = []
    for idx, (box, sub_img) in enumerate(zip(res['boxes'], res['sub_images'])):
        fname = f"pose_{idx+1:02d}.jpg"
        sub_rel = f"{case_id}/{fname}"
        sub_path = os.path.join(case_dir, fname)

        w, h = sub_img.size
        # Lanczos upscale if small for crisp visual review
        if w < 180:
            scale = 2
            sub_disp = sub_img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
        else:
            sub_disp = sub_img
        sub_disp.save(sub_path, quality=95)

        sub_cards.append({
            'index': idx + 1,
            'rel_path': sub_rel,
            'box': box,
            'width': w,
            'height': h,
            'aspect_ratio': round(w / h, 2)
        })

    manifest.append({
        'id': case_id,
        'title': case['title'],
        'source_name': case['source_name'],
        'original_img': orig_rel,
        'overlay_img': overlay_rel,
        'layout_type': res['layout_type'],
        'count': res['count'],
        'sub_cards': sub_cards
    })
    print(f"Generated {case_id} ({res['layout_type']}): {len(sub_cards)} sub-cards.")

with open(os.path.join(out_base, 'split_manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("Demo generation completed! Total cases:", len(manifest))
