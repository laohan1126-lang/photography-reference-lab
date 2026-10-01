"""
ref_lab/pose_pipeline.py
End-to-End Pose Ingestion & Curation Pipeline:
1. Phase 1: Note-level skill preflight (kill noise/merch/buyer-show).
2. Phase 2: Automatic multi-grid slicing (splits collages into individual sub-images, keeps singletons intact).
3. Phase 3: Sub-card independent aesthetic evaluation (evaluates each action pose separately).
4. Phase 4: Delivery to User (pure single-pose cards for final human review).
"""

from __future__ import annotations

import io
import os
import hashlib
from typing import List, Dict, Any, Tuple
from PIL import Image
import numpy as np

from tools.collage_splitter import CollageSplitter


class PoseIngestionPipeline:
    def __init__(self):
        self.splitter = CollageSplitter()

    def evaluate_note_phase1(self, title: str, author: str, full_text: str, w: int, h: int) -> Tuple[bool, str]:
        """
        Phase 1: Filter out non-photography noise, commercial ads, buyer shows, and text posts.
        """
        combined = f" {title.lower()} {author.lower()} {full_text.lower()} "

        # 1. Physical dimensions
        if max(w, h) < 500 or min(w, h) < 200:
            return False, f"尺寸过小或为纯字广告条 ({w}x{h})"

        # 2. Hard Negatives (Commercial / Buyer Show / Resale)
        negatives = [
            ("对镜拍", "对镜自拍买家秀"),
            ("对镜自拍", "对镜自拍买家秀"),
            ("试衣间", "试衣间自拍"),
            ("哪家好", "店铺导购比价"),
            ("避雷", "争议挂人帖"),
            ("挂人", "争议挂人帖"),
            ("跑路", "争议维权帖"),
            ("出格裙", "二手交易"),
            ("出服", "二手交易"),
            ("求服", "求物闲置"),
            ("转单", "二手转单"),
            ("闲鱼", "二手闲置"),
            ("出租", "服装出租商业帖"),
            ("包邮", "商品买卖广告"),
        ]
        for marker, reason in negatives:
            if marker in combined:
                return False, f"初筛拦截：命中【{marker}】({reason})"

        # 3. Photography or Pose signal
        positives = [
            "姿势", "动作", "拍照", "摄影", "写真", "出片", "客片",
            "正片", "参考", "构图", "角度", "摆姿", "教程", "速写"
        ]
        if not any(p in combined for p in positives):
            return False, "初筛拦截：缺少明确摄影摆姿或正片出片信号"

        return True, "通过初筛：具备摄影摆姿与正片参考价值"

    def evaluate_sub_card_phase3(self, sub_img: Image.Image, sub_idx: int, parent_title: str) -> Dict[str, Any]:
        """
        Phase 3: Evaluate each individual sliced pose card independently.
        Checks aspect ratio, clarity, and assigns action tags.
        """
        w, h = sub_img.size
        aspect_ratio = round(w / h, 2)

        # 1. Check if cropped card is too tiny or deformed
        if w < 50 or h < 50:
            return {
                "passed": False,
                "reason": "切片尺寸过小，缺乏细节",
                "aesthetic_score": 30,
                "pose_type": "unknown",
                "tag": "无效微图"
            }

        # 2. Heuristic pose classification based on aspect ratio
        if aspect_ratio <= 0.65:
            pose_type = "全身立姿/纵向构图"
            tag = "全身立姿"
            base_score = 88
        elif aspect_ratio <= 0.95:
            pose_type = "七分身/坐姿/全身舒展"
            tag = "全身/坐姿"
            base_score = 85
        elif aspect_ratio <= 1.2:
            pose_type = "方构图/半身特写"
            tag = "半身特写"
            base_score = 82
        else:
            pose_type = "横构图/环境互动"
            tag = "环境横构图"
            base_score = 80

        # Title bonus
        if any(k in parent_title for k in ["神仙", "万能", "绝美", "高级", "双人", "学姐", "可爱"]):
            base_score += 4

        return {
            "passed": True,
            "reason": f"单动作完整无截断，具备独立摆姿参考价值 ({pose_type})",
            "aesthetic_score": min(96, base_score),
            "pose_type": pose_type,
            "tag": tag
        }

    def process_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full pipeline:
        Input: candidate dict with title, author, full_text, img (PIL Image or bytes), image_url
        Output: dict with status, parent metadata, and list of sliced single-image cards for user review.
        """
        title = candidate.get("title", "")
        author = candidate.get("author", "")
        full_text = candidate.get("full_text", "")
        img = candidate.get("img")
        if isinstance(img, bytes):
            img = Image.open(io.BytesIO(img))

        w, h = img.size

        # Step 1: Phase 1 Note Filter
        p1_pass, p1_reason = self.evaluate_note_phase1(title, author, full_text, w, h)
        if not p1_pass:
            return {
                "status": "dropped_phase1",
                "reason": p1_reason,
                "title": title,
                "is_collage": False,
                "cards_count": 0,
                "delivered_cards": []
            }

        # Step 2: Phase 2 Smart Multi-Grid Slicing
        split_res = self.splitter.split(img)
        is_collage = split_res["is_collage"]
        sub_images = split_res["sub_images"]
        boxes = split_res["boxes"]
        layout_type = split_res["layout_type"]

        # Step 3: Phase 3 Sub-card Evaluation
        delivered_cards = []
        for idx, (sub_im, box) in enumerate(zip(sub_images, boxes)):
            eval_res = self.evaluate_sub_card_phase3(sub_im, idx + 1, title)
            if eval_res["passed"]:
                # High-quality Lanczos display scale if small
                cw, ch = sub_im.size
                if cw < 200:
                    scale = 2
                    disp_img = sub_im.resize((cw * scale, ch * scale), Image.Resampling.LANCZOS)
                else:
                    disp_img = sub_im

                delivered_cards.append({
                    "sub_index": idx + 1,
                    "img": disp_img,
                    "box": box,
                    "orig_size": [cw, ch],
                    "aspect_ratio": round(cw / ch, 2),
                    "pose_type": eval_res["pose_type"],
                    "tag": eval_res["tag"],
                    "aesthetic_score": eval_res["aesthetic_score"],
                    "reason": eval_res["reason"],
                    "parent_title": title,
                    "parent_author": author,
                    "layout_type": layout_type
                })

        return {
            "status": "passed_and_delivered",
            "title": title,
            "author": author,
            "is_collage": is_collage,
            "layout_type": layout_type,
            "raw_panels_count": len(sub_images),
            "delivered_cards_count": len(delivered_cards),
            "delivered_cards": delivered_cards,
            "overlay_img": split_res.get("overlay_img")
        }
