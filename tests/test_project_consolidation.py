from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from ref_lab.db import Database, encode
from tools.consolidate_duplicate_project import (
    ConsolidationRefused,
    apply_merge,
    build_merge_plan,
    rollback_merge,
)


SEMANTIC = {
    "character": "安养寺姬芽",
    "work": "作品 A",
    "costume": "服装 B",
    "brief": "保留人工选择",
    "gear": "Sony A7M4；50mm f/1.8",
}
SOURCE_ID = "77458f14b4d64487a5aae3302acef152"
TARGET_ID = "f0619bf62bb04d41825fee93fe3164a2"


def _sha(number: int) -> str:
    return f"{number:064x}"


def _project(ident: str, **changes):
    now = "2026-10-29T00:00:00.000+00:00"
    return {
        "id": ident,
        **SEMANTIC,
        "revision": 3,
        "archived_at": None,
        "created_at": now,
        "updated_at": now,
        **changes,
    }


def _ref(ident: str, project_id: str, asset_sha: str, decision: str, number: int, **changes):
    return {
        "id": ident,
        "project_id": project_id,
        "asset_sha": asset_sha,
        "title": f"ref {number}",
        "source": {"page_url": f"https://example.invalid/{number}", "source_confirmed": True},
        "discovered_sources": [],
        "legacy_notes": "",
        "decision": decision,
        "lane": "field",
        "preference": f"human preference {number}",
        "borrow": [f"borrow {number}"],
        "allow_cross_domain": False,
        "review": None,
        "card": None,
        "accepted_fingerprint": None,
        "revision": 4,
        "created_at": "2026-10-29T00:00:00.000+00:00",
        "updated_at": "2026-10-29T00:00:00.000+00:00",
        "before_reject": {"decision": "pending"} if decision == "reject" else None,
        **changes,
    }


def seed_library(
    root: Path, *, semantic: dict | None = None, overlap: bool = False,
    historical_foreign_keys: bool = False,
):
    database = root / "data" / "library.sqlite3"
    Database(database)
    source_project = _project(SOURCE_ID, **(semantic or {}))
    target_project = _project(TARGET_ID)
    now = "2026-10-29T00:00:00.000+00:00"
    source_refs = []
    for number in range(20):
        decision = "pending" if number < 6 else "reject"
        source_refs.append(_ref(f"source-{number:02d}", SOURCE_ID, _sha(number + 1), decision, number))
    target_sha = _sha(1) if overlap else _sha(101)
    target_ref = _ref("target-keep", TARGET_ID, target_sha, "keep", 101)
    source_refs[0].update(
        preflight={"id": "old-pf", "asset_sha": _sha(1), "producer": "legacy-machine",
                   "project_context": "old-project-context", "status": "filtered"},
        preflight_context="old-project-context",
        preflight_filtered=True,
        preflight_status="filtered",
        preflight_reason="old prediction",
        preflight_id="old-pf",
        dhash="old-project-dhash",
    )
    running_job = {
        "id": "target-running", "project_id": TARGET_ID, "kind": "collection", "status": "running",
        "revision": 9, "search_state": "running", "review_state": "idle",
    }
    with sqlite3.connect(database) as con:
        con.execute("INSERT INTO projects VALUES(?,?)", (SOURCE_ID, encode(source_project)))
        con.execute("INSERT INTO projects VALUES(?,?)", (TARGET_ID, encode(target_project)))
        for ref in [*source_refs, target_ref]:
            con.execute("INSERT OR IGNORE INTO assets VALUES(?,?)", (ref["asset_sha"], encode({
                "id": ref["asset_sha"], "storage_status": "available", "integrity": "ok",
            })))
            con.execute("INSERT INTO refs VALUES(?,?,?,?,?,?)", (
                ref["id"], ref["project_id"], ref["asset_sha"], ref["decision"], "candidate", encode(ref),
            ))
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?)", (
            running_job["id"], TARGET_ID, "collection", "running", encode(running_job),
        ))
        con.execute("INSERT INTO preflights VALUES(?,?,?,?,?,?,?)", (
            "old-pf", _sha(1), SOURCE_ID, "source-00", None, "filtered", encode(source_refs[0]["preflight"]),
        ))
        con.execute("INSERT INTO aliases VALUES(?,?,?)", (SOURCE_ID, "legacy", "source-00"))
        con.execute("INSERT INTO screening_sessions VALUES(?,?,?,?,?,?)", (
            "source-session", SOURCE_ID, "finished", now, now, encode({"id": "source-session"}),
        ))
        if historical_foreign_keys:
            con.execute("CREATE TABLE historical_orphans (id TEXT REFERENCES assets(id))")
            con.execute("INSERT INTO historical_orphans VALUES(?)", (_sha(9001),))
            con.execute("INSERT INTO aliases VALUES(?,?,?)", (SOURCE_ID, "orphan", "missing-ref"))
            con.execute("INSERT INTO discoveries VALUES(?,?,?,?,?,?)", (
                "orphan-discovery", _sha(1), SOURCE_ID, None, "missing-ref", "{}",
            ))
            con.execute("INSERT INTO preflights VALUES(?,?,?,?,?,?,?)", (
                "orphan-preflight", _sha(1), SOURCE_ID, "missing-ref", None, "unknown", "{}",
            ))
    return database, source_refs, target_ref, running_job


def _rows(database: Path, table: str, where: str = "", args=()):
    with sqlite3.connect(database) as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute(f"SELECT * FROM {table} {where}", args)]


def _foreign_keys(database: Path):
    with sqlite3.connect(database) as con:
        rows = [[str(row[0]), row[1], str(row[2]), int(row[3])]
                for row in con.execute("PRAGMA foreign_key_check")]
    return sorted(rows, key=lambda row: (row[0], row[1] is not None, row[1] or 0, row[2], row[3]))


def test_merge_preserves_all_decisions_running_target_and_original_bytes(tmp_path):
    database, source_refs, target_ref, running_job = seed_library(tmp_path)
    original = tmp_path / "data" / "assets" / "original.png"
    original.parent.mkdir()
    original.write_bytes(b"immutable original bytes")
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    target_job_before = _rows(database, "jobs", "WHERE project_id=?", (TARGET_ID,))
    target_ref_before = _rows(database, "refs", "WHERE project_id=?", (TARGET_ID,))

    plan = build_merge_plan(
        database, SOURCE_ID, TARGET_ID,
        expected_source_revision=3, expected_target_revision=3,
    )
    assert plan["status"] == "ready", plan["errors"]
    result = apply_merge(database, plan, receipt_root=tmp_path / "merge-receipts")

    source_rows = _rows(database, "refs", "WHERE project_id=?", (SOURCE_ID,))
    target_rows = _rows(database, "refs", "WHERE project_id=? ORDER BY id", (TARGET_ID,))
    assert source_rows == []
    assert len(target_rows) == 21
    decisions = [json.loads(row["data"])["decision"] for row in target_rows if row["id"].startswith("source-")]
    assert decisions.count("pending") == 6
    assert decisions.count("reject") == 14
    assert next(row for row in target_rows if row["id"] == target_ref["id"])["decision"] == "keep"
    assert _rows(database, "jobs", "WHERE project_id=?", (TARGET_ID,)) == target_job_before
    assert [row for row in target_rows if row["id"] == target_ref["id"]] == target_ref_before
    assert json.loads(_rows(database, "jobs", "WHERE id=?", (running_job["id"],))[0]["data"]) == running_job

    with sqlite3.connect(database) as con:
        source_project = json.loads(con.execute("SELECT data FROM projects WHERE id=?", (SOURCE_ID,)).fetchone()[0])
        moved = json.loads(con.execute("SELECT data FROM refs WHERE id=?", (source_refs[0]["id"],)).fetchone()[0])
        assert source_project["merged_into"] == TARGET_ID and source_project["archived_at"]
        assert moved["project_id"] == TARGET_ID and moved["revision"] == 5
        assert moved["preference"] == "human preference 0" and moved["borrow"] == ["borrow 0"]
        assert moved["before_reject"] is None and moved["created_at"] == source_refs[0]["created_at"]
        assert moved["preflight"] is None and moved["preflight_context"] is None
        assert moved["preflight_status"] == "unreviewed" and moved["preflight_filtered"] == 0
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
    assert original.read_bytes() == b"immutable original bytes"
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
    receipt = Path(result["receipt_dir"]) / "receipt.json"
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert saved["status"] == "applied" and len(saved["moved_references"]) == 20
    assert Path(saved["before_backup"]).is_file()
    for table in ("jobs", "aliases", "preflights", "screening_sessions", "target_refs"):
        assert saved["history_before"][table] == saved["history_after"][table]


def test_source_running_job_is_refused(tmp_path):
    database, _, _, _ = seed_library(tmp_path)
    with sqlite3.connect(database) as con:
        data = {"id": "source-running", "project_id": SOURCE_ID, "status": "running"}
        con.execute("INSERT INTO jobs VALUES(?,?,?,?,?)", ("source-running", SOURCE_ID, "collection", "running", encode(data)))
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    assert plan["status"] == "blocked"
    assert any("source project has queued/running jobs" in error for error in plan["errors"])
    with pytest.raises(ConsolidationRefused, match="blocked"):
        apply_merge(database, plan, receipt_root=tmp_path / "receipts")


def test_unrelated_historical_foreign_key_orphans_do_not_block_merge_or_rollback(tmp_path):
    database, _, _, _ = seed_library(tmp_path)
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    assert plan["status"] == "ready", plan["errors"]
    assert plan["foreign_key_findings"] == []

    database, _, _, _ = seed_library(tmp_path / "with-orphan", historical_foreign_keys=True)
    expected = _foreign_keys(database)
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    assert plan["status"] == "ready", plan["errors"]
    assert plan["foreign_key_findings"] == expected
    assert len(expected) == 4
    applied = apply_merge(database, plan, receipt_root=tmp_path / "receipts")
    assert applied["foreign_key_findings_before"] == expected
    assert applied["foreign_key_findings_after"] == expected
    assert _foreign_keys(database) == expected
    rollback_merge(
        database, Path(applied["receipt_dir"]) / "receipt.json",
        receipt_root=tmp_path / "rollback-receipts",
    )
    assert _foreign_keys(database) == expected


def test_missing_source_asset_is_refused_even_if_foreign_key_error_is_old(tmp_path):
    database, _, _, _ = seed_library(tmp_path)
    with sqlite3.connect(database) as con:
        con.execute("DELETE FROM assets WHERE id=?", (_sha(2),))
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    assert plan["status"] == "blocked"
    assert any("source ref asset is missing" in error for error in plan["errors"])


def test_new_foreign_key_error_after_planning_is_refused(tmp_path):
    database, _, _, _ = seed_library(tmp_path)
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    assert plan["status"] == "ready" and plan["foreign_key_findings"] == []
    with sqlite3.connect(database) as con:
        con.execute("DELETE FROM assets WHERE id=?", (_sha(2),))
    with pytest.raises(ConsolidationRefused, match="unresolved foreign keys changed"):
        apply_merge(database, plan, receipt_root=tmp_path / "receipts")
    with sqlite3.connect(database) as con:
        assert len(con.execute("PRAGMA foreign_key_check").fetchall()) >= 1
        assert con.execute("SELECT COUNT(*) FROM refs WHERE project_id=?", (SOURCE_ID,)).fetchone()[0] == 20


@pytest.mark.parametrize("operation", ["apply", "rollback"])
def test_new_foreign_key_error_inside_transaction_is_rolled_back(tmp_path, operation):
    database, _, _, _ = seed_library(tmp_path, historical_foreign_keys=True)
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    applied = None
    if operation == "rollback":
        applied = apply_merge(database, plan, receipt_root=tmp_path / "receipts")
    with sqlite3.connect(database) as con:
        con.executescript("""
            CREATE TABLE deferred_orphans (
                project_id TEXT REFERENCES projects(id) DEFERRABLE INITIALLY DEFERRED
            );
            CREATE TRIGGER inject_orphan AFTER UPDATE ON projects BEGIN
                INSERT INTO deferred_orphans VALUES ('missing-project');
            END;
        """)
        original_findings = [list(row) for row in con.execute("PRAGMA foreign_key_check")]
        original_project = con.execute("SELECT data FROM projects WHERE id=?", (SOURCE_ID,)).fetchone()[0]
        original_refs = con.execute("SELECT COUNT(*) FROM refs WHERE project_id=?", (SOURCE_ID,)).fetchone()[0]
    with pytest.raises(ConsolidationRefused, match="during " + operation):
        if operation == "apply":
            apply_merge(database, plan, receipt_root=tmp_path / "failed-receipts")
        else:
            rollback_merge(database, Path(applied["receipt_dir"]) / "receipt.json",
                           receipt_root=tmp_path / "failed-receipts")
    with sqlite3.connect(database) as con:
        assert [list(row) for row in con.execute("PRAGMA foreign_key_check")] == original_findings
        assert con.execute("SELECT data FROM projects WHERE id=?", (SOURCE_ID,)).fetchone()[0] == original_project
        assert con.execute("SELECT COUNT(*) FROM refs WHERE project_id=?", (SOURCE_ID,)).fetchone()[0] == original_refs
        assert con.execute("SELECT COUNT(*) FROM deferred_orphans").fetchone()[0] == 0
    receipt_path = next((tmp_path / "failed-receipts").glob("*/receipt.json"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert len(receipt["foreign_key_findings_after"]) > len(receipt["foreign_key_findings_before"])


def test_foreign_key_findings_support_without_rowid_tables(tmp_path):
    database, _, _, _ = seed_library(tmp_path)
    with sqlite3.connect(database) as con:
        con.executescript("""
            CREATE TABLE old_without_rowid (
                id TEXT PRIMARY KEY, asset TEXT REFERENCES assets(id)
            ) WITHOUT ROWID;
            INSERT INTO old_without_rowid VALUES ('old', 'missing');
        """)
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    assert plan["status"] == "ready"
    assert any(row[0] == "old_without_rowid" and row[1] is None for row in plan["foreign_key_findings"])
    apply_merge(database, plan, receipt_root=tmp_path / "receipts")


def test_semantic_mismatch_and_sha_overlap_are_refused(tmp_path):
    mismatch_db, _, _, _ = seed_library(tmp_path / "mismatch", semantic={"costume": "different"})
    mismatch = build_merge_plan(mismatch_db, SOURCE_ID, TARGET_ID)
    assert mismatch["status"] == "blocked"
    assert "source and target project semantic fields differ" in mismatch["errors"]

    overlap_db, _, _, _ = seed_library(tmp_path / "overlap", overlap=True)
    overlap = build_merge_plan(overlap_db, SOURCE_ID, TARGET_ID)
    assert overlap["status"] == "blocked"
    assert any("asset SHA overlap" in error for error in overlap["errors"])


def test_stale_plan_and_unsupported_evidence_are_refused(tmp_path):
    database, source_refs, _, _ = seed_library(tmp_path / "stale")
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    changed = dict(source_refs[0], revision=99, preference="user changed this")
    with sqlite3.connect(database) as con:
        con.execute("UPDATE refs SET data=? WHERE id=?", (encode(changed), changed["id"]))
    with pytest.raises(ConsolidationRefused, match="source refs changed"):
        apply_merge(database, plan, receipt_root=tmp_path / "receipts-stale")

    evidence_db, evidence_refs, _, _ = seed_library(tmp_path / "evidence")
    supported = dict(evidence_refs[1], review={"asset_sha": evidence_refs[1]["asset_sha"]})
    with sqlite3.connect(evidence_db) as con:
        con.execute("UPDATE refs SET data=? WHERE id=?", (encode(supported), supported["id"]))
    evidence_plan = build_merge_plan(evidence_db, SOURCE_ID, TARGET_ID)
    assert evidence_plan["status"] == "blocked"
    assert any("has a review" in error for error in evidence_plan["errors"])

    notes_db, _, _, _ = seed_library(tmp_path / "notes")
    with sqlite3.connect(notes_db) as con:
        con.execute("INSERT INTO notes VALUES(?,?,?,?)", (
            "note-1", SOURCE_ID, "fingerprint", encode({"id": "note-1", "project_id": SOURCE_ID}),
        ))
    notes_plan = build_merge_plan(notes_db, SOURCE_ID, TARGET_ID)
    assert notes_plan["status"] == "blocked"
    assert any("notes" in error for error in notes_plan["errors"])


def test_scoped_rollback_preserves_new_target_records_and_increments_revision(tmp_path):
    database, source_refs, _, running_job = seed_library(tmp_path)
    plan = build_merge_plan(database, SOURCE_ID, TARGET_ID)
    applied = apply_merge(database, plan, receipt_root=tmp_path / "receipts")
    new_ref = _ref("target-new-after-merge", TARGET_ID, _sha(999), "pending", 999)
    with sqlite3.connect(database) as con:
        con.execute("INSERT INTO assets VALUES(?,?)", (_sha(999), encode({"id": _sha(999)})))
        con.execute("INSERT INTO refs VALUES(?,?,?,?,?,?)", (
            new_ref["id"], TARGET_ID, new_ref["asset_sha"], "pending", "candidate", encode(new_ref),
        ))

    rolled_back = rollback_merge(
        database, Path(applied["receipt_dir"]) / "receipt.json",
        receipt_root=tmp_path / "rollback-receipts",
    )
    assert rolled_back["status"] == "rolled_back"
    assert len(_rows(database, "refs", "WHERE project_id=?", (SOURCE_ID,))) == 20
    new_rows = _rows(database, "refs", "WHERE id=?", (new_ref["id"],))
    assert len(new_rows) == 1 and new_rows[0]["project_id"] == TARGET_ID
    moved = json.loads(_rows(database, "refs", "WHERE id=?", (source_refs[0]["id"],))[0]["data"])
    assert moved["project_id"] == SOURCE_ID and moved["revision"] == 6
    assert moved["preflight_id"] == "old-pf"
    with sqlite3.connect(database) as con:
        project = json.loads(con.execute("SELECT data FROM projects WHERE id=?", (SOURCE_ID,)).fetchone()[0])
        assert project["archived_at"] is None and "merged_into" not in project
        assert project["revision"] == 5
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
    assert len(_rows(database, "jobs", "WHERE id=?", (running_job["id"],))) == 1
