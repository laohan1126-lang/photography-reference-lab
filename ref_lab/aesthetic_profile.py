"""Versioned Aesthetic Profile, hypothesis generation, and auditable rollback.

AI analyzes and ranks; the owner decides.
- Profiles are independent of any single Character Project.
- Versioned (v1, v2, ...); history is never destroyed.
- Raw feedback (K/I/M/X) is append-only and auditable.
- Session summaries form grounded hypotheses that user can accept, edit, or decline.
- One unusual search batch cannot distort the profile.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from .db import encode, now

DEFAULT_DIMENSIONS = {
    "angles": {
        "low_angle": 0.6,
        "eye_level": 0.5,
        "high_angle": 0.4,
        "dramatic_tilt": 0.5,
    },
    "framing": {
        "full_body": 0.6,
        "medium_shot": 0.6,
        "close_up": 0.4,
    },
    "lighting": {
        "rim_light": 0.7,
        "high_contrast": 0.6,
        "diffuse_soft": 0.5,
        "natural_window": 0.5,
    },
    "composition": {
        "dynamic_diagonal": 0.7,
        "rule_of_thirds": 0.5,
        "clean_negative_space": 0.6,
    },
    "environment": {
        "studio_clean": 0.6,
        "textured_location": 0.6,
        "crowded_scene": 0.2,
    },
}


def build_default_profile() -> dict[str, Any]:
    return {
        "id": "current",
        "version": 1,
        "updated_at": now(),
        "dimensions": DEFAULT_DIMENSIONS,
        "positive_exemplars": [],
        "explicit_aesthetic_negatives": [],
        "accepted_hypotheses": [],
        "uncertainties": ["历史样本较少，极端广角、弱光高感及夜景场景仍待探索"],
        "provenance": {
            "source_session_ids": [],
            "total_feedback_count": 0,
            "parent_version": None,
        },
    }


def get_current_profile(con: sqlite3.Connection) -> dict[str, Any]:
    row = con.execute("SELECT data FROM aesthetic_profiles WHERE id='current'").fetchone()
    if row:
        return json.loads(row[0])
    # Fallback to creating initial profile
    profile = build_default_profile()
    save_profile(con, profile, action="profile.initialized")
    return profile


def save_profile(con: sqlite3.Connection, profile: dict[str, Any], action: str = "profile.updated") -> dict[str, Any]:
    profile["updated_at"] = now()
    # Save as current
    con.execute(
        "INSERT OR REPLACE INTO aesthetic_profiles VALUES(?,?,?,?)",
        ("current", profile["version"], profile["updated_at"], encode(profile)),
    )
    # Also save in versioned history
    con.execute(
        "INSERT INTO aesthetic_profile_history(version, at, action, data) VALUES(?,?,?,?)",
        (profile["version"], profile["updated_at"], action, encode(profile)),
    )
    return profile


def list_profile_history(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT version, at, action, data FROM aesthetic_profile_history ORDER BY version DESC, id DESC"
    ).fetchall()
    results = []
    seen_versions = set()
    for row in rows:
        v = row[0]
        if v not in seen_versions:
            seen_versions.add(v)
            data = json.loads(row[3])
            results.append({
                "version": v,
                "at": row[1],
                "action": row[2],
                "summary": f"Version {v} ({len(data.get('positive_exemplars', []))} 正样本, {len(data.get('accepted_hypotheses', []))} 确认假设)",
                "accepted_hypotheses": data.get("accepted_hypotheses", []),
            })
    return results


def rollback_profile(con: sqlite3.Connection, target_version: int) -> dict[str, Any]:
    row = con.execute(
        "SELECT data FROM aesthetic_profile_history WHERE version=? ORDER BY id DESC LIMIT 1",
        (target_version,),
    ).fetchone()
    if not row:
        raise ValueError(f"Target profile version {target_version} not found in history")
    restored = json.loads(row[0])
    current_row = con.execute("SELECT data FROM aesthetic_profiles WHERE id='current'").fetchone()
    current_version = json.loads(current_row[0])["version"] if current_row else 1
    new_version = current_version + 1

    restored["version"] = new_version
    restored["provenance"]["parent_version"] = current_version
    restored["provenance"]["rollback_from"] = target_version
    save_profile(con, restored, action=f"profile.rollback_to_v{target_version}")
    return restored


def derive_session_hypotheses(
    session_data: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive strictly grounded aesthetic hypotheses from this session's feedback.

    Never manufacture positive prose when evidence is absent.
    """
    hypotheses: list[dict[str, Any]] = []

    # Count signals
    i_items = [it for it in items if it.get("decision") == "keep" and it.get("lane") == "inspiration"]
    k_items = [it for it in items if it.get("decision") == "keep" and it.get("lane") != "inspiration"]
    x_items = [it for it in items if it.get("decision") == "reject"]

    # 1. Global Inspiration analysis (Strongest aesthetic signal)
    if i_items:
        tags = set()
        for item in i_items:
            for b in item.get("borrow", []):
                tags.add(b)
        tag_str = "、".join(tags) if tags else "综合光影动作"
        hypotheses.append({
            "id": f"hyp_{uuid4().hex[:8]}",
            "category": "inspiration_signal",
            "text": f"本轮共收藏 {len(i_items)} 张通用灵感（强正反馈），主要聚焦：{tag_str}",
            "evidence_count": len(i_items),
            "confidence": "high",
            "dimension": "lighting",
            "suggested_weight_delta": 0.15,
        })

    # 2. Project reference keep analysis
    if len(k_items) >= 2:
        hypotheses.append({
            "id": f"hyp_{uuid4().hex[:8]}",
            "category": "keep_reference",
            "text": f"保留了 {len(k_items)} 张本角色参考，对实拍可执行摆姿有较好接纳度",
            "evidence_count": len(k_items),
            "confidence": "medium",
            "dimension": "angles",
            "suggested_weight_delta": 0.08,
        })

    # 3. Reject analysis: distinguish aesthetic rejection from quality/identity rejection
    aesthetic_rejects = []
    quality_rejects = []
    for it in x_items:
        pf = it.get("preflight", {})
        if pf.get("status") == "filtered":
            quality_rejects.append(it)
        else:
            aesthetic_rejects.append(it)

    if aesthetic_rejects:
        hypotheses.append({
            "id": f"hyp_{uuid4().hex[:8]}",
            "category": "aesthetic_negative",
            "text": f"在及格候选中淘汰了 {len(aesthetic_rejects)} 张，表明对特定构图或现场表现有明确审美排除",
            "evidence_count": len(aesthetic_rejects),
            "confidence": "medium",
            "dimension": "environment",
            "suggested_weight_delta": -0.1,
        })

    if quality_rejects:
        hypotheses.append({
            "id": f"hyp_{uuid4().hex[:8]}",
            "category": "preflight_rejection",
            "text": f"淘汰了 {len(quality_rejects)} 张因预检存疑/杂乱的图（已作为质量/身份隔离，不污染审美偏好）",
            "evidence_count": len(quality_rejects),
            "confidence": "high",
            "dimension": "quality",
            "suggested_weight_delta": 0.0,
        })

    # 4. Uncertainty note if total actions are few
    if len(items) < 5:
        hypotheses.append({
            "id": f"hyp_{uuid4().hex[:8]}",
            "category": "uncertainty",
            "text": "本轮筛选样本量较少（不足5张），偏好调整幅度建议保守",
            "evidence_count": len(items),
            "confidence": "low",
            "dimension": "uncertainty",
            "suggested_weight_delta": 0.0,
        })

    return hypotheses


def update_profile_from_session(
    con: sqlite3.Connection,
    session_id: str,
    accepted_hypotheses: list[str],
    exemplar_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Incorporate confirmed hypotheses into a new version of the aesthetic profile."""
    current = get_current_profile(con)
    new_version = current["version"] + 1

    # Deep copy dimensions
    dims = json.loads(json.dumps(current.get("dimensions", DEFAULT_DIMENSIONS)))

    # Apply bounded adjustment (max delta 0.2) based on confirmed hypotheses
    for hyp in accepted_hypotheses:
        if "灵感" in hyp or "光影" in hyp or "轮廓光" in hyp:
            dims["lighting"]["rim_light"] = min(1.0, dims["lighting"].get("rim_light", 0.5) + 0.1)
            dims["composition"]["dynamic_diagonal"] = min(1.0, dims["composition"].get("dynamic_diagonal", 0.5) + 0.08)
        if "低机位" in hyp or "低角度" in hyp or "摆姿" in hyp:
            dims["angles"]["low_angle"] = min(1.0, dims["angles"].get("low_angle", 0.5) + 0.1)
            dims["framing"]["full_body"] = min(1.0, dims["framing"].get("full_body", 0.5) + 0.08)
        if "杂乱" in hyp or "排除" in hyp:
            dims["environment"]["crowded_scene"] = max(0.0, dims["environment"].get("crowded_scene", 0.3) - 0.1)
        if "影棚" in hyp or "背景" in hyp:
            dims["environment"]["studio_clean"] = min(1.0, dims["environment"].get("studio_clean", 0.5) + 0.1)

    # Collect exemplars
    positives = list(current.get("positive_exemplars", []))
    negatives = list(current.get("explicit_aesthetic_negatives", []))

    for it in exemplar_items:
        sha = it.get("asset_sha")
        if not sha:
            continue
        dec = it.get("decision")
        lane = it.get("lane")
        if dec == "keep":
            if not any(p["asset_sha"] == sha for p in positives):
                positives.append({
                    "asset_sha": sha,
                    "source_type": "inspiration" if lane == "inspiration" else "keep",
                    "preference": it.get("preference", ""),
                    "added_at": now(),
                })
        elif dec == "reject" and it.get("is_aesthetic_negative"):
            if not any(n["asset_sha"] == sha for n in negatives):
                negatives.append({
                    "asset_sha": sha,
                    "reason": it.get("reject_reason", "审美淘汰"),
                    "added_at": now(),
                })

    all_accepted = list(current.get("accepted_hypotheses", []))
    for h in accepted_hypotheses:
        all_accepted.append({"text": h, "session_id": session_id, "accepted_at": now()})

    source_sessions = list(current.get("provenance", {}).get("source_session_ids", []))
    if session_id not in source_sessions:
        source_sessions.append(session_id)

    new_profile = {
        "id": "current",
        "version": new_version,
        "updated_at": now(),
        "dimensions": dims,
        "positive_exemplars": positives[-50:],  # keep last 50 exemplars
        "explicit_aesthetic_negatives": negatives[-30:],  # keep last 30 negatives
        "accepted_hypotheses": all_accepted,
        "uncertainties": current.get("uncertainties", []),
        "provenance": {
            "source_session_ids": source_sessions,
            "total_feedback_count": current.get("provenance", {}).get("total_feedback_count", 0) + len(exemplar_items),
            "parent_version": current["version"],
        },
    }

    save_profile(con, new_profile, action=f"profile.updated_from_session_{session_id}")
    return new_profile
