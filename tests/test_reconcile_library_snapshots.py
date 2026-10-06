from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "reconcile_library_snapshots.py"


BASE_SCHEMA = """
CREATE TABLE projects (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE assets (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE refs (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL);
CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, project_id TEXT, entity_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, data TEXT NOT NULL);
"""


def make_db(path: Path, version: int = 3) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(BASE_SCHEMA)
    con.execute("INSERT INTO projects VALUES ('p1','{}')")
    con.execute("INSERT INTO assets VALUES ('base-asset','{}')")
    con.execute("INSERT INTO refs VALUES ('r1','p1',1,'{\"decision\":\"pending\"}')")
    con.execute("INSERT INTO refs VALUES ('r2','p1',1,'{\"decision\":\"pending\"}')")
    con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES ('t0','p1','r1','human','created','{}')")
    con.execute(f"PRAGMA user_version={version}")
    con.commit()
    return con


def run_cli(base: Path, current: Path, incoming: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base), "--current", str(current), "--incoming", str(incoming), *extra],
        text=True,
        capture_output=True,
        check=False,
    )


def report_from(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepared_triplet(tmp_path: Path) -> tuple[Path, Path, Path]:
    base, current, incoming = (tmp_path / name for name in ("base.sqlite", "current.sqlite", "incoming.sqlite"))
    base_con = make_db(base, version=3)
    base_con.close()
    for path, version in ((current, 4), (incoming, 3)):
        con = make_db(path, version=version)
        con.close()
    return base, current, incoming


def test_dry_run_and_apply_merge_incoming_rows_without_losing_current_only_data(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    with sqlite3.connect(current) as con:
        con.execute("INSERT INTO assets VALUES ('dot-asset','{\"source\":\"Dot\"}')")
        con.execute("CREATE TABLE study_candidates (id TEXT PRIMARY KEY, asset_sha TEXT NOT NULL)")
        con.execute("INSERT INTO study_candidates VALUES ('dot-candidate','dot-asset')")
        con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES ('t1','p1','dot-asset','human','study.imported','{}')")
        con.execute("UPDATE refs SET revision=2 WHERE id='r2'")
        con.execute("PRAGMA user_version=4")
    with sqlite3.connect(incoming) as con:
        con.execute("UPDATE refs SET revision=2,data=? WHERE id='r1'", ('{"decision":"keep"}',))
        con.execute("CREATE TABLE asset_observations (id TEXT PRIMARY KEY, asset_sha TEXT NOT NULL REFERENCES assets(id), data TEXT NOT NULL)")
        con.execute("CREATE INDEX observation_asset ON asset_observations(asset_sha)")
        con.execute("INSERT INTO asset_observations VALUES ('ai-first','base-asset','{\"actor\":\"ai\",\"n\":1}')")
        con.execute("INSERT INTO asset_observations VALUES ('ai-latest','base-asset','{\"actor\":\"ai\",\"n\":2}')")
        con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES ('t1','p1','r1','ai','classified','{}')")

    input_hashes = {path: digest(path) for path in (base, current, incoming)}
    output = tmp_path / "merged.sqlite"
    dry = run_cli(base, current, incoming, "--output", str(output))
    assert dry.returncode == 0, dry.stderr
    dry_report = report_from(dry)
    assert dry_report["status"] == "dry_run_clean"
    assert not output.exists()

    applied = run_cli(base, current, incoming, "--apply", "--output", str(output))
    assert applied.returncode == 0, applied.stderr
    report = report_from(applied)
    assert report["status"] == "applied"
    assert report["inputs"]["base"]["user_version"] == 3
    assert report["inputs"]["incoming"]["user_version"] == 3
    assert report["result"]["user_version"] == 4
    assert report["event_id_map"]["2"] == 3

    with sqlite3.connect(output) as con:
        assert con.execute("SELECT revision,data FROM refs WHERE id='r1'").fetchone() == (2, '{"decision":"keep"}')
        assert con.execute("SELECT revision,data FROM refs WHERE id='r2'").fetchone() == (2, '{"decision":"pending"}')
        assert con.execute("SELECT data FROM assets WHERE id='dot-asset'").fetchone() == ('{"source":"Dot"}',)
        assert con.execute("SELECT id,asset_sha FROM study_candidates").fetchone() == ("dot-candidate", "dot-asset")
        assert [r[0] for r in con.execute("SELECT id FROM asset_observations ORDER BY rowid")] == ["ai-first", "ai-latest"]
        assert con.execute("SELECT id FROM events ORDER BY id").fetchall() == [(1,), (2,), (3,)]
        assert con.execute("PRAGMA user_version").fetchone()[0] == 4
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert {path: digest(path) for path in (base, current, incoming)} == input_hashes


def test_conflicting_two_sided_row_changes_report_key_and_do_not_write(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    with sqlite3.connect(current) as con:
        con.execute("UPDATE refs SET revision=2,data='current' WHERE id='r1'")
    with sqlite3.connect(incoming) as con:
        con.execute("UPDATE refs SET revision=3,data='incoming' WHERE id='r1'")
    output = tmp_path / "must-not-exist.sqlite"

    result = run_cli(base, current, incoming, "--apply", "--output", str(output))

    assert result.returncode != 0
    report = report_from(result)
    assert report["status"] == "conflict"
    assert {("refs", "r1")} <= {(item.get("table"), item.get("key")) for item in report["conflicts"]}
    assert not output.exists()


def test_duplicate_incoming_events_are_deduplicated_on_repeat_merge(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    with sqlite3.connect(current) as con:
        con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES ('t1','p1','r1','ai','classified','{}')")
    with sqlite3.connect(incoming) as con:
        con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES ('t1','p1','r1','ai','classified','{}')")
        con.execute("INSERT INTO events(at,project_id,entity_id,actor,action,data) VALUES ('t1','p1','r1','ai','classified','{}')")
    first_output = tmp_path / "first.sqlite"
    first = run_cli(base, current, incoming, "--apply", "--output", str(first_output))
    assert first.returncode == 0, first.stderr
    first_report = report_from(first)
    assert first_report["event_id_map"] == {"2": 2, "3": 3}

    second_output = tmp_path / "second.sqlite"
    second = run_cli(base, first_output, incoming, "--apply", "--output", str(second_output))
    assert second.returncode == 0, second.stderr
    second_report = report_from(second)
    assert second_report["event_id_map"] == {"2": 2, "3": 3}
    with sqlite3.connect(second_output) as con:
        assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3


@pytest.mark.parametrize("delete_side", ["incoming", "current"])
def test_deleting_baseline_event_reports_conflict_without_traceback(tmp_path: Path, delete_side: str) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    target = incoming if delete_side == "incoming" else current
    with sqlite3.connect(target) as con:
        con.execute("DELETE FROM events WHERE id=1")

    result = run_cli(base, current, incoming)

    assert result.returncode != 0
    report = report_from(result)
    assert report["status"] == "conflict"
    assert any(item["kind"] == "row_deletion" and item["table"] == "events" for item in report["conflicts"])
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("delete_side", ["incoming", "current"])
def test_deleting_any_baseline_row_blocks_apply(tmp_path: Path, delete_side: str) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    target = incoming if delete_side == "incoming" else current
    with sqlite3.connect(target) as con:
        con.execute("DELETE FROM refs WHERE id='r1'")
    output = tmp_path / "must-not-exist.sqlite"

    result = run_cli(base, current, incoming, "--apply", "--output", str(output))

    assert result.returncode != 0
    report = report_from(result)
    assert any(item["kind"] == "row_deletion" and item["table"] == "refs" for item in report["conflicts"])
    assert not output.exists()


def test_refuses_input_or_existing_output_overwrite_and_leaves_inputs_unchanged(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    hashes = {path: digest(path) for path in (base, current, incoming)}
    overwrite_input = run_cli(base, current, incoming, "--apply", "--output", str(current))
    assert overwrite_input.returncode != 0
    existing_output = tmp_path / "already-there.sqlite"
    existing_output.write_bytes(b"owner data")
    existing_hash = digest(existing_output)
    overwrite_existing = run_cli(base, current, incoming, "--apply", "--output", str(existing_output))
    assert overwrite_existing.returncode != 0
    assert digest(existing_output) == existing_hash
    assert {path: digest(path) for path in (base, current, incoming)} == hashes


def test_new_foreign_key_violation_blocks_output(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    with sqlite3.connect(incoming) as con:
        con.execute("CREATE TABLE asset_observations (id TEXT PRIMARY KEY, asset_sha TEXT NOT NULL REFERENCES assets(id), data TEXT NOT NULL)")
        con.execute("INSERT INTO asset_observations VALUES ('bad','missing-asset','{}')")
    output = tmp_path / "must-not-exist.sqlite"

    result = run_cli(base, current, incoming, "--apply", "--output", str(output))

    assert result.returncode != 0
    report = report_from(result)
    assert report["status"] == "failed"
    assert "foreign key" in report["error"].lower()
    assert not output.exists()


def test_preexisting_foreign_key_problem_is_preserved_without_increase(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    for path in (base, current, incoming):
        with sqlite3.connect(path) as con:
            con.execute("CREATE TABLE legacy_links (id TEXT PRIMARY KEY, project_id TEXT REFERENCES projects(id))")
            con.execute("INSERT INTO legacy_links VALUES ('legacy-orphan','missing-project')")
    output = tmp_path / "preserved-legacy-problem.sqlite"

    result = run_cli(base, current, incoming, "--apply", "--output", str(output))

    assert result.returncode == 0, result.stderr
    report = report_from(result)
    assert report["current_foreign_key_violation_count"] == 1
    assert report["result"]["foreign_key_violation_count"] == 1
    with sqlite3.connect(output) as con:
        assert len(con.execute("PRAGMA foreign_key_check").fetchall()) == 1


def test_new_table_without_primary_key_is_rejected(tmp_path: Path) -> None:
    base, current, incoming = prepared_triplet(tmp_path)
    with sqlite3.connect(incoming) as con:
        con.execute("CREATE TABLE unknown_table (value TEXT)")

    result = run_cli(base, current, incoming)

    assert result.returncode != 0
    assert report_from(result)["status"] == "failed"
    assert "primary key" in report_from(result)["error"].lower()
