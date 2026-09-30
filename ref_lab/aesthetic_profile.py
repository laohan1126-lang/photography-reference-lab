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
    items = [i for i in items if i.get("origin") == "human_curation"]
    hypotheses = []
    groups = [("inspiration_signal", [i for i in items if i.get("decision") == "keep" and i.get("lane") == "inspiration"], "你收藏了通用灵感；这不自动表明喜欢某种光线或机位"),
              ("keep_reference", [i for i in items if i.get("decision") == "keep" and i.get("lane") != "inspiration"], "你保留了项目参考；项目用途不等于长期审美偏好"),
              ("aesthetic_negative", [i for i in items if i.get("decision") == "reject" and i.get("is_aesthetic_negative") is True], "你明确标记了审美不喜欢；保留理由与图片供以后复核")]
    for category, cases, text in groups:
        if cases:
            hypotheses.append({"id": f"hyp_{uuid4().hex[:8]}", "category": category,
                               "text": text, "evidence_count": len(cases), "confidence": "high",
                               "rationale": "仅汇总人工选择，不推导摄影属性或自动调整权重",
                               "evidence": [{k: i.get(k) for k in ("reference_id", "asset_sha", "preference", "borrow", "reject_reason")} for i in cases],
                               "suggested_weight_delta": 0.0})
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

    # Confirmed text is retained verbatim. Keywords cannot justify numeric weights.
    # Collect exemplars
    positives = list(current.get("positive_exemplars", []))
    negatives = list(current.get("explicit_aesthetic_negatives", []))
    project_uses = list(current.get("project_use_exemplars", []))

    for it in exemplar_items:
        sha = it.get("asset_sha")
        if not sha:
            continue
        dec = it.get("decision")
        lane = it.get("lane")
        if dec == "keep" and lane != "inspiration":
            project_uses.append({"asset_sha": sha, "session_id": session_id,
                                 "reference_id": it.get("reference_id"), "project_context": it.get("project_context"),
                                 "preference": it.get("preference", ""), "origin": "human_project_use"})
        elif dec == "keep" and lane == "inspiration":
            if not any(p["asset_sha"] == sha for p in positives):
                positives.append({
                    "asset_sha": sha,
                    "source_type": "inspiration" if lane == "inspiration" else "keep",
                    "preference": it.get("preference", ""),
                    "session_id": session_id, "origin": "human_curation", "added_at": now(),
                })
        elif dec == "reject" and it.get("is_aesthetic_negative"):
            if not any(n["asset_sha"] == sha for n in negatives):
                negatives.append({
                    "asset_sha": sha,
                    "reason": it.get("reject_reason", "审美淘汰"),
                    "session_id": session_id, "origin": "human_curation", "added_at": now(),
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
        "project_use_exemplars": project_uses,
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
