"""
tools/verify_pose_pipeline.py
Verify the unified Pose Ingestion & Slicing Pipeline on real Xiaohongshu samples.
Demonstrates:
- Phase 1: Note filter
- Phase 2: Automatic multi-grid slicing (collages become N single images, single portraits stay 1 image)
- Phase 3: Sub-card independent curation
- Phase 4: Delivered clean single images for final user review
"""

import os
import sys
from pathlib import Path
from PIL import Image

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.abspath("."))
from ref_lab.pose_pipeline import PoseIngestionPipeline

pipeline = PoseIngestionPipeline()

test_cases = [
    {
        "title": "十一假期出游｜9组JK公园拍照万能姿势",
        "author": "摄影师小K",
        "full_text": "十一假期出游｜9组JK公园拍照万能姿势 动作教程 摄影客片",
        "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_11_613ef233.jpg"
    },
    {
        "title": "【拯救动作废】适合故事感的双人拍照姿势x36",
        "author": "双人制服写真",
        "full_text": "双人拍照姿势 闺蜜互动 故事感拍照 动作参考",
        "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_12_8c0a89cc.jpg"
    },
    {
        "title": "超简单jk拍照姿势 治愈系日常成片",
        "author": "夏日微风",
        "full_text": "超简单jk拍照姿势 治愈系日常外景 摄影客片 正片",
        "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_01_1c81cc9d.jpg"
    },
    {
        "title": "出格裙 闲鱼全新出服转单包邮",
        "author": "二手买家",
        "full_text": "对镜自拍买家秀 试衣间 闲鱼 二手出物",
        "image_path": "inspections/fresh-jk-20-demo/images_dropped/dropped_031_8a654da2.jpg"
    }
]

out_dir = Path("inspections/pipeline-delivery-feed")
out_dir.mkdir(parents=True, exist_ok=True)
cards_dir = out_dir / "delivered_cards"
cards_dir.mkdir(parents=True, exist_ok=True)

feed = []
total_delivered = 0

print("==================================================")
print("🚀 运行端到端流水线：从搜图初筛 -> 自动切分 -> 独立单图审核 -> 最终交付")
print("==================================================")

for i, tc in enumerate(test_cases):
    img = Image.open(tc["image_path"])
    candidate = {
        "title": tc["title"],
        "author": tc["author"],
        "full_text": tc["full_text"],
        "img": img
    }
    res = pipeline.process_candidate(candidate)
    
    print(f"\n[Case {i+1}] 《{tc['title']}》")
    print(f"  - 初筛状态: {res['status']}")
    if res['status'] == 'dropped_phase1':
        print(f"  - 拦截原因: {res['reason']}")
    else:
        print(f"  - 排版类型: {res['layout_type']} (是否拼贴: {res['is_collage']})")
        print(f"  - 拆解出独立动作: {res['delivered_cards_count']} 张单图")
        
        for card in res['delivered_cards']:
            total_delivered += 1
            card_filename = f"feed_card_{total_delivered:03d}.jpg"
            card_path = cards_dir / card_filename
            card['img'].save(card_path, quality=95)
            
            feed.append({
                "feed_id": total_delivered,
                "file": f"delivered_cards/{card_filename}",
                "tag": card["tag"],
                "pose_type": card["pose_type"],
                "score": card["aesthetic_score"],
                "reason": card["reason"],
                "parent_title": card["parent_title"],
                "parent_author": card["parent_author"],
                "aspect_ratio": card["aspect_ratio"]
            })

print(f"\n==================================================")
print(f"✅ 处理完成！初筛通过并拆解出的最终交付单图总数: {total_delivered} 张！")
print("==================================================")

import json
with open(out_dir / "feed_manifest.json", "w", encoding="utf-8") as f:
    json.dump(feed, f, ensure_ascii=False, indent=2)
print("已保存落地单图清单至 inspections/pipeline-delivery-feed/feed_manifest.json")


