"""Thin, durable candidate queue shared by Search and Review.

Search writes originals and ``received.json`` as soon as a download succeeds.
Review writes per-image verdicts to ``review-audit.json``. A human decision lives
in ``human-decisions.json`` and is never rewritten by the review worker.

This module deliberately contains no model calls, no browser code and no
imports into the personal library. It only projects the private run artifacts
into a pollable candidate view.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from pathlib import Path

from .storage import atomic_write

ROOT = Path(__file__).resolve().parents[1]
_JOB_ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")

_LOCK = threading.RLock()
_DECISION_LOCK = threading.RLock()


def run_root() -> Path:
    return ROOT / ".local" / "collection-runs"


def run_directory(job_id: str) -> Path:
    if not _JOB_ID.fullmatch(str(job_id or "")):
        raise ValueError("Invalid collection job identity")
    return run_root() / str(job_id) / "current"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text("utf8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, default=str).encode("utf8"))


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA.fullmatch(value))


def _received_rows(folder: Path) -> list[dict]:
    rows = read_json(folder / "received.json", None)
    if rows is None:
        state = read_json(folder / "collector-state.json", {})
        rows = state.get("received", []) if isinstance(state, dict) else []
    if not isinstance(rows, list):
        return []
    output = []
    images = (folder / "images").resolve()
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not _valid_sha(row.get("asset_sha")):
            continue
        if row["asset_sha"] in seen:
            continue
        try:
            path = Path(str(row.get("original_path", "")))
            resolved = path.resolve()
            if path.is_symlink() or not resolved.is_relative_to(images) or not resolved.is_file():
                continue
        except (OSError, RuntimeError, ValueError):
            continue
        seen.add(row["asset_sha"])
        output.append({
            **row,
            "original_path": str(resolved),
            "original_filename": resolved.name,
        })
    return output


def _review_items(folder: Path) -> dict[str, dict]:
    data = read_json(folder / "review-audit.json", {})
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, dict):
        return {}
    return {sha: value for sha, value in items.items()
            if _valid_sha(sha) and isinstance(value, dict)}


def _human_items(folder: Path) -> dict[str, dict]:
    data = read_json(folder / "human-decisions.json", {})
    items = data.get("items") if isinstance(data, dict) else None
    return items if isinstance(items, dict) else {}


def _search_summary(folder: Path) -> dict:
    summary = read_json(folder / "search-summary.json", {})
    if isinstance(summary, dict) and summary:
        return summary
    state = read_json(folder / "collector-state.json", {})
    if isinstance(state, dict) and state:
        return {
            "status": "completed" if state.get("search_complete") else "running",
            "stop_reason": state.get("search_stop_reason", ""),
            "found": len(state.get("received", [])),
            "phase": state.get("phase", ""),
        }
    return {}


def _review_summary(folder: Path) -> dict:
    summary = read_json(folder / "review-summary.json", {})
    if isinstance(summary, dict) and summary:
        return summary
    return {}


def _status(row: dict, review: dict | None, human: dict | None) -> str:
    decision = str((human or {}).get("decision", ""))
    if decision == "keep":
        return "human_keep"
    if decision == "reject":
        return "human_reject"
    if review:
        state = str(review.get("status", ""))
        if state == "accepted":
            return "accepted"
        if state == "rejected":
            return "rejected"
        if state == "duplicate":
            return "rejected"
        if state == "blocked":
            return "blocked"
        if state == "reviewing":
            return "reviewing"
    return "pending"


def _item(row: dict, review: dict | None, human: dict | None, job_id: str) -> dict:
    status = _status(row, review, human)
    value = review.get("review") if isinstance((review or {}).get("review"), dict) else None
    comparisons = value.get("reference_comparisons", []) if value else []
    source = {
        "page_url": str(row.get("page_url", "")),
        "image_url": str(row.get("image_url", "")),
        "search_query": str(row.get("search_query", "")),
        "author": str(row.get("author", "")),
        "source_text": str(row.get("source_text", ""))[:2000],
    }
    return {
        "asset_sha": row["asset_sha"],
        "status": status,
        "original_filename": row.get("original_filename", ""),
        "width": row.get("width"),
        "height": row.get("height"),
        "acquired_at": row.get("acquired_at"),
        "source": source,
        "discovery_url": str(row.get("discovery_url", "")),
        "review": None if value is None else {
            "decision": review.get("decision", ""),
            "accepted": bool(review.get("accepted")),
            "identity": value.get("identity"),
            "costume": value.get("costume"),
            "confidence": value.get("confidence"),
            "kind": value.get("kind"),
            "reason": value.get("reason", ""),
            "reference_count": len(comparisons),
        },
        "review_error": str((review or {}).get("error", ""))[:800],
        "human_decision": str((human or {}).get("decision", "")),
        "human_decided_at": (human or {}).get("at"),
        "relevance": row.get("relevance") if isinstance(row.get("relevance"), dict) else {
            "tier": "unconfirmed", "label": "角色相关性未确认",
            "reason": "该候选没有保存文字相关性记录。",
        },
        "original_url": f"/api/jobs/{job_id}/candidates/{row['asset_sha']}/original",
    }


def counts(items: list[dict]) -> dict:
    result = {
        "found": len(items),
        "accepted": 0,
        "human_keep": 0,
        "passed": 0,
        "rejected": 0,
        "human_reject": 0,
        "blocked": 0,
        "pending": 0,
        "reviewing": 0,
        "target_confirmed": 0,
        "exploration": 0,
        "other_character": 0,
        "non_photo": 0,
    }
    for item in items:
        status = item.get("status")
        tier = str((item.get("relevance") or {}).get("tier") or "unconfirmed")
        if tier == "target_named":
            result["target_confirmed"] += 1
        elif tier in {"target_context", "unconfirmed"}:
            result["exploration"] += 1
        elif tier in {"other_character", "non_photo"}:
            result[tier] += 1
        if status == "accepted":
            result["accepted"] += 1
        elif status == "human_keep":
            result["human_keep"] += 1
        elif status == "rejected":
            result["rejected"] += 1
        elif status == "human_reject":
            result["human_reject"] += 1
        elif status == "blocked":
            result["blocked"] += 1
        elif status == "reviewing":
            result["reviewing"] += 1
        else:
            result["pending"] += 1
    result["passed"] = result["accepted"] + result["human_keep"]
    result["rejected_total"] = result["rejected"] + result["human_reject"]
    return result


def snapshot(job_id: str, *, offset: int = 0, limit: int = 200) -> dict:
    """Return a complete count plus a bounded item page.

    The project is rebuilt from atomic local files, so a fresh server process or
    a reopened browser sees the same candidates after a restart.
    """
    folder = run_directory(job_id)
    with _LOCK:
        rows = _received_rows(folder)
        reviews = _review_items(folder)
        humans = _human_items(folder)
    items = [_item(row, reviews.get(row["asset_sha"]), humans.get(row["asset_sha"]), job_id) for row in rows]
    overall = counts(items)
    offset = max(0, int(offset))
    limit = min(500, max(1, int(limit)))
    return {
        "version": 1,
        "job_id": job_id,
        "run_directory": str(folder),
        "search": _search_summary(folder),
        "review": _review_summary(folder),
        "progress": read_json(folder / "review-state.json", {}),
        "counts": overall,
        "offset": offset,
        "limit": limit,
        "items": items[offset:offset + limit],
    }


def decide(job_id: str, sha: str, decision: str) -> dict:
    if decision not in {"keep", "reject", "clear"}:
        raise ValueError("Human decision must be keep, reject or clear")
    if not _valid_sha(sha):
        raise ValueError("Invalid image SHA")
    folder = run_directory(job_id)
    rows = {row["asset_sha"]: row for row in _received_rows(folder)}
    if sha not in rows:
        raise ValueError("This image is not in the acquired candidate queue")
    with _DECISION_LOCK:
        path = folder / "human-decisions.json"
        data = read_json(path, {})
        items = data.get("items") if isinstance(data, dict) and isinstance(data.get("items"), dict) else {}
        if decision == "clear":
            items.pop(sha, None)
        else:
            items[sha] = {
                "decision": decision,
                "at": __import__("time").time(),
                "asset_sha": sha,
                "actor": "human",
            }
        write_json(path, {"version": 1, "items": items})
    return snapshot(job_id)


def original_bytes(job_id: str, sha: str) -> tuple[Path, bytes]:
    if not _valid_sha(sha):
        raise ValueError("Invalid image SHA")
    folder = run_directory(job_id)
    for row in _received_rows(folder):
        if row["asset_sha"] != sha:
            continue
        path = Path(row["original_path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Original image bytes changed")
        return path, raw
    raise ValueError("This image is not in the acquired candidate queue")


def search_terminal(summary: dict) -> bool:
    return str(summary.get("status", "")) in {"completed", "blocked", "failed", "cancelled"}


def human_decision(folder: Path, sha: str) -> dict | None:
    return _human_items(folder).get(sha)


def human_items(folder: Path) -> dict[str, dict]:
    return _human_items(folder)


def decide_path(folder: Path) -> Path:
    return folder / "human-decisions.json"
