"""Additive v2 catalog migration; no image bytes, choices or accepted cards rewritten."""
from __future__ import annotations

import json
import sqlite3
from .db import encode, now
from .catalog_data import keep_inspiration, record_discovery, record_observation

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS discoveries (
 id TEXT PRIMARY KEY, asset_sha TEXT REFERENCES assets(id),
 project_id TEXT REFERENCES projects(id), job_id TEXT REFERENCES jobs(id),
 reference_id TEXT REFERENCES refs(id), data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS discovery_asset ON discoveries(asset_sha);
CREATE INDEX IF NOT EXISTS discovery_job ON discoveries(job_id);
CREATE TABLE IF NOT EXISTS asset_observations (
 id TEXT PRIMARY KEY, asset_sha TEXT NOT NULL REFERENCES assets(id), data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS observation_asset ON asset_observations(asset_sha);
CREATE TABLE IF NOT EXISTS inspirations (
 id TEXT PRIMARY KEY, asset_sha TEXT REFERENCES assets(id), active INTEGER NOT NULL,
 data TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS inspiration_asset ON inspirations(asset_sha) WHERE asset_sha IS NOT NULL;
CREATE INDEX IF NOT EXISTS inspiration_active ON inspirations(active);
"""


def upgrade_catalog(con: sqlite3.Connection) -> dict:
    report = {"references_preserved": 0, "discoveries": 0, "inspirations": 0, "observations": 0}
    for statement in CATALOG_SCHEMA.split(";"):
        if statement.strip():
            con.execute(statement)
    # Nullable ownership permits genuinely global notes, retaining IDs and fingerprints.
    info = {r[1]: r for r in con.execute("PRAGMA table_info(notes)")}
    if info["project_id"][3]:
        con.execute("ALTER TABLE notes RENAME TO notes_v1")
        con.execute("CREATE TABLE notes (id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id), "
                    "fingerprint TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(project_id,fingerprint))")
        con.execute("INSERT INTO notes SELECT * FROM notes_v1")
        con.execute("DROP TABLE notes_v1")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS global_note_fingerprint ON notes(fingerprint) WHERE project_id IS NULL")
    for row in con.execute("SELECT data FROM refs").fetchall():
        ref = json.loads(row[0])
        report["references_preserved"] += 1
        # Do not guess past role/costume/free-text context from today's project values.
        for source in ref.get("discovered_sources", [ref["source"]]):
            record_discovery(con, ref, source, legacy=True)
        record_observation(con, ref)
        if ref["decision"] == "keep" and ref["lane"] == "inspiration":
            keep_inspiration(con, asset_sha=ref["asset_sha"], title=ref["title"], source=ref["source"],
                             preference=ref.get("preference", ""), borrow=ref.get("borrow", []), origin_ref=ref)
        if ref["decision"] == "reject":
            # A conservative new retention window; old rejection time may be unknown.
            ref.setdefault("rejected_at", now())
            ref.setdefault("before_reject", {"decision": "pending", "lane": ref["lane"]})
            con.execute("UPDATE refs SET data=? WHERE id=?", (encode(ref), ref["id"]))
    for table, key in (("discoveries", "discoveries"), ("inspirations", "inspirations"), ("asset_observations", "observations")):
        report[key] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return report
