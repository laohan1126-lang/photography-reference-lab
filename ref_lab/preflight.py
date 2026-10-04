"""Deterministic file checks and discovery context, never visual classification.

Identity, content and photographic usefulness require Agent or human review.
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

def detect_modality(image: Image.Image, metadata: dict[str, Any]) -> tuple[str, list[str]]:
    """No visual classifier runs here; metadata and geometry cannot establish modality."""
    return "unknown", []


def discovery_context(metadata: dict[str, Any]) -> dict[str, Any]:
    """Preserve explicit source doubts without presenting them as image facts."""
    source = metadata.get("source") or {}
    text = " ".join(str(value or "") for value in (
        metadata.get("title"), source.get("title"), source.get("search_category"),
    )).lower()
    terms = (
        "游戏截图", "游戏画面", "特效设计", "皮肤特效", "官方立绘", "同人画",
        "商品图", "商品展示", "服装展示", "人台展示", "假发出售", "道具出售",
        "布光图", "灯位图", "制作教程", "整理教程", "怎么整理", "如何整理",
    )
    return {
        "origin": "discovery_metadata",
        "photographic_fact": False,
        "title": metadata.get("title") or "",
        "source_title": source.get("title") or "",
        "search_query": source.get("search_query") or "",
        "filter_terms": [term for term in terms if term in text],
    }


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
    """Measure a possible divider-line hint; this does not establish collage content."""
    width, height = image.size
    if width < 300 or height < 300:
        return False
    gray = image.convert("L")
    # Check potential split lines: 33%, 50%, 66%
    for ratio in (0.333, 0.5, 0.667):
        y = int(height * ratio)
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
    """Validate decodability/dimensions and expose measurements for later review."""
    unknown = {
        "is_single_person": None, "is_collage": None,
        "is_equipment_or_scene": None, "is_blurry_or_lowres": None,
        "pose_readable": None,
    }
    try:
        stream = io.BytesIO(image_path) if isinstance(image_path, bytes) else image_path
        with Image.open(stream) as image:
            image.load()
            width, height = image.size
            dhash = compute_dhash(image)
            divider_hint = detect_collage(image)
            sharpness = measure_sharpness(image)
    except Exception as exc:
        return {
            **unknown, "passed": False,
            "filter_reasons": [f"无法读取图片格式: {exc}"], "dhash": "",
        }

    filter_reasons = []
    is_lowres = width < 200 or height < 200
    if is_lowres:
        filter_reasons.append("分辨率过低（尺寸小于 200px）")
    ratio = width / max(1, height)
    if ratio > 4.5 or ratio < 0.22:
        filter_reasons.append("长宽比超出参考库文件尺寸范围")
    return {
        **unknown,
        "passed": not filter_reasons,
        "filter_reasons": filter_reasons,
        "is_blurry_or_lowres": True if is_lowres else None,
        "divider_hint": divider_hint,
        "sharpness": round(sharpness, 2),
        "dhash": dhash, "width": width, "height": height,
    }


def evaluate_identity(
    image_path: Path | bytes,
    metadata: dict[str, Any],
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Keep source conflicts as discovery doubts; pixels are not classified here."""
    canonical = (context or {}).get("canonical_name", "")
    source = metadata.get("source") or {}
    text = " ".join(str(value or "") for value in (
        metadata.get("title"), source.get("title"), source.get("search_category"),
    )).lower()
    aliases = [str(alias).lower() for values in (context or {}).get("aliases", {}).values() for alias in values]
    if canonical:
        aliases.append(canonical.lower())
    conflicts = [
        item.get("name") for item in (context or {}).get("common_confusions", [])
        if item.get("name") and item["name"].lower() in text
    ]
    source_conflict = bool(conflicts) and not any(alias and alias in text for alias in aliases)
    reason = "当前确定性预检没有视觉身份分类器，metadata 不能代替图像核验；诚实保留为不确定"
    if source_conflict:
        reason += "；来源文本提及其他角色：" + "、".join(conflicts)
    return {
        "prediction": "uncertain", "confidence": "low", "reason": reason,
        "source_conflict": source_conflict,
        "transferable_candidate": False,
    }


def run_candidate_preflight(
    image_bytes_or_path: Path | bytes,
    metadata: dict[str, Any],
    context: dict[str, Any] | None,
    asset_sha: str,
    project_id: str,
    reference_id: str | None = None,
) -> dict[str, Any]:
    """Run deterministic file checks; leave all visual conclusions for actual review."""
    quality_res = evaluate_quality(image_bytes_or_path)
    identity_res = evaluate_identity(image_bytes_or_path, metadata, context)
    status = "uncertain" if quality_res["passed"] else "filtered"
    status_reason = (
        "文件尺寸预检通过；角色、模态、人数与动作可读性待 Agent 或人工看图核验"
        if quality_res["passed"]
        else "基础文件预检未通过: " + "; ".join(quality_res["filter_reasons"])
    )
    return {
        "id": f"pf_{uuid4().hex[:12]}",
        "asset_sha": asset_sha, "project_id": project_id, "reference_id": reference_id,
        "content_type": "unknown",
        "identity_prediction": "uncertain", "confidence": "low", "visual_evidence": [],
        "reason": status_reason, "status_reason": status_reason,
        "producer": "deterministic_preflight", "evidence_boundary_version": 2,
        "status": status, "quality": quality_res, "identity": identity_res,
        "discovery_context": discovery_context(metadata),
        "dhash": quality_res.get("dhash", ""), "created_at": now(),
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
