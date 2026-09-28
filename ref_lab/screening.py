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
    preference: str = "",
    borrow: list[str] | None = None,
    is_aesthetic_negative: bool = False,
    reject_reason: str = "",
    preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = con.execute("SELECT data FROM screening_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise ValueError(f"Screening session {session_id} not found")
    data = json.loads(row[0])

    # Record action
    action_record = {
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

    data["finished_at"] = now()
    data["status"] = "reviewing_summary"

    # Derive hypotheses from this session's actions
    hypotheses = derive_session_hypotheses(data, data.get("actions", []))
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
        "exemplar_candidates_count": len([a for a in data.get("actions", []) if a.get("decision") == "keep"]),
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

    data["accepted_hypotheses"] = accepted_hypotheses
    data["apply_to_profile"] = apply_to_profile

    new_profile = None
    if apply_to_profile and accepted_hypotheses:
        new_profile = update_profile_from_session(
            con,
            session_id=session_id,
            accepted_hypotheses=accepted_hypotheses,
            exemplar_items=data.get("actions", []),
        )
        data["status"] = "completed_learned"
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
