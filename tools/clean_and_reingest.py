"""Retire pending collage slices recoverably; never delete or automatically re-ingest.

Run from the checkout: python -m tools.clean_and_reingest --help
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ref_lab.config import Settings
from ref_lab.models import ReferenceTransferInput
from ref_lab.service import Library


def retire_pending_slices(library: Library, project_id: str, *, apply: bool = False) -> dict:
    library.project(project_id)
    with library.db.read() as con:
        if con.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Database has foreign key errors; recover a copy before cleanup")
        rows = con.execute(
            "SELECT data FROM refs WHERE project_id=? AND decision='pending' "
            "AND json_extract(data,'$.detached_at') IS NULL "
            "AND json_extract(data,'$.title') LIKE '【动作#%'", (project_id,),
        ).fetchall()
    refs = [json.loads(row[0]) for row in rows]
    if len(refs) > 100:
        raise ValueError("More than 100 slices; review smaller batches before applying")
    if apply and refs:
        library.transfer_references(project_id, ReferenceTransferInput(
            mode="remove", items=[{"reference_id": r["id"], "expected_revision": r["revision"]} for r in refs],
        ))
    return {"status": "detached" if apply else "dry_run", "reference_ids": [r["id"] for r in refs],
            "reingested": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--apply", action="store_true", help="Detach through the service; recoverable in project recycle")
    args = parser.parse_args()
    if not (args.data_dir / "library.sqlite3").is_file():
        parser.error("Existing library.sqlite3 required; refusing to create an empty library")
    library = Library(Settings(args.data_dir.resolve(), "local-maintenance-no-network-access"))
    print(json.dumps(retire_pending_slices(library, args.project, apply=args.apply), ensure_ascii=False))


if __name__ == "__main__":
    main()
