"""Recover dangling Reference links in a new database copy, preserving exact old rows.

This produces database-only artifacts, not a full library backup or recovered human choices.
Run: python -m tools.recover_orphaned_references --source data/library.sqlite3 --output-dir NEW
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from ref_lab.db import Database, encode


def recover_copy(source: Path, output_dir: Path) -> dict:
    source = source.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    before = output_dir / "before.sqlite3"
    recovered = output_dir / "library.sqlite3"
    report = {"status": "failed", "source": str(source), "database_only": True,
              "before": str(before), "recovered": str(recovered), "archived_rows": 0}
    try:
        # SQLite's backup API includes committed WAL data; a file copy may lose it.
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original, \
                closing(sqlite3.connect(before)) as snapshot:
            original.backup(snapshot)
        report["before_sha256"] = hashlib.sha256(before.read_bytes()).hexdigest()
        with closing(sqlite3.connect(before)) as snapshot, closing(sqlite3.connect(recovered)) as con:
            snapshot.backup(con)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys=ON")
            with con:
                con.execute("BEGIN IMMEDIATE")
                if [r[0] for r in con.execute("PRAGMA integrity_check")] != ["ok"]:
                    raise ValueError("Structural database corruption; refusing automatic recovery")
                issues = [tuple(r) for r in con.execute("PRAGMA foreign_key_check")]
                report["foreign_keys_before"] = [list(r) for r in issues]
                columns = {"aliases": "ref_id", "discoveries": "reference_id", "preflights": "reference_id"}
                for table, rowid, parent, fk_id in issues:
                    if table not in columns or parent != "refs":
                        raise ValueError(f"Unsupported foreign key violation: {table} -> {parent}")
                    column = columns[table]
                    row = dict(con.execute(f"SELECT * FROM {table} WHERE rowid=?", (rowid,)).fetchone())
                    missing_id = row[column]
                    if not missing_id or con.execute("SELECT 1 FROM refs WHERE id=?", (missing_id,)).fetchone():
                        raise ValueError("Violation is not a missing Reference; refusing recovery")
                    Database.event(con, row.get("project_id"), missing_id, "recovery.orphan_link_archived",
                                   {"table": table, "rowid": rowid, "original_row": row}, actor="recovery")
                    if table == "aliases":
                        # NULL is invalid here. Exact old mapping stays in the event and snapshot.
                        con.execute("DELETE FROM aliases WHERE rowid=?", (rowid,))
                    else:
                        data = json.loads(row["data"])
                        data["orphaned_reference_id"] = missing_id
                        data["reference_id"] = None
                        con.execute(f"UPDATE {table} SET {column}=NULL,data=? WHERE rowid=?", (encode(data), rowid))
                    report["archived_rows"] += 1
                if con.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("Recovery left unresolved foreign key errors")
        report.update(status="recovered_copy", foreign_keys_after=[],
                      recovered_sha256=hashlib.sha256(recovered.read_bytes()).hexdigest())
        return report
    except Exception as exc:
        report.update(error=str(exc), archived_rows=0)
        raise
    finally:
        (output_dir / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing paths are refused")
    args = parser.parse_args()
    print(json.dumps(recover_copy(args.source, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
