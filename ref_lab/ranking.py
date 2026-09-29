"""Multi-factor explainable ranking and aesthetic exploration.

No single opaque 'Aesthetic Score 92'.
Evaluates 4 independent, observable dimensions:
1. character / task relevance
2. photographic usefulness
3. personal preference match
4. novelty / exploration
"""
from __future__ import annotations

from typing import Any
from .preflight import hamming_distance


def evaluate_photographic_points(quality_data: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    points = []
    w = quality_data.get("width", 0)
    h = quality_data.get("height", 0)
    sharpness = quality_data.get("sharpness", 0.0)
    text = (metadata.get("title", "") + " " + metadata.get("source", {}).get("search_query", "")).lower()

    if h > w * 1.2:
        points.append("竖构图/全身人像")
    elif w > h * 1.2:
        points.append("横构图/环境人像")
    else:
        points.append("方画幅构图")

    if sharpness > 40.0:
        points.append("主体焦点清晰")

    # Photographic cues from text or observation
    if any(k in text for k in ("逆光", "轮廓光", "背光", "rim", "backlight")):
        points.append("轮廓光分离")
    elif any(k in text for k in ("柔光", "窗边", "自然光", "soft")):
        points.append("柔和自然光")
    elif any(k in text for k in ("侧光", "硬光", "戏剧光", "contrast")):
        points.append("高对比侧光")

    if any(k in text for k in ("低机位", "仰拍", "仰视", "low")):
        points.append("低机位透视")
    elif any(k in text for k in ("俯拍", "俯视", "high")):
        points.append("俯拍构图")
    else:
        points.append("平视自然视角")

    if any(k in text for k in ("动态", "走动", "起跳", "甩发", "action", "dynamic")):
        points.append("动态摆姿线条")
    else:
        points.append("静态稳定姿势")

    return points


def score_and_rank_candidates(
    candidates: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Score candidates along 4 dimensions and rank with exploration slots."""
    if not candidates:
        return []

    profile_dims = (profile or {}).get("dimensions", {})
    lighting_pref = profile_dims.get("lighting", {}).get("rim_light", 0.6)
    angle_pref = profile_dims.get("angles", {}).get("low_angle", 0.6)

    scored_items = []
    seen_dhashes: list[str] = []

    for index, cand in enumerate(candidates):
        preflight = cand.get("preflight") or {}
        quality = preflight.get("quality") or {}
        identity = preflight.get("identity") or {}
        dhash = preflight.get("dhash") or cand.get("dhash") or ""

        # 1. Relevance Score
        pred = identity.get("prediction", "uncertain")
        if pred == "match":
            relevance = 1.0
            id_status = "高可信匹配"
        elif pred == "uncertain":
            relevance = 0.65
            id_status = "身份存疑待核查"
        elif identity.get("transferable_candidate"):
            relevance = 0.45
            id_status = "可迁移动作参考"
        else:
            relevance = 0.1
            id_status = "角色不匹配"

        # 2. Photographic Usefulness Score
        sharpness = quality.get("sharpness", 25.0)
        usefulness = min(1.0, 0.4 + (sharpness / 100.0) * 0.4)
        if quality.get("passed"):
            usefulness += 0.2
        usefulness = min(1.0, max(0.1, usefulness))

        # 3. Preference Match Score
        photo_points = evaluate_photographic_points(quality, cand)
        preference_points = []
        pref_score = 0.5

        if "轮廓光分离" in photo_points:
            pref_score += (lighting_pref - 0.5) * 0.4
            preference_points.append("符合偏好：轮廓光/光影分离")
        if "低机位透视" in photo_points or "动态摆姿线条" in photo_points:
            pref_score += (angle_pref - 0.5) * 0.4
            preference_points.append("符合偏好：低机位/动态张力姿势")
        pref_score = min(1.0, max(0.1, pref_score))

        # 4. Exploration / Novelty Score
        # Novelty is higher when an item has features that differ from the top profile preference
        is_novel_angle = "俯拍构图" in photo_points or "方画幅构图" in photo_points
        is_novel_lighting = "柔和自然光" in photo_points
        is_exploration = is_novel_angle or is_novel_lighting
        exploration_score = 0.8 if is_exploration else 0.3
        exploration_reason = "探索项：非日常高频视角/柔和光影样本" if is_exploration else ""

        # Near-duplicate demotion
        is_near_dup = False
        if dhash:
            for prev_h in seen_dhashes:
                if hamming_distance(dhash, prev_h) <= 5:
                    is_near_dup = True
                    break
            seen_dhashes.append(dhash)

        # Composite Ranking calculation (Never a single obscure aesthetic number)
        composite = (
            relevance * 0.35 +
            usefulness * 0.35 +
            pref_score * 0.20 +
            exploration_score * 0.10
        )
        if is_near_dup:
            composite -= 0.3  # Demote near-duplicate burst shots

        # Human-readable recommendation reason
        if pred == "match":
            rec_reason = f"角色高度契合 · {photo_points[0]} · {photo_points[-1]}"
        elif identity.get("transferable_candidate"):
            rec_reason = f"非目标角色但动作具备借鉴价值（{photo_points[0]}）"
        else:
            rec_reason = f"候选参考 · {photo_points[0]}"

        explanation = {
            "identity_status": id_status,
            "recommendation_reason": rec_reason,
            "photographic_points": photo_points,
            "preference_points": preference_points,
            "is_exploration": is_exploration,
            "exploration_reason": exploration_reason,
            "is_near_duplicate": is_near_dup,
            "total_score": round(composite, 2),
            "relevance_score": round(relevance, 2),
            "usefulness_score": round(usefulness, 2),
            "preference_score": round(pref_score, 2),
            "exploration_score": round(exploration_score, 2),
            "scores": {
                "relevance": round(relevance, 2),
                "usefulness": round(usefulness, 2),
                "preference": round(pref_score, 2),
                "exploration": round(exploration_score, 2),
                "composite": round(composite, 2),
            },
        }

        cand_copy = dict(cand)
        cand_copy["ranking_explanation"] = explanation
        cand_copy["recommendation"] = explanation
        cand_copy["ranking_score"] = round(composite, 3)
        scored_items.append(cand_copy)

    # Sort primarily by composite score
    scored_items.sort(key=lambda x: x["ranking_score"], reverse=True)

    # Interleave exploration: ensure at least 15-20% high-exploration items in top view
    final_ranked = []
    normal_pool = [x for x in scored_items if not x["ranking_explanation"]["is_exploration"]]
    explor_pool = [x for x in scored_items if x["ranking_explanation"]["is_exploration"]]

    norm_idx, exp_idx = 0, 0
    count = 0
    while norm_idx < len(normal_pool) or exp_idx < len(explor_pool):
        count += 1
        # Every 4th item, take from exploration pool if available
        if count % 4 == 0 and exp_idx < len(explor_pool):
            final_ranked.append(explor_pool[exp_idx])
            exp_idx += 1
        elif norm_idx < len(normal_pool):
            final_ranked.append(normal_pool[norm_idx])
            norm_idx += 1
        elif exp_idx < len(explor_pool):
            final_ranked.append(explor_pool[exp_idx])
            exp_idx += 1

    return final_ranked
