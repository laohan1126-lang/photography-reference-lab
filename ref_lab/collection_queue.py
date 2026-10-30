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


def _derived_records(folder: Path) -> dict[str, dict]:
    """Read the local collage records without trusting their paths."""
    data = read_json(folder / "derived.json", {})
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, dict):
        return {}
    return {sha: value for sha, value in items.items()
            if _valid_sha(sha) and isinstance(value, dict)}


def _derived_rows(folder: Path, parents: dict[str, dict]) -> dict[str, list[dict]]:
    """Usable derived tiles per parent SHA.

    Only ``valid`` children written by the current algorithm become candidate
    cards. Records from another version are reported as pending update, damaged
    or unbound tiles are excluded (and stay on disk), and a tile SHA is shown at
    most once even if two records claim it.
    """
    from . import collage
    from .integrity import sha_matches
    output: dict[str, list[dict]] = {}
    derived_dir = (folder / "derived").resolve()
    seen_children: set[str] = set()
    for parent_sha, record in _derived_records(folder).items():
        parent = parents.get(parent_sha)
        if parent is None:
            continue
        if not collage.record_is_current(record):
            continue
        children = [child for child in (record.get("children") or []) if isinstance(child, dict)]
        total = len(children)
        for index, child in enumerate(children, 1):
            if child.get("status") != collage.VALID:
                continue
            sha = child.get("child_sha")
            if not _valid_sha(sha) or sha == parent_sha or sha in seen_children:
                continue
            if str(child.get("parent_sha") or "") != parent_sha:
                continue
            try:
                path = Path(str(child.get("path") or ""))
                resolved = path.resolve()
                if path.is_symlink() or not resolved.is_relative_to(derived_dir):
                    continue
            except (OSError, RuntimeError, ValueError):
                continue
            if not sha_matches(resolved, sha):
                continue
            seen_children.add(sha)
            size = child.get("size") or [None, None]
            output.setdefault(parent_sha, []).append({
                **{key: parent.get(key) for key in
                   ("page_url", "image_url", "search_query", "author", "source_text",
                    "discovery_url", "relevance", "acquired_at")},
                "asset_sha": sha,
                "original_path": str(resolved),
                "original_filename": resolved.name,
                "width": size[0] if len(size) > 0 else None,
                "height": size[1] if len(size) > 1 else None,
                "derived": True,
                "parent_sha": parent_sha,
                "crop": child.get("crop"),
                "source_size": child.get("source_size"),
                "quality": child.get("quality"),
                "child_index": index,
                "child_total": total,
                "collage_layout": record.get("layout"),
                "algorithm_version": record.get("algorithm_version"),
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
    progress = read_json(folder / "progress.json", {})
    if not isinstance(progress,dict):progress={}
    if progress.get("phase") == "browser_recovering":
        return {"status":"running","stop_reason":"","phase":"browser_recovering",
                "browser_errors":progress.get("browser_errors",[])}
    if isinstance(summary, dict) and summary:
        return summary
    state = read_json(folder / "collector-state.json", {})
    if isinstance(state, dict) and state:
        status = "completed" if state.get("search_complete") else (
            "blocked" if state.get("search_stop_reason") in ("browser_unavailable", "sources_blocked") else "running"
        )
        return {
            "status": status,
            "stop_reason": state.get("search_stop_reason", ""),
            "found": len(state.get("received", [])),
            "phase": state.get("phase", ""),
            "browser_errors": read_json(folder / "browser-errors.json", [])[-20:],
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


def _item(row: dict, review: dict | None, human: dict | None, job_id: str,
          collage: dict | None = None) -> dict:
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
        "discovery_url": str(row.get("discovery_url") or ""),
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
        "derived": bool(row.get("derived")),
        "parent_sha": row.get("parent_sha") if row.get("derived") else None,
        "crop": row.get("crop") if row.get("derived") else None,
        "source_size": row.get("source_size") if row.get("derived") else None,
        "child_index": row.get("child_index") if row.get("derived") else None,
        "child_total": row.get("child_total") if row.get("derived") else None,
        "collage_layout": row.get("collage_layout") if row.get("derived") else None,
        "quality": row.get("quality") if row.get("derived") else None,
        "collage": collage if not row.get("derived") else None,
    }


def counts(items: list[dict], *, originals: int | None = None, folder=None,
           rows=None, records=None) -> dict:
    """Candidate counts.

    The photography/counting numbers come from the single canonical function
    (``collection_counts.compute``); this wrapper adds the per-card review and
    human-decision statuses. Human keep/reject never changes how many photos were
    acquired.
    """
    from .collection_counts import compute
    if folder is not None and rows is not None and records is not None:
        result = compute(folder, rows, records)
    else:
        result = {
            "found": len(items) if originals is None else int(originals),
            "target_confirmed": 0, "exploration": 0, "other_character": 0,
            "non_photo": 0, "original_singles": 0, "derived_valid": 0,
            "usable_independent": 0, "usable_named": 0, "awaiting_manual": 0,
            "collages": 0, "collage_split_ok": 0, "collage_partial": 0,
            "collage_needs_manual": 0, "collage_low_resolution": 0,
            "collage_duplicate": 0, "collage_failed": 0,
            "derived_total": 0, "derived_rejected": 0, "derived_duplicate": 0,
            "outdated_records": 0, "unprocessed": 0, "integrity_failures": 0,
        }
    result = {**result}
    result["cards"] = len(items)
    for key in ("accepted", "human_keep", "passed", "rejected", "human_reject",
                "blocked", "pending", "reviewing"):
        result[key] = 0
    for item in items:
        status = item.get("status")
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
    a reopened browser sees the same candidates after a restart. Derived collage
    tiles appear next to their parent, never in place of the original.
    """
    folder = run_directory(job_id)
    with _LOCK:
        rows = _received_rows(folder)
        records = _derived_records(folder)
        children = _derived_rows(folder, {row["asset_sha"]: row for row in rows})
        reviews = _review_items(folder)
        humans = _human_items(folder)
    items = []
    for row in rows:
        record = records.get(row["asset_sha"]) or {}
        collage_children = [child for child in (record.get("children") or []) if isinstance(child, dict)]
        collage = None
        if record:
            from . import collage as _collage
            collage = {
                "status": record.get("status") or "no_collage",
                "layout": record.get("layout") or "",
                "rows": record.get("rows"),
                "cols": record.get("cols"),
                "algorithm_version": record.get("algorithm_version"),
                "outdated": not _collage.record_is_current(record),
                "children_total": len(collage_children),
                "children_valid": sum(1 for child in collage_children if child.get("status") == "valid"),
                "children_rejected": sum(1 for child in collage_children
                                         if child.get("status") not in {"valid"}),
                "parent_counts": bool((record.get("counts") or {}).get("parent_counts",
                                                                      record.get("status") == "no_collage")),
                "reason": record.get("reason") or "",
                "integrity": record.get("integrity") or {},
            }
        items.append(_item(row, reviews.get(row["asset_sha"]), humans.get(row["asset_sha"]),
                           job_id, collage=collage))
        for child in children.get(row["asset_sha"], []):
            items.append(_item(child, None, humans.get(child["asset_sha"]), job_id))
    overall = counts(items, folder=folder, rows=rows, records=records)
    types = read_json(folder/'photo-types.json', {}).get('items', {})
    photo_audit = read_json(folder/'photo-audit.json', {}).get('items', {})
    associations = {}
    from .search_relevance import is_confirmed
    for row in rows:
        if not is_confirmed(row):
            continue
        shas = [row['asset_sha'], *[child.get('child_sha') for child in
                records.get(row['asset_sha'], {}).get('children', [])
                if child.get('status') in {'valid', 'duplicate_run'}]]
        for sha in shas:
            associations.setdefault(sha, []).append({'page_url':row.get('page_url'),
                'relevance':row['relevance']})
    for item in items:
        item['photo_type'] = types.get(item['asset_sha'], {'status':'pending'})
        item['photo_audit'] = photo_audit.get(item['asset_sha'])
        item['goal_qualified'] = item['asset_sha'] in overall['goal_shas']
        item['goal_name_evidence'] = associations.get(item['asset_sha'], [])
        item['name_associated'] = bool(item['goal_name_evidence'])
    offset = max(0, int(offset))
    limit = min(500, max(1, int(limit)))
    return {
        "version": 1,
        "job_id": job_id,
        "run_directory": str(folder),
        "search": _search_summary(folder),
        "review": _review_summary(folder),
        "postprocess": read_json(folder / "postprocess.json", {}),
        "postprocess_manager": read_json(folder / "postprocess-manager.json", {}),
        "live_import": read_json(folder / "live-import.json", {}),
        "progress": read_json(folder / "review-state.json", {}),
        "name_lookup": read_json(folder / "name-enrichment.json", {}),
        "counts": overall,
        "offset": offset,
        "limit": limit,
        "items": items[offset:offset + limit],
    }


def _queue_rows(folder: Path) -> list[dict]:
    """Durable rows a decision may target: originals plus usable collage tiles."""
    rows = _received_rows(folder)
    children = _derived_rows(folder, {row["asset_sha"]: row for row in rows})
    output = list(rows)
    for row in rows:
        output.extend(children.get(row["asset_sha"], []))
    return output


def decide(job_id: str, sha: str, decision: str) -> dict:
    if decision not in {"keep", "reject", "clear"}:
        raise ValueError("Human decision must be keep, reject or clear")
    if not _valid_sha(sha):
        raise ValueError("Invalid image SHA")
    folder = run_directory(job_id)
    rows = {row["asset_sha"]: row for row in _queue_rows(folder)}
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
    """Bytes for one candidate card: an original or a usable derived tile.

    The content hash is always re-verified, so a changed file is refused instead
    of being displayed as the reviewed image.
    """
    if not _valid_sha(sha):
        raise ValueError("Invalid image SHA")
    folder = run_directory(job_id)
    for row in _queue_rows(folder):
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
