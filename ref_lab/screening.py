"""Screening Sessions: natural human curation sessions and grounded summaries.

Sessions decouple individual clicks (K/I/M/X) from continuous profile rewriting.
Finishing a session forms hypotheses that the user can accept, edit, or decline.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from .aesthetic_profile import derive_session_hypotheses, get_current_profile, update_profile_from_session
from .db import encode, now


def get_or_create_active_session(
    con: sqlite3.Connection,
    project_id: str,
    profile_version: int | None = None,
) -> dict[str, Any]:
    row = con.execute(
        "SELECT data FROM screening_sessions WHERE project_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if row:
        return json.loads(row[0])

    if profile_version is None:
        profile = get_current_profile(con)
        profile_version = profile["version"]

    ident = f"sess_{uuid4().hex[:12]}"
    session_data = {
        "id": ident,
        "project_id": project_id,
        "status": "active",
        "started_at": now(),
        "finished_at": None,
        "profile_version": profile_version,
        "actions": [],
        "stats": {"viewed": 0, "keep": 0, "inspiration": 0, "maybe": 0, "reject": 0},
    }
    con.execute(
        "INSERT INTO screening_sessions VALUES(?,?,?,?,?,?)",
        (ident, project_id, "active", session_data["started_at"], None, encode(session_data)),
    )
    return session_data


def record_session_action(
    con: sqlite3.Connection,
    session_id: str,
    reference_id: str,
    asset_sha: str,
    decision: str,
    lane: str = "field",
    preference: str | None = None,
    borrow: list[str] | None = None,
    is_aesthetic_negative: bool = False,
    reject_reason: str = "",
    preflight: dict[str, Any] | None = None,
    reference_revision: int | None = None,
    project_context: dict[str, Any] | None = None,
    decision_origin: str = "unknown",
    inspiration_context: dict[str, Any] | None = None,
    reference_fingerprint: str | None = None,
) -> dict[str, Any]:
    row = con.execute("SELECT data FROM screening_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise ValueError(f"Screening session {session_id} not found")
    data = json.loads(row[0])

    if data["status"] != "active":
        raise ValueError("Screening session is no longer active")
    previous = next((a for a in reversed(data["actions"]) if a.get("reference_id") == reference_id
                     and a.get("asset_sha") == asset_sha and a.get("origin") == "human_curation"), {})
    # Carry forward only explicit human notes from this session, never legacy annotations.
    if preference is None:
        preference = previous.get("preference", "")
    if borrow is None:
        borrow = previous.get("borrow", [])
    # Record action
    action_record = {
        "origin": "human_curation",
        "decision_origin": decision_origin,
        "inspiration_context": inspiration_context,
        "reference_fingerprint": reference_fingerprint,
        "reference_revision": reference_revision, "project_context": project_context,
        "reference_id": reference_id,
        "asset_sha": asset_sha,
        "decision": decision,
        "lane": lane,
        "preference": preference,
        "borrow": borrow or [],
        "is_aesthetic_negative": is_aesthetic_negative,
        "reject_reason": reject_reason,
        "preflight": preflight or {},
        "at": now(),
    }
    data["actions"].append(action_record)

    # Update stats
    stats = data["stats"]
    stats["viewed"] = len(data["actions"])
    if decision == "keep":
        if lane == "inspiration":
            stats["inspiration"] += 1
        else:
            stats["keep"] += 1
    elif decision == "maybe":
        stats["maybe"] += 1
    elif decision == "reject":
        stats["reject"] += 1

    con.execute("UPDATE screening_sessions SET data=? WHERE id=?", (encode(data), session_id))
    return data


def finish_screening_session(con: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    row = con.execute("SELECT data FROM screening_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise ValueError(f"Screening session {session_id} not found")
    data = json.loads(row[0])

    if data["status"] not in {"active", "reviewing_summary"}:
        raise ValueError("Completed session cannot be finished again")
    # Raw image-specific history survives replacement; only the final choice of
    # a reference can become its current summary sample.
    items = list({a.get("reference_id"): a for a in data.get("actions", [])}.values())
    stats = {"viewed": len(items), "keep": 0, "inspiration": 0, "maybe": 0, "reject": 0}
    for item in items:
        if item.get("decision_origin") not in {"human_curation", "human_inspiration_archive"}:
            continue
        key = "inspiration" if item["decision"] == "keep" and item.get("lane") == "inspiration" else item["decision"]
        if key in stats:
            stats[key] += 1
    data["stats"] = stats
    data["finished_at"] = data.get("finished_at") or now()
    data["status"] = "reviewing_summary"

    # Derive hypotheses from this session's actions
    hypotheses = derive_session_hypotheses(data, items) if data.get("evidence_boundary_version") != 2 else data["derived_hypotheses"]
    data["evidence_boundary_version"] = 2
    data["derived_hypotheses"] = hypotheses

    con.execute(
        "UPDATE screening_sessions SET status='reviewing_summary', finished_at=?, data=? WHERE id=?",
        (data["finished_at"], encode(data), session_id),
    )

    profile = get_current_profile(con)

    summary = {
        "session_id": session_id,
        "project_id": data["project_id"],
        "started_at": data["started_at"],
        "finished_at": data["finished_at"],
        "stats": data["stats"],
        "hypotheses": hypotheses,
        "current_profile_version": profile["version"],
        "exemplar_candidates_count": len([a for a in items if a.get("decision") == "keep"]),
    }
    return summary


def confirm_session_summary(
    con: sqlite3.Connection,
    session_id: str,
    accepted_hypotheses: list[str],
    apply_to_profile: bool = True,
) -> dict[str, Any]:
    row = con.execute("SELECT data FROM screening_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise ValueError(f"Screening session {session_id} not found")
    data = json.loads(row[0])

    if data["status"].startswith("completed_"):
        if data.get("accepted_hypotheses") != accepted_hypotheses or data.get("apply_to_profile") != apply_to_profile:
            raise ValueError("Completed summary cannot be overwritten")
        return {"session_id": session_id, "status": data["status"], "accepted_hypotheses": accepted_hypotheses,
                "apply_to_profile": apply_to_profile, "profile_version": data["result_profile_version"],
                "profile": None, "idempotent": True}
    if data["status"] != "reviewing_summary":
        raise ValueError("Finish the session before confirming")
    if data.get("evidence_boundary_version") != 2:
        raise ValueError("Historical summary must be reviewed again before confirmation")
    allowed = {h["text"] for h in data.get("derived_hypotheses", [])}
    if len(accepted_hypotheses) != len(set(accepted_hypotheses)) or not set(accepted_hypotheses) <= allowed:
        raise ValueError("Only this session's displayed summaries can be confirmed")
    items = list({a.get("reference_id"): a for a in data.get("actions", [])}.values())
    # The writer transaction closes the check-to-save race. A finished summary
    # is a snapshot, not authorization to replay withdrawn or replaced choices.
    from .service import Problem
    for item in items:
        if apply_to_profile and accepted_hypotheses and not feedback_is_current(con, item):
            raise Problem(409, "筛选总结已过期：图片、选择、收藏或项目已改变，请重新筛选并总结")
    data["accepted_hypotheses"] = accepted_hypotheses
    data["apply_to_profile"] = apply_to_profile

    selected_categories = {h["category"] for h in data["derived_hypotheses"] if h["text"] in accepted_hypotheses}
    def selected_item(item):
        if item.get("decision") == "keep":
            category = "inspiration_signal" if item.get("lane") == "inspiration" else "keep_reference"
        else:
            category = "aesthetic_negative" if item.get("decision") == "reject" and item.get("is_aesthetic_negative") else None
        return item.get("origin") == "human_curation" and item.get("decision_origin") in {"human_curation", "human_inspiration_archive"} and category in selected_categories
    new_profile = None
    if apply_to_profile and accepted_hypotheses:
        new_profile = update_profile_from_session(
            con,
            session_id=session_id,
            accepted_hypotheses=accepted_hypotheses,
            exemplar_items=[i for i in items if selected_item(i)],
        )
        data["status"] = "completed_feedback_saved"
        data["result_profile_version"] = new_profile["version"]
    else:
        data["status"] = "completed_skipped_learning"
        profile = get_current_profile(con)
        data["result_profile_version"] = profile["version"]

    con.execute("UPDATE screening_sessions SET status=?, data=? WHERE id=?", (data["status"], encode(data), session_id))
    return {
        "session_id": session_id,
        "status": data["status"],
        "accepted_hypotheses": accepted_hypotheses,
        "apply_to_profile": apply_to_profile,
        "profile_version": data["result_profile_version"],
        "profile": new_profile,
    }


def list_sessions(con: sqlite3.Connection, project_id: str) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT data FROM screening_sessions WHERE project_id=? ORDER BY started_at DESC",
        (project_id,),
    ).fetchall()
    return [json.loads(r[0]) for r in rows]


def feedback_is_current(con: sqlite3.Connection, item: dict) -> bool:
    """Historical feedback survives; only matching owner state is reusable now."""
    row = con.execute("SELECT data FROM refs WHERE id=?", (item.get("reference_id"),)).fetchone()
    if not row:
        return False
    ref = json.loads(row[0])
    from .policy import digest, context_digest
    if ref.get("asset_sha") != item.get("asset_sha") or ref["revision"] != item.get("reference_revision"):
        return False
    if digest(ref) != item.get("reference_fingerprint"):
        return False  # Raw maintenance scripts can change state without revision.
    asset = con.execute("SELECT data FROM assets WHERE id=?", (item.get("asset_sha"),)).fetchone()
    if not asset:
        return False
    asset = json.loads(asset[0])
    if asset.get("storage_status") in {"purged", "purge_failed"} or asset.get("integrity") == "failed":
        return False
    project = con.execute("SELECT data FROM projects WHERE id=?", (ref["project_id"],)).fetchone()
    if not project:
        return False
    project = json.loads(project[0])
    context = item.get("project_context") or {}
    if project.get("archived_at") or project.get("revision") != context.get("revision") or context_digest(project) != context_digest(context):
        return False
    inspiration = item.get("inspiration_context")
    if inspiration:
        row = con.execute("SELECT data FROM inspirations WHERE id=? AND active=1", (inspiration.get("id"),)).fetchone()
        if not row or json.loads(row[0])["revision"] != inspiration.get("revision"):
            return False
    return True
