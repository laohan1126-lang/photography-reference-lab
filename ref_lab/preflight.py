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

FILTERED_MODALITIES = {
    "game_screenshot", "anime_screenshot", "official_illustration", "fan_art",
    "costume_display", "mannequin", "product", "collage", "scenery", "equipment",
}


def detect_modality(image: Image.Image, metadata: dict[str, Any]) -> tuple[str, list[str]]:
    """Pixel heuristic only. Source text cannot classify the depicted subject."""
    if detect_collage(image):
        return "collage", ["图像分割线规则提示可能为拼图，仍需人工核对"]
    return "unknown", []


def discovery_context(metadata: dict[str, Any]) -> dict[str, Any]:
    source = metadata.get("source") or {}
    text = " ".join(str(v or "") for v in (metadata.get("title"), source.get("title"), source.get("page_url"), source.get("search_category"))).lower()
    # Conservative source filtering remains useful, but is not visual evidence.
    keywords = ("bts_", "prop_", "official_", "器材", "布光图", "灯位", "相机", "柔光", "道具", "假发", "商品", "cos服", "截图", "特效设计", "皮肤展示", "建模", "render", "插画", "立绘", "原画", "壁纸", "fanart", "fan art", "illustration", "人台", "假人", "平铺", "mannequin", "空镜", "scenery", "求助", "教程")
    return {"origin": "discovery_metadata", "title": metadata.get("title", ""),
            "source_title": source.get("title", ""), "page_url": source.get("page_url", ""),
            "search_query": source.get("search_query", ""),
            "filter_terms": [term for term in keywords if term in text], "photographic_fact": False}


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
        "is_single_person": None,
        "is_collage": is_collage,
        "is_equipment_or_scene": is_equipment,
        "is_blurry_or_lowres": is_lowres or is_blurry,
        "pose_readable": None,
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
    """Source conflicts can prompt review; neither text nor color proves identity."""
    source = metadata.get("source") or {}
    text = " ".join(str(v or "") for v in (metadata.get("title"), source.get("title"), source.get("page_url"), source.get("search_category"))).lower()
    context = context or {}
    aliases = [str(a).lower() for values in context.get("aliases", {}).values() for a in values]
    canonical = context.get("canonical_name", "")
    if canonical:
        aliases.append(canonical.lower())
    conflicts = [c.get("name", "") for c in context.get("common_confusions", [])
                 if c.get("name") and any(part.strip() and part.strip().lower() in text
                    for part in c["name"].replace("(", "|").replace(")", "|").split("|"))]
    conflict = bool(conflicts and not any(a and a in text for a in aliases))
    return {"prediction": "uncertain", "confidence": "low", "origin": "unverified_identity",
            "reason": "来源文字提示其他角色：" + "、".join(conflicts) + "；未从图像确认身份" if conflict else "当前本地规则没有角色视觉分类器，诚实保留 uncertain；未从图像确认身份",
            "source_conflict": conflict, "source_conflict_origin": "discovery_metadata",
            "transferable_candidate": False}


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
        content_type, visual_evidence = "unknown", []

    quality_res = evaluate_quality(image_bytes_or_path)
    identity_res = evaluate_identity(image_bytes_or_path, metadata, context)
    source_context = discovery_context(metadata)

    # Determine overall candidate status
    if content_type in FILTERED_MODALITIES:
        status = "filtered"
        status_reason = f"非真人摄影模态过滤: {content_type} ({'; '.join(visual_evidence)})"
    elif not quality_res["passed"]:
        status = "filtered"
        status_reason = f"基础质量预检未通过: {'; '.join(quality_res['filter_reasons'])}"
    elif source_context["filter_terms"] or identity_res["source_conflict"]:
        status = "filtered"
        status_reason = "来源文本筛选提示（不是图像事实）：" + (", ".join(source_context["filter_terms"]) or identity_res["reason"])
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
        "evidence_boundary_version": 2,
        "discovery_context": source_context,
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
    """Return the most recently inserted preflight, respecting project scope strictly.

    Preflight IDs contain random UUID fragments and are not chronological.  A
    project-scoped lookup must also never fall back to another project's result:
    the same immutable asset may be referenced by multiple projects with
    different identity contexts.
    """
    if project_id is not None:
        row = con.execute(
            "SELECT data FROM preflights WHERE asset_sha=? AND project_id=? ORDER BY rowid DESC LIMIT 1",
            (asset_sha, project_id),
        ).fetchone()
        return json.loads(row[0]) if row else None

    row = con.execute(
        "SELECT data FROM preflights WHERE asset_sha=? ORDER BY rowid DESC LIMIT 1",
        (asset_sha,),
    ).fetchone()
    return json.loads(row[0]) if row else None


def list_preflights(con: sqlite3.Connection, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
    if status:
        rows = con.execute(
            "SELECT data FROM preflights WHERE project_id=? AND status=? ORDER BY rowid DESC",
            (project_id, status),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT data FROM preflights WHERE project_id=? ORDER BY rowid DESC",
            (project_id,),
        ).fetchall()
    return [json.loads(r[0]) for r in rows]
