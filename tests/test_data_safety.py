from contextlib import closing
import json
import sqlite3
import zipfile

import pytest

from conftest import image_bytes
from ref_lab.cli import backup, doctor
from ref_lab.config import Settings
from ref_lab.models import CandidateInput, ProjectInput
from ref_lab.service import Library
from tools.clean_and_reingest import retire_pending_slices
from tools.recover_orphaned_references import recover_copy


def slice_reference(library, project):
    asset = library.ingest_asset(image_bytes(), "fixture.png")
    ref = library.add_candidate(project["id"], CandidateInput(
        asset_sha=asset["id"], title="【动作#01】synthetic slice", import_key="split:fixture:1",
    ))["reference"]
    library.scan_project_preflight(project["id"], force=True)
    return library.reference(ref["id"])


def test_pending_slice_retirement_preserves_history_and_other_uses(library, project):
    ref = slice_reference(library, project)
    other = library.create_project(ProjectInput(character="Other"))
    other_ref = library.add_candidate(other["id"], CandidateInput(asset_sha=ref["asset_sha"]))["reference"]
    before = library.reference(ref["id"])
    with library.db.read() as con:
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("refs", "aliases", "discoveries", "preflights", "assets")}
    assert retire_pending_slices(library, project["id"])["status"] == "dry_run"
    assert library.reference(ref["id"]) == before
    result = retire_pending_slices(library, project["id"], apply=True)
    assert result["reference_ids"] == [ref["id"]] and not result["reingested"]
    detached = library.reference(ref["id"])
    assert detached["detached_at"] and detached["decision"] == "pending"
    assert library.reference(other_ref["id"])["detached_at"] is None
    with library.db.read() as con:
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
        assert all(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == n for t, n in counts.items())
    assert retire_pending_slices(library, project["id"], apply=True)["reference_ids"] == []
    restored = library.restore_detached_reference(ref["id"], detached["revision"])
    assert restored["detached_at"] is None and restored["asset_sha"] == ref["asset_sha"]


def test_recovery_includes_wal_and_archives_exact_rows_without_touching_source(library, project, tmp_path):
    ref = slice_reference(library, project)
    with closing(sqlite3.connect(library.db.path)) as damaged:
        damaged.row_factory = sqlite3.Row
        damaged.execute("PRAGMA journal_mode=WAL")
        damaged.execute("DELETE FROM refs WHERE id=?", (ref["id"],))
        damaged.commit()
        issues = damaged.execute("PRAGMA foreign_key_check").fetchall()
        assert len(issues) == 3
        original_rows = {t: dict(damaged.execute(f"SELECT * FROM {t} WHERE rowid=?", (rowid,)).fetchone())
                         for t, rowid, _, _ in issues}
        report = recover_copy(library.db.path, tmp_path / "recovered")
        assert report["archived_rows"] == 3 and report["status"] == "recovered_copy"
        assert len(damaged.execute("PRAGMA foreign_key_check").fetchall()) == 3
        with pytest.raises(ValueError):
            retire_pending_slices(library, project["id"], apply=True)
    with closing(sqlite3.connect(report["recovered"])) as con:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not con.execute("PRAGMA foreign_key_check").fetchall()
        archived = [json.loads(r[0]) for r in con.execute(
            "SELECT data FROM events WHERE action='recovery.orphan_link_archived'")]
        assert {a["table"]: a["original_row"] for a in archived} == original_rows
        for table in ("discoveries", "preflights"):
            data = json.loads(con.execute(f"SELECT data FROM {table}").fetchone()[0])
            assert data["reference_id"] is None and data["orphaned_reference_id"] == ref["id"]
        assert con.execute("SELECT COUNT(*) FROM refs").fetchone()[0] == 0
    with closing(sqlite3.connect(report["before"])) as con:
        assert len(con.execute("PRAGMA foreign_key_check").fetchall()) == 3
    with pytest.raises(FileExistsError):
        recover_copy(library.db.path, tmp_path / "recovered")


def test_unknown_foreign_key_error_rolls_back_and_reports_failure(library, project, tmp_path):
    ref = slice_reference(library, project)
    with closing(sqlite3.connect(library.db.path)) as con, con:
        con.execute("DELETE FROM refs WHERE id=?", (ref["id"],))
        con.execute("CREATE TABLE unrelated (id TEXT REFERENCES projects(id))")
        con.execute("INSERT INTO unrelated VALUES ('missing-project')")
    output = tmp_path / "failed-recovery"
    with pytest.raises(ValueError, match="Unsupported foreign key"):
        recover_copy(library.db.path, output)
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "failed" and receipt["archived_rows"] == 0
    with closing(sqlite3.connect(output / "library.sqlite3")) as con:
        assert len(con.execute("PRAGMA foreign_key_check").fetchall()) == 4
        assert con.execute("SELECT COUNT(*) FROM events WHERE actor='recovery'").fetchone()[0] == 0


def test_backup_closes_handles_and_restores_hash_identical_assets(library, project, tmp_path):
    ref = slice_reference(library, project)
    result = backup(library, tmp_path / "full.zip")
    assert not result["secrets_included"]
    restored_dir = tmp_path / "restored"
    with zipfile.ZipFile(result["backup"]) as archive:
        assert "access-token" not in archive.namelist()
        archive.extractall(restored_dir)
    restored = Library(Settings(restored_dir, "isolated-regression-access-token"))
    assert doctor(restored)["ok"]
    assert restored.assets.path(ref["asset"]).read_bytes() == image_bytes()
    assert restored.reference(ref["id"])["revision"] == ref["revision"]
