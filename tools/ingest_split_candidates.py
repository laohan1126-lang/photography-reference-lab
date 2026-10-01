"""
tools/ingest_split_candidates.py
Automatically splits multi-grid collages, evaluates individual sub-actions,
and directly ingests approved clean single-images into the active Project
so the user can review them in the main web UI (http://127.0.0.1:18765).
"""

from pathlib import Path
import io
import os
import sys
from PIL import Image

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.abspath("."))

from ref_lab.config import Settings
from ref_lab.service import Library
from ref_lab.models import CandidateInput, Source
from ref_lab.pose_pipeline import PoseIngestionPipeline

def ingest_split_poses_to_project(project_id: str, candidate_items: list):
    os.environ["LAB_DATA_DIR"] = "d:/AI PROJECTS/photography-reference-lab/data"
    settings = Settings.from_env()
    library = Library(settings)
    pipeline = PoseIngestionPipeline()

    print(f"Connecting to library at: {settings.data_dir}")
    project = library.project(project_id)
    print(f"Target Project: [{project['id']}] {project.get('character')} ({project.get('work')})")

    total_ingested = 0

    for idx, item in enumerate(candidate_items):
        title = item["title"]
        author = item.get("author", "未知作者")
        post_url = item.get("post_url", "https://www.xiaohongshu.com")
        image_path = item["image_path"]

        print(f"\n--- 处理笔记 [{idx+1}/{len(candidate_items)}]: 《{title}》 ---")
        img = Image.open(image_path)
        
        # 1. 运行切图与独立审美评估流水线
        res = pipeline.process_candidate({
            "title": title,
            "author": author,
            "full_text": item.get("full_text", title),
            "img": img
        })

        if res["status"] == "dropped_phase1":
            print(f"  [X] 初筛拦截抛弃: {res['reason']}")
            continue

        cards = res["delivered_cards"]
        print(f"  [√] 初筛通过 | 排版类型: {res['layout_type']} | 拆解出 {len(cards)} 张合格单图")

        # 2. 将每个合格的单图动作进行超采样清晰度重构并直接入库！
        for card in cards:
            sub_idx = card["sub_index"]
            sub_img = card["img"]
            pose_type = card["pose_type"]
            tag = card["tag"]
            reason = card["reason"]

            # --- 画质优化管线：超采样重构 + 摄影级锐化 ---
            from PIL import ImageFilter, ImageEnhance
            ow, oh = sub_img.size
            # 统一将切片放大到至少 600px 宽，保证在 Web 大图预览区 1:1 甚至高 PPI 显示不发糊
            scale = max(2, int(round(650.0 / ow)))
            target_w = ow * scale
            target_h = oh * scale
            hi_res = sub_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # UnsharpMask 摄影锐化微反差：恢复边缘线条感
            sharp = hi_res.filter(ImageFilter.UnsharpMask(radius=1.8, percent=145, threshold=2))
            # 略微提升微对比度，消除低清发白发雾感
            enhanced_img = ImageEnhance.Contrast(sharp).enhance(1.06)

            # 将重构后的高清 PIL Image 转为高质量 JPEG bytes
            buf = io.BytesIO()
            enhanced_img.save(buf, format="JPEG", quality=96)
            img_bytes = buf.getvalue()

            # 写入 asset 库
            asset_meta = library.ingest_asset(img_bytes, f"pose_{sub_idx:02d}.jpg")
            asset_sha = asset_meta["id"]

            # 构造候选单图名称与元数据
            card_title = f"【动作#{sub_idx:02d}·{tag}】{title}"
            import_key = f"split:{asset_sha[:16]}:{sub_idx}"

            source = Source(
                page_url=post_url,
                image_url=post_url,
                title=card_title,
                author=author,
                search_query="JK拍照姿势",
                rights="personal_reference",
                source_confirmed=False
            )

            cand_input = CandidateInput(
                title=card_title,
                source=source,
                import_key=import_key,
                legacy_notes=f"智能切分单动作: {pose_type} (审美评分 {card['aesthetic_score']}分)",
                discovery_intent="transferable_pose",
                discovery_reason=f"自适应多宫格拆分动作卡片 · {reason}",
                asset_sha=asset_sha
            )

            # 真正写入 refs 表，进入待审候选池 (decision='pending')
            add_res = library.add_candidate(project_id, cand_input, decision="pending", actor="auto_splitter")
            is_new = add_res.get("created", False)
            status_text = "新入库" if is_new else "已存在"
            print(f"    -> [动作 #{sub_idx:02d} {tag}] {status_text} | SHA: {asset_sha[:8]} | 状态: pending (待终审)")
            if is_new:
                total_ingested += 1

    print(f"\n==================================================")
    print(f"🎉 全部切分与入库完成！本次新增入库单图: {total_ingested} 张！")
    print(f"现在直接在主系统 (http://127.0.0.1:18765) 刷新即可在待审列表终审！")
    print(f"==================================================")

if __name__ == "__main__":
    JK_PROJECT_ID = "82c18730e7d1461ea0bac521ecb3414e"
    items_to_process = [
        {
            "title": "十一假期出游｜9组JK公园拍照万能姿势",
            "author": "摄影师小K",
            "post_url": "https://www.xiaohongshu.com/explore/jk_park_9",
            "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_11_613ef233.jpg",
            "full_text": "十一假期出游｜9组JK公园拍照万能姿势 动作教程 摄影客片 正片"
        },
        {
            "title": "【拯救动作废】适合故事感的双人拍照姿势x36",
            "author": "制服双人写真",
            "post_url": "https://www.xiaohongshu.com/explore/jk_pair_36",
            "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_12_8c0a89cc.jpg",
            "full_text": "双人拍照姿势 闺蜜互动 故事感拍照 动作参考"
        },
        {
            "title": "拍照姿势｜26个可爱jk坐姿参考☀️(室外版)",
            "author": "元气JK",
            "post_url": "https://www.xiaohongshu.com/explore/jk_sit_26",
            "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_10_30b1dd44.jpg",
            "full_text": "拍照姿势 26个可爱jk坐姿参考 室外版 摄影正片 摆姿"
        },
        {
            "title": "超简单jk拍照姿势 治愈系日常成片",
            "author": "夏日微风",
            "post_url": "https://www.xiaohongshu.com/explore/jk_single_01",
            "image_path": "inspections/fresh-jk-20-demo/images_kept/fresh_jk_01_1c81cc9d.jpg",
            "full_text": "超简单jk拍照姿势 治愈系日常外景 摄影客片 正片"
        }
    ]
    ingest_split_poses_to_project(JK_PROJECT_ID, items_to_process)
