"""Asset-level records, independent of project curation and field-card acceptance.

These helpers share their caller's transaction. A discovery intent never writes a
visual observation. An observation never creates a project use or an acceptance.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from uuid import uuid4
from .db import encode, now

FACT_FIELDS = ("asset_sha", "kind", "visible_person", "pose_readable", "single_image",
               "sufficiently_clear", "observations", "critical_uncertainties")


def record_discovery(con: sqlite3.Connection, ref: dict, source: dict, *,
                     project_snapshot: dict | None = None, job_id: str | None = None,
                     intent: str = "unknown", reason: str = "", discovery_url: str = "",
                     import_key: str = "", legacy: bool = False) -> str:
    # The import key preserves distinct historical sightings of deduplicated bytes.
    identity = {"reference_id": ref["id"], "asset_sha": ref.get("asset_sha"),
                "job_id": job_id, "source": source, "intent": intent,
                "discovery_url": discovery_url, "import_key": import_key}
    ident = hashlib.sha256(encode(identity).encode()).hexdigest()
    data = {**identity, "id": ident, "discovery_reason": reason,
            "project_id": ref.get("project_id"), "project_snapshot": project_snapshot,
            "context_status": "legacy_context_unknown" if legacy else "captured_at_discovery",
            "created_at": now()}
    con.execute("INSERT OR IGNORE INTO discoveries VALUES(?,?,?,?,?,?)",
                (ident, ref.get("asset_sha"), ref.get("project_id"), job_id, ref["id"], encode(data)))
    return ident


def record_observation(con: sqlite3.Connection, ref: dict) -> str | None:
    review = ref.get("review")
    if not review or not ref.get("asset_sha") or review.get("asset_sha") != ref["asset_sha"]:
        return None
    # character_match is a project-specific assessment, not a fact about the asset.
    data = {"facts": {k: review[k] for k in FACT_FIELDS}, "actor": ref.get("review_actor", "unknown"),
            "producer": ref.get("review_producer", "unknown"), "origin_reference_id": ref["id"]}
    ident = hashlib.sha256(encode(data).encode()).hexdigest()
    data.update(id=ident, created_at=now())
    con.execute("INSERT OR IGNORE INTO asset_observations VALUES(?,?,?)",
                (ident, ref["asset_sha"], encode(data)))
    return ident


def keep_inspiration(con: sqlite3.Connection, *, asset_sha: str | None, title: str,
                     source: dict, preference: str = "", borrow: list | None = None,
                     origin_ref: dict | None = None) -> tuple[dict, bool]:
    """Save/revive a global membership without overwriting another context's taste.

Missing historical images get a stable legacy identity; their metadata is not lost.
    """
    ident = f"missing-{origin_ref['id']}" if not asset_sha and origin_ref else uuid4().hex
    row = (con.execute("SELECT data FROM inspirations WHERE asset_sha=?", (asset_sha,)).fetchone()
           if asset_sha else con.execute("SELECT data FROM inspirations WHERE id=?", (ident,)).fetchone())
    created = row is None
    if row:
        item = json.loads(row[0])
        before = encode(item)
        item.update(active=True, removed_at=None)
    else:
        item = {"id": ident, "asset_sha": asset_sha, "title": title, "source": source,
                "preference": preference, "borrow": borrow or [], "context_notes": [],
                "origin_reference_ids": [], "active": True, "removed_at": None,
                "revision": 1, "created_at": now(), "updated_at": now()}
        before = ""
    if origin_ref:
        if origin_ref["id"] not in item["origin_reference_ids"]:
            item["origin_reference_ids"].append(origin_ref["id"])
        note = {"reference_id": origin_ref["id"], "project_id": origin_ref["project_id"],
                "preference": preference, "borrow": borrow or []}
        if note not in item["context_notes"] and (preference or borrow):
            item["context_notes"].append(note)
    if created:
        con.execute("INSERT INTO inspirations VALUES(?,?,?,?)", (item["id"], asset_sha, 1, encode(item)))
    elif encode(item) != before:
        item.update(revision=item["revision"] + 1, updated_at=now())
        con.execute("UPDATE inspirations SET active=1,data=? WHERE id=?", (encode(item), item["id"]))
    return item, created
