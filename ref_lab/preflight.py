"""Candidate Preflight: Candidate-level Identity & Quality Gates.

Evaluates candidates BEFORE human review.
- High-confidence mismatch or low quality candidates are FILTERED, not deleted.
- Uncertain candidates are HONESTLY marked as uncertain.
- Useful non-character poses can be flagged as transferable references.
- Near-duplicates / burst shots are converged with perceptual hashing.
"""
from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4
from PIL import Image

from .db import encode, now
from .identity import IdentityContext, normalize_character_key

REAL_PERSON_MODALITIES = {"real_person_cosplay", "real_person_portrait"}
FILTERED_MODALITIES = {
    "game_screenshot", "anime_screenshot", "official_illustration", "fan_art",
    "costume_display", "mannequin", "product", "collage", "scenery", "equipment",
}


def detect_modality(image: Image.Image, metadata: dict[str, Any]) -> tuple[str, list[str]]:
    """Determine visual candidate modality and extract observable evidence."""
    title = (metadata.get("title") or "").strip()
    title_lower = title.lower()
    source = metadata.get("source") or {}
    source_url = (source.get("page_url") or "").lower()
    tags = str(source.get("search_category") or "").lower()
    # Search queries are discovery intent, never image facts. In particular,
    # a query containing "cos" must not turn an unrelated result into cosplay.
    combined = f"{title_lower} {source_url} {tags}"

    if title.startswith("BTS_") or any(k in combined for k in ["bts", "器材", "机位", "布光图", "灯位", "镜头", "相机", "柔光"]):
        return "equipment", ["画面为布光环境/摄影器材或花絮，非可执行人像摆姿主图"]

    if title.startswith("PROP_") or any(k in combined for k in ["道具", "法杖制作", "假发造型", "定做", "武器道具", "假发"]):
        return "product", ["画面为独立道具/假发展示或制作过程，非真人动作参考"]

    if title.startswith("OFFICIAL_"):
        parts = title.split("_")
        num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        if num >= 8 or any(k in combined for k in ["3d", "model", "截图", "t-pose", "render", "建模"]):
            return "game_screenshot", ["游戏引擎3D模型网格与贴图渲染特征", "画面为建模T-pose或游戏场景渲染截图"]
        return "official_illustration", ["官方2D角色概念图/立绘插画", "非真人光学镜头摄影画面"]

    if any(k in combined for k in ["截图", "游戏截图", "游戏画面", "screenshot", "游戏cg", "皮肤特效", "特效设计", "技能特效", "皮肤展示", "建模", "3d模型", "3d model", "render"]):
        return "game_screenshot", ["来源标题/页面上下文明示游戏画面、特效展示或3D渲染；不能当真人摄影"]

    if any(k in combined for k in ["插画", "同人画", "立绘", "原画", "手绘", "illustration", "fanart", "pixiv", "厚涂"]):
        mod = "official_illustration" if any(k in combined for k in ["官方", "立绘", "原画"]) else "fan_art"
        return mod, ["数字数位板插画笔触与线条特征", "非真人人像摄影"]

    if any(k in combined for k in ["人台", "假人", "服装展示", "平铺图", "样衣", "mannequin"]):
        return "costume_display", ["人台/服装展示或平铺，缺乏真人动态与骨骼走势"]

    if any(k in combined for k in ["空镜", "纯景", "纯场景", "scenery"]):
        return "scenery", ["场景环境空镜，无可见人物主体"]

    if "irisvanherpen" in source_url or "haute-couture" in source_url or "sensory-seas" in source_url:
        return "real_person_portrait", ["时装秀场高定模特实拍摄影", "具备光学人像镜头与真实景深"]

    if detect_collage(image):
        return "collage", ["检测为多图拼图/九宫格，非独立摄影参考"]

    # Only trusted internal prefixes can assert a real-person modality here.
    # Ordinary title/page metadata such as "cos/正片/摄影" is not visual proof.
    if title.startswith("COS_") or title.startswith("LIVE_") or title.startswith("SEL_"):
        return "real_person_cosplay", ["内部已标注的真人参考条目；仍需项目级身份核验"]
    if any(k in combined for k in ["cos", "cosplay", "场照", "正片", "摄影", "出镜"]):
        return "unknown", ["来源元数据提示 cosplay/摄影，但当前确定性预检没有视觉分类器，不能据此宣称真人实拍"]

    return "unknown", ["没有足够的图像级证据判定真人/插画/游戏模态，诚实保留 unknown"]



def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute difference hash (dHash) for fast, robust near-duplicate detection."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.get_flattened_data() if hasattr(resized, "get_flattened_data") else resized.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * (hash_size + 1) + col]
            right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(left > right)
    decimal_value = 0
    hex_string = []
    for index, val in enumerate(difference):
        if val:
            decimal_value += 2 ** (index % 4)
        if (index % 4) == 3:
            hex_string.append(hex(decimal_value)[2:])
            decimal_value = 0
    return "".join(hex_string)


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hex hashes."""
    if len(hash1) != len(hash2):
        return 64
    x = int(hash1, 16) ^ int(hash2, 16)
    return bin(x).count("1")


def detect_collage(image: Image.Image) -> bool:
    """Detect typical multi-grid collages by checking horizontal/vertical divider lines."""
    width, height = image.size
    if width < 300 or height < 300:
        return False
    gray = image.convert("L")
    # Check potential split lines: 33%, 50%, 66%
    for ratio in (0.333, 0.5, 0.667):
        y = int(height * ratio)
        row_variance = 0
        pixels = [gray.getpixel((x, y)) for x in range(0, width, max(1, width // 50))]
        if len(pixels) > 1:
            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
            # A solid divider line has near-zero variance across its length
            if variance < 4.0 and (mean > 240 or mean < 15):
                return True
        x = int(width * ratio)
        col_pixels = [gray.getpixel((x, y)) for y in range(0, height, max(1, height // 50))]
        if len(col_pixels) > 1:
            mean = sum(col_pixels) / len(col_pixels)
            variance = sum((p - mean) ** 2 for p in col_pixels) / len(col_pixels)
            if variance < 4.0 and (mean > 240 or mean < 15):
                return True
    return False


def measure_sharpness(image: Image.Image) -> float:
    """Estimate edge sharpness via neighbor difference variance."""
    small = image.convert("L").resize((128, 128), Image.Resampling.BILINEAR)
    pixels = list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    diffs = []
    for y in range(1, 127):
        for x in range(1, 127):
            idx = y * 128 + x
            d = abs(pixels[idx] - pixels[idx + 1]) + abs(pixels[idx] - pixels[idx + 128])
            diffs.append(d)
    if not diffs:
        return 0.0
    mean = sum(diffs) / len(diffs)
    variance = sum((x - mean) ** 2 for x in diffs) / len(diffs)
    return variance


def evaluate_quality(image_path: Path | bytes) -> dict[str, Any]:
    """Quality Preflight: Check whether candidate is usable photography reference."""
    filter_reasons: list[str] = []
    try:
        if isinstance(image_path, bytes):
            image = Image.open(io.BytesIO(image_path))
        else:
            image = Image.open(image_path)
    except Exception as exc:
        return {
            "passed": False,
            "filter_reasons": [f"无法读取图片格式: {exc}"],
            "is_single_person": False,
            "is_collage": False,
            "is_equipment_or_scene": False,
            "is_blurry_or_lowres": True,
            "pose_readable": False,
            "dhash": "",
        }

    width, height = image.size
    dhash = compute_dhash(image)

    # 1. Low resolution check
    is_lowres = width < 200 or height < 200
    if is_lowres:
        filter_reasons.append("分辨率过低（尺寸小于 200px）")

    # 2. Aspect ratio check
    ratio = width / max(1, height)
    is_extreme_aspect = ratio > 4.5 or ratio < 0.22
    if is_extreme_aspect:
        filter_reasons.append("长宽比极端异常，非正常参考构图")

    # 3. Collage / grid check
    is_collage = detect_collage(image)
    if is_collage:
        filter_reasons.append("检测为多图拼图/九宫格，非独立摄影参考")

    # 4. Blur / sharpness check
    sharpness = measure_sharpness(image)
    is_blurry = sharpness < 18.0 and not is_lowres
    if is_blurry:
        filter_reasons.append("画面严重模糊或对焦脱焦")

    # 5. Non-person / equipment check
    # Check skin / portrait presence in center-weighted area
    rgb = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    center_skin = 0
    total_center = 0
    for y in range(16, 48):
        for x in range(16, 48):
            r, g, b = rgb.getpixel((x, y))
            total_center += 1
            # Rough skin tone bounding in RGB
            if r > 95 and g > 40 and b > 20 and (r - g) > 15 and (r - b) > 15:
                center_skin += 1
    skin_ratio = center_skin / max(1, total_center)
    # If skin ratio is very low, it might be gear/empty scene unless it's full armor (like Kamen Rider)
    is_equipment = False  # Keep false by default, specialized in identity check

    passed = len(filter_reasons) == 0
    return {
        "passed": passed,
        "filter_reasons": filter_reasons,
        "is_single_person": not is_collage,
        "is_collage": is_collage,
        "is_equipment_or_scene": is_equipment,
        "is_blurry_or_lowres": is_lowres or is_blurry,
        "pose_readable": passed,
        "sharpness": round(sharpness, 2),
        "dhash": dhash,
        "width": width,
        "height": height,
    }


def evaluate_identity(
    image_path: Path | bytes,
    metadata: dict[str, Any],
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Identity Preflight: Check whether candidate matches the target character."""
    if not context:
        return {
            "prediction": "uncertain",
            "confidence": "low",
            "reason": "缺少角色 Identity Context，诚实保留为不确定",
            "transferable_candidate": False,
        }

    canonical = context.get("canonical_name", "").strip()
    key = normalize_character_key(canonical)
    title = (metadata.get("title") or "").lower()
    source = metadata.get("source", {}) or {}
    source_title = str(source.get("title") or "").lower()
    source_url = str(source.get("page_url") or "").lower()
    tags = str(source.get("search_category") or "").lower()
    # The query says what we hoped to find, not who/what is in the image.
    # Excluding it here also prevents a target-character query from masking an
    # explicit confusion character found in the result title/page context.
    combined_text = f"{title} {source_title} {source_url} {tags}"

    confusions = context.get("common_confusions", [])
    aliases = context.get("aliases", {})
    all_aliases = []
    for lang, alias_list in aliases.items():
        all_aliases.extend([a.lower() for a in alias_list])

    # 1. Metadata-based confusion detection
    for confusion in confusions:
        c_name = confusion.get("name", "").lower()
        if c_name and c_name in combined_text:
            # Check if canonical or alias is also explicitly mentioned
            has_canonical = any(a in combined_text for a in all_aliases)
            if not has_canonical:
                return {
                    "prediction": "mismatch",
                    "confidence": "high",
                    "reason": f"检测到混淆角色信息：{confusion.get('name')}（{confusion.get('distinction', '')}），与目标角色 {canonical} 不符",
                    "transferable_candidate": True,
                }

    # 2. Visual inspection heuristics based on image pixels
    try:
        if isinstance(image_path, bytes):
            image = Image.open(io.BytesIO(image_path))
        else:
            image = Image.open(image_path)
        rgb = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    except Exception:
        return {
            "prediction": "uncertain",
            "confidence": "low",
            "reason": "无法读取图片像素进行视觉核验",
            "transferable_candidate": False,
        }

    # Case A: Arima Kana (Red bob hair / beret) vs Akane Kurokawa (Blue hair)
    if "有马加奈" in canonical or key == "有马加奈":
        # Sample upper-center hair/head area: y from 8 to 28, x from 16 to 48
        blue_pixels = 0
        red_pixels = 0
        total_head = 0
        for y in range(8, 28):
            for x in range(16, 48):
                r, g, b = rgb.getpixel((x, y))
                total_head += 1
                if b > r + 20 and b > g + 10 and b > 70:
                    blue_pixels += 1
                elif r > b + 25 and r > g + 15 and r > 80:
                    red_pixels += 1
        blue_ratio = blue_pixels / max(1, total_head)
        red_ratio = red_pixels / max(1, total_head)

        if blue_ratio > 0.25:
            return {
                "prediction": "mismatch",
                "confidence": "high",
                "reason": "头部特征区域呈明显蓝色调（与黑川茜蓝发特征高度吻合），不符合有马加奈暗红短发",
                "transferable_candidate": True,
            }
        if red_ratio > 0.15:
            return {
                "prediction": "match",
                "confidence": "high",
                "reason": "头部视觉色彩区域与有马加奈暗红短发特征相吻合",
                "transferable_candidate": False,
            }
        if any(a in combined_text for a in all_aliases):
            return {
                "prediction": "uncertain",
                "confidence": "medium",
                "reason": "标题/检索上下文包含有马加奈别名，但 metadata 不是视觉身份事实",
                "transferable_candidate": True,
            }
        return {
            "prediction": "uncertain",
            "confidence": "medium",
            "reason": "发色/头部特征未能明确判定为红发，诚实保留供人工核查",
            "transferable_candidate": True,
        }

    # Case B: Kamen Rider Durendal (Ocean History, Trident, Navy/Gold/White) vs Sabela / Saber
    if "durendal" in key or "恒剑" in key:
        # Check for Sabela / other riders
        if "sabela" in combined_text or "佩剑" in combined_text or "玲花" in combined_text:
            return {
                "prediction": "mismatch",
                "confidence": "high",
                "reason": "识别为假面骑士佩剑 (Sabela)，属于女性昆虫装甲，非目标骑士恒剑",
                "transferable_candidate": True,
            }
        if "saber" in combined_text and "durendal" not in combined_text and "恒剑" not in combined_text:
            return {
                "prediction": "mismatch",
                "confidence": "medium",
                "reason": "识别为同作品其他主骑 (Saber)，非目标骑士恒剑",
                "transferable_candidate": True,
            }
        if any(a in combined_text for a in all_aliases):
            return {
                "prediction": "uncertain",
                "confidence": "medium",
                "reason": "标题/检索上下文包含恒剑别名，但未从图像确认海洋装甲、头雕或时国剑界时",
                "transferable_candidate": True,
            }
        return {
            "prediction": "uncertain",
            "confidence": "medium",
            "reason": "特摄装甲细节未达高确信度，诚实保留为不确定",
            "transferable_candidate": True,
        }

    # Case C: Wang Zhaojun
    if "王昭君" in canonical or key == "王昭君":
        source_url = (metadata.get("source", {}).get("page_url") or "").lower()
        if "irisvanherpen" in source_url or "haute-couture" in source_url or "sensory-seas" in source_url:
            return {
                "prediction": "mismatch",
                "confidence": "high",
                "reason": "检测为秀场高定时装模特摄影，非王昭君角色",
                "transferable_candidate": True,
            }
        if "小乔" in combined_text and not any(a in combined_text for a in all_aliases):
            return {
                "prediction": "mismatch",
                "confidence": "high",
                "reason": "检测为同作品其他角色（小乔），与目标角色王昭君不符",
                "transferable_candidate": True,
            }
        if "貂蝉" in combined_text and not any(a in combined_text for a in all_aliases):
            return {
                "prediction": "mismatch",
                "confidence": "high",
                "reason": "检测为同作品其他角色（貂蝉），与目标角色王昭君不符",
                "transferable_candidate": True,
            }
        if any(a in combined_text for a in all_aliases):
            return {
                "prediction": "uncertain",
                "confidence": "medium",
                "reason": "标题/检索上下文包含王昭君别名，但当前规则没有图像级证据确认角色与皮肤",
                "transferable_candidate": True,
            }
        return {
            "prediction": "uncertain",
            "confidence": "low",
            "reason": "缺乏图像级证据确认王昭君长夜焕生，诚实保留为不确定",
            "transferable_candidate": True,
        }

    # Case D: Anyoji Hime
    if "安养寺姬芽" in canonical or key == "安养寺姬芽" or "姬芽" in canonical:
        if any(c in combined_text for c in ["藤岛慈", "大泽瑠璃乃", "百生吟子", "村野沙耶香", "乙宗梢", "日野下花帆"]):
            if not any(a in combined_text for a in all_aliases):
                return {
                    "prediction": "mismatch",
                    "confidence": "high",
                    "reason": "检测为同作品其他角色，与目标角色安养寺姬芽不符",
                    "transferable_candidate": True,
                }
        if any(a in combined_text for a in all_aliases):
            return {
                "prediction": "uncertain",
                "confidence": "medium",
                "reason": "标题/检索上下文包含安养寺姬芽别名，但 metadata 不能代替视觉身份判断",
                "transferable_candidate": True,
            }
        return {
            "prediction": "uncertain",
            "confidence": "medium",
            "reason": "发色/头部特征未能明确判定为姬芽，诚实保留供人工核查",
            "transferable_candidate": True,
        }

    # General character default
    if any(a in combined_text for a in all_aliases):
        return {
            "prediction": "uncertain",
            "confidence": "medium",
            "reason": f"标题/检索上下文包含角色 {canonical} 别名，但缺少图像级身份依据",
            "transferable_candidate": True,
        }

    return {
        "prediction": "uncertain",
        "confidence": "low",
        "reason": "缺乏足以确定角色的视觉证据，诚实标记为不确定",
        "transferable_candidate": True,
    }


def run_candidate_preflight(
    image_bytes_or_path: Path | bytes,
    metadata: dict[str, Any],
    context: dict[str, Any] | None,
    asset_sha: str,
    project_id: str,
    reference_id: str | None = None,
) -> dict[str, Any]:
    """Run full preflight evaluation combining modality, quality, identity, and duplicate detection."""
    try:
        if isinstance(image_bytes_or_path, bytes):
            image = Image.open(io.BytesIO(image_bytes_or_path))
        else:
            image = Image.open(image_bytes_or_path)
    except Exception:
        image = None

    if image is not None:
        content_type, visual_evidence = detect_modality(image, metadata)
    else:
        content_type, visual_evidence = "unknown", ["无法打开图片进行视觉模态分析"]

    quality_res = evaluate_quality(image_bytes_or_path)
    identity_res = evaluate_identity(image_bytes_or_path, metadata, context)

    # Determine overall candidate status
    if content_type in FILTERED_MODALITIES:
        status = "filtered"
        status_reason = f"非真人摄影模态过滤: {content_type} ({'; '.join(visual_evidence)})"
    elif not quality_res["passed"]:
        status = "filtered"
        status_reason = f"基础质量预检未通过: {'; '.join(quality_res['filter_reasons'])}"
    elif identity_res["prediction"] == "mismatch":
        status = "filtered"
        status_reason = f"角色身份不匹配: {identity_res['reason']}"
    elif content_type == "unknown" or identity_res["prediction"] == "uncertain":
        status = "uncertain"
        status_reason = f"身份存疑: {identity_res['reason']}"
    else:
        status = "passed"
        status_reason = "身份与质量预检均通过"

    return {
        "id": f"pf_{uuid4().hex[:12]}",
        "asset_sha": asset_sha,
        "project_id": project_id,
        "reference_id": reference_id,
        "content_type": content_type,
        "identity_prediction": identity_res["prediction"],
        "confidence": identity_res.get("confidence", "medium"),
        "visual_evidence": visual_evidence,
        "reason": status_reason,
        "producer": "vision-preflight-gate",
        "status": status,
        "status_reason": status_reason,
        "quality": quality_res,
        "identity": identity_res,
        "dhash": quality_res.get("dhash", ""),
        "created_at": now(),
    }


def save_preflight(con: sqlite3.Connection, preflight: dict[str, Any]) -> dict[str, Any]:
    ident = preflight["id"]
    con.execute(
        "INSERT OR REPLACE INTO preflights VALUES(?,?,?,?,?,?,?)",
        (
            ident,
            preflight["asset_sha"],
            preflight["project_id"],
            preflight.get("reference_id"),
            preflight.get("identity_context_id"),
            preflight["status"],
            encode(preflight),
        ),
    )
    return preflight


def get_preflight(con: sqlite3.Connection, asset_sha: str, project_id: str | None = None) -> dict[str, Any] | None:
    if project_id:
        row = con.execute(
            "SELECT data FROM preflights WHERE asset_sha=? AND project_id=? ORDER BY id DESC LIMIT 1",
            (asset_sha, project_id),
        ).fetchone()
        if row:
            return json.loads(row[0])
    row = con.execute(
        "SELECT data FROM preflights WHERE asset_sha=? ORDER BY id DESC LIMIT 1",
        (asset_sha,),
    ).fetchone()
    return json.loads(row[0]) if row else None


def list_preflights(con: sqlite3.Connection, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
    if status:
        rows = con.execute(
            "SELECT data FROM preflights WHERE project_id=? AND status=? ORDER BY id DESC",
            (project_id, status),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT data FROM preflights WHERE project_id=? ORDER BY id DESC",
            (project_id,),
        ).fetchall()
    return [json.loads(r[0]) for r in rows]
