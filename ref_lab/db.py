"""SQLite transactions and a versioned schema; images never live in the database."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS refs (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 asset_sha TEXT REFERENCES assets(id), decision TEXT NOT NULL, state TEXT NOT NULL,
 data TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ref_asset_project ON refs(project_id,asset_sha) WHERE asset_sha IS NOT NULL;
CREATE INDEX IF NOT EXISTS ref_project ON refs(project_id,decision,state);
CREATE TABLE IF NOT EXISTS aliases (
 project_id TEXT NOT NULL REFERENCES projects(id), import_key TEXT NOT NULL,
 ref_id TEXT NOT NULL REFERENCES refs(id), PRIMARY KEY(project_id,import_key)
);
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 kind TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS job_queue ON jobs(kind,status);
CREATE TABLE IF NOT EXISTS notes (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 fingerprint TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(project_id,fingerprint)
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, project_id TEXT,
 entity_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS event_project ON events(project_id,id);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.read() as con:
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1}:
                raise RuntimeError(f"Unsupported database schema {version}; restore or migrate explicitly")
            con.executescript(SCHEMA)
            con.execute("PRAGMA user_version=1")
            con.commit()

    def connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=15000")
        return con

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        con = self.connection()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        con = self.connection()
        try:
            yield con
        finally:
            con.close()

    @staticmethod
    def event(con: sqlite3.Connection, project_id: str | None, entity_id: str,
              action: str, payload: object, actor: str = "human") -> None:
        con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES(?,?,?,?,?,?)",
                    (now(), project_id, entity_id, actor, action, encode(payload)))
