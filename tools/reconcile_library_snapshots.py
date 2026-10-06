#!/usr/bin/env python3
"""Conservatively reconcile two SQLite snapshots against their common base.

This utility operates directly on SQLite snapshots. It never opens the application
or its asset store, performs migrations, or mutates an input database.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any


class MergeError(Exception):
    pass


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"blob_hex": value.hex()}
    if isinstance(value, float):
        return {"float_hex": value.hex()}
    return value


def json_key(key: tuple[Any, ...]) -> Any:
    values = [json_value(item) for item in key]
    return values[0] if len(values) == 1 else values


def value_token(value: Any) -> bytes:
    return json.dumps(json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class TableData:
    name: str
    create_sql: str
    columns: tuple[str, ...]
    column_signature: tuple[tuple[Any, ...], ...]
    primary_key: tuple[str, ...]
    rows: dict[tuple[Any, ...], tuple[Any, ...]]
    order: list[tuple[Any, ...]]
    rowids: dict[tuple[Any, ...], int | None]


class Snapshot:
    def __init__(self, label: str, path: Path):
        self.label = label
        self.path = path
        self.con: sqlite3.Connection | None = None
        self.user_version = 0
        self.objects: dict[tuple[str, str], tuple[str, str | None]] = {}
        self.tables: dict[str, TableData] = {}
        self.foreign_key_errors: Counter[tuple[Any, ...]] = Counter()
        self.fingerprint = ""

    def open(self) -> "Snapshot":
        if not self.path.is_file():
            raise MergeError(f"{self.label} input database is unavailable")
        try:
            uri = self.path.resolve().as_uri() + "?mode=ro"
            self.con = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=15)
            self.con.execute("PRAGMA query_only=ON")
            self.con.execute("BEGIN")
            # Establish the read snapshot before inspecting schema or data.
            self.con.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
            self.user_version = int(self.con.execute("PRAGMA user_version").fetchone()[0])
            self._read_objects()
            self._read_tables()
            self.foreign_key_errors = Counter(tuple(row) for row in self.con.execute("PRAGMA foreign_key_check"))
            self.fingerprint = self._fingerprint()
            return self
        except MergeError:
            self.close()
            raise
        except (sqlite3.Error, OSError, ValueError) as exc:
            self.close()
            raise MergeError(f"{self.label} input is not a readable SQLite snapshot ({type(exc).__name__})") from exc

    def _read_objects(self) -> None:
        assert self.con is not None
        for kind, name, table_name, sql in self.con.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE type IN ('table','index','view','trigger') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type,name"
        ):
            self.objects[(kind, name)] = (table_name, sql)

    def _read_tables(self) -> None:
        assert self.con is not None
        for (kind, name), (_, create_sql) in self.objects.items():
            if kind != "table":
                continue
            if not create_sql or create_sql.lstrip().upper().startswith("CREATE VIRTUAL TABLE"):
                raise MergeError(f"unsupported virtual table: {name}")
            quoted = quote_ident(name)
            info = list(self.con.execute(f"PRAGMA table_info({quoted})"))
            xinfo = list(self.con.execute(f"PRAGMA table_xinfo({quoted})"))
            if any(len(row) > 6 and row[6] for row in xinfo):
                raise MergeError(f"unsupported hidden/generated column in table {name}")
            pk_info = sorted((row[5], row[1]) for row in info if row[5])
            primary_key = tuple(column for _, column in pk_info)
            if not primary_key:
                raise MergeError(f"table {name} has no primary key")
            columns = tuple(row[1] for row in info)
            signature = tuple(tuple(row[1:6]) for row in info)
            rows: dict[tuple[Any, ...], tuple[Any, ...]] = {}
            order: list[tuple[Any, ...]] = []
            rowids: dict[tuple[Any, ...], int | None] = {}
            try:
                cursor = self.con.execute(f"SELECT _rowid_,* FROM {quoted} ORDER BY _rowid_")
                source_rows = ((int(record[0]), tuple(record[1:])) for record in cursor)
            except sqlite3.OperationalError:
                ordered = ",".join(quote_ident(column) for column in primary_key)
                cursor = self.con.execute(f"SELECT * FROM {quoted} ORDER BY {ordered}")
                source_rows = ((None, tuple(record)) for record in cursor)
            indexes = [columns.index(column) for column in primary_key]
            for rowid, row in source_rows:
                key = tuple(row[index] for index in indexes)
                if any(value is None for value in key):
                    raise MergeError(f"table {name} contains a null primary key")
                if key in rows:
                    raise MergeError(f"table {name} contains a duplicate primary key")
                rows[key] = row
                order.append(key)
                rowids[key] = rowid
            self.tables[name] = TableData(name, create_sql, columns, signature, primary_key, rows, order, rowids)

    def _fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(f"user_version:{self.user_version}\n".encode())
        for (kind, name), (table, sql) in sorted(self.objects.items()):
            for item in (kind, name, table, sql or ""):
                digest.update(value_token(item) + b"\0")
        for name, table in sorted(self.tables.items()):
            digest.update(value_token(name) + b"\n")
            for key in sorted(table.rows, key=lambda candidate: tuple(value_token(v) for v in candidate)):
                digest.update(value_token(table.rowids[key]) + b"\0")
                digest.update(value_token(key) + b"\0")
                for value in table.rows[key]:
                    digest.update(value_token(value) + b"\0")
                digest.update(b"\n")
        return digest.hexdigest()

    def close(self) -> None:
        if self.con is not None:
            try:
                self.con.rollback()
            except sqlite3.Error:
                pass
            self.con.close()
            self.con = None


def table_info_signature(snapshot: Snapshot, name: str) -> tuple[tuple[Any, ...], ...] | None:
    table = snapshot.tables.get(name)
    return table.column_signature if table else None


def conflict(report: dict[str, Any], kind: str, table: str | None = None, key: tuple[Any, ...] | None = None,
             detail: str | None = None) -> None:
    item: dict[str, Any] = {"kind": kind}
    if table is not None:
        item["table"] = table
    if key is not None:
        item["key"] = json_key(key)
    if detail:
        item["detail"] = detail
    report["conflicts"].append(item)


def content_without_id(table: TableData, row: tuple[Any, ...]) -> tuple[Any, ...]:
    index = table.columns.index("id")
    return row[:index] + row[index + 1 :]


def analyze(base: Snapshot, current: Snapshot, incoming: Snapshot) -> tuple[dict[str, Any], dict[str, Any]]:
    report: dict[str, Any] = {
        "status": "analyzing",
        "inputs": {
            label: {"snapshot_sha256": snap.fingerprint, "user_version": snap.user_version,
                    "table_counts": {name: len(table.rows) for name, table in sorted(snap.tables.items())}}
            for label, snap in (("base", base), ("current", current), ("incoming", incoming))
        },
        "result": {"user_version": current.user_version},
        "tables": {},
        "conflicts": [],
        "event_id_map": {},
    }
    schema_plan: dict[str, Any] = {
        "create_tables": [], "create_indexes": [], "rows": {}, "events": [],
        "columns": {}, "primary_keys": {},
    }

    all_table_names = set(base.tables) | set(current.tables) | set(incoming.tables)
    for name in sorted(all_table_names):
        present = [snapshot for snapshot in (base, current, incoming) if name in snapshot.tables]
        for left_index, left in enumerate(present):
            for right in present[left_index + 1 :]:
                if table_info_signature(left, name) != table_info_signature(right, name):
                    conflict(report, "table_columns_mismatch", name, detail=f"{left.label} vs {right.label}")

    # The current database defines the resulting schema. An incoming snapshot
    # may contribute only objects it added after the common baseline.
    for name in sorted(base.tables):
        if name not in incoming.tables:
            conflict(report, "schema_deletion", name, detail="incoming removed a baseline table")
        if name not in current.tables:
            conflict(report, "current_schema_missing", name, detail="current removed a baseline table")
    for name in sorted(incoming.tables.keys() - base.tables.keys()):
        incoming_table = incoming.tables[name]
        current_table = current.tables.get(name)
        if current_table is None:
            schema_plan["create_tables"].append(incoming_table.create_sql)

    schema_kinds = ("view", "trigger")
    for kind in schema_kinds:
        baseline_names = {name for object_kind, name in base.objects if object_kind == kind}
        current_names = {name for object_kind, name in current.objects if object_kind == kind}
        incoming_names = {name for object_kind, name in incoming.objects if object_kind == kind}
        for name in sorted(baseline_names - incoming_names):
            conflict(report, "schema_deletion", name, detail=f"incoming removed a baseline {kind}")
        for name in sorted(incoming_names - baseline_names):
            conflict(report, "unsupported_schema_object", name, detail=f"incoming added a {kind}; only tables and indexes may be added")
        for name in sorted(incoming_names & baseline_names):
            if incoming.objects[(kind, name)][1] != base.objects[(kind, name)][1]:
                conflict(report, "schema_change", name, detail=f"incoming changed a baseline {kind}")
        for name in sorted(current_names & baseline_names):
            if current.objects[(kind, name)][1] != base.objects[(kind, name)][1]:
                conflict(report, "schema_change", name, detail=f"current changed a baseline {kind}")

    base_indexes = {name: data for (kind, name), data in base.objects.items() if kind == "index"}
    current_indexes = {name: data for (kind, name), data in current.objects.items() if kind == "index"}
    incoming_indexes = {name: data for (kind, name), data in incoming.objects.items() if kind == "index"}
    for name in sorted(base_indexes.keys() - incoming_indexes.keys()):
        conflict(report, "schema_deletion", name, detail="incoming removed a baseline index")
    for name in sorted(base_indexes.keys() & incoming_indexes.keys()):
        if base_indexes[name][1] != incoming_indexes[name][1]:
            conflict(report, "schema_change", name, detail="incoming changed a baseline index")
    for name in sorted(current_indexes.keys() & incoming_indexes.keys()):
        if current_indexes[name][1] != incoming_indexes[name][1]:
            conflict(report, "schema_change", name, detail="incoming index conflicts with current schema")
    for name in sorted(incoming_indexes.keys() - base_indexes.keys()):
        table_name, sql = incoming_indexes[name]
        if not sql:
            continue
        if name not in current_indexes:
            if table_name not in current.tables and table_name not in incoming.tables:
                conflict(report, "index_table_missing", name)
            else:
                schema_plan["create_indexes"].append(sql)

    # Triggers in current can mutate unrelated rows as a side effect of direct
    # inserts/updates; refuse rather than invoking application-like behavior.
    if any(kind == "trigger" for kind, _ in current.objects):
        conflict(report, "unsupported_current_trigger", detail="current database contains triggers")

    for name in sorted(all_table_names):
        base_table = base.tables.get(name)
        current_table = current.tables.get(name)
        incoming_table = incoming.tables.get(name)
        b_rows = base_table.rows if base_table else {}
        c_rows = current_table.rows if current_table else {}
        i_rows = incoming_table.rows if incoming_table else {}
        table_report = {
            "base_rows": len(b_rows), "current_rows": len(c_rows), "incoming_rows": len(i_rows),
            "incoming_rows_added": 0, "incoming_rows_updated": 0, "incoming_rows_unchanged": 0,
        }
        report["tables"][name] = table_report
        if name == "events":
            if not (base_table and current_table and incoming_table):
                # New/current-only event tables are handled below when all
                # present schemas have the standard append-only primary key.
                pass
            if incoming_table is None:
                continue
            if incoming_table.primary_key != ("id",) or "id" not in incoming_table.columns:
                conflict(report, "invalid_events_schema", name, detail="events must have a single id primary key")
                continue
            id_column = incoming_table.columns.index("id")
            id_info = next(row for row in incoming.con.execute(f"PRAGMA table_info({quote_ident(name)})") if row[1] == "id")
            if str(id_info[2]).strip().upper() != "INTEGER":
                conflict(report, "invalid_events_schema", name, detail="events.id must be INTEGER")
                continue
            # Existing history on both branches is immutable, including every
            # baseline event. Deletions were already recorded below.
            for key, base_row in b_rows.items():
                current_row, incoming_row = c_rows.get(key), i_rows.get(key)
                if current_row is not None and current_row != base_row:
                    conflict(report, "event_mutation", name, key, "current changed a baseline event")
                if incoming_row is not None and incoming_row != base_row:
                    conflict(report, "event_mutation", name, key, "incoming changed a baseline event")
            # Match incoming additions one-to-one against current additions of
            # identical content. This makes a repeated merge idempotent without
            # collapsing multiple legitimate identical events in either branch.
            current_by_content: dict[tuple[Any, ...], list[int]] = {}
            for key, row in c_rows.items():
                if key in b_rows:
                    continue
                event_id = row[id_column]
                current_by_content.setdefault(content_without_id(current_table or incoming_table, row), []).append(int(event_id))
            current_content_offsets: dict[tuple[Any, ...], int] = {}
            next_id = max((int(row[id_column]) for row in c_rows.values()), default=0) + 1
            event_operations = []
            for source_key in incoming_table.order:
                row = i_rows[source_key]
                source_id = int(row[id_column])
                if source_key in b_rows:
                    continue
                content = content_without_id(incoming_table, row)
                candidates = current_by_content.get(content, [])
                offset = current_content_offsets.get(content, 0)
                if offset < len(candidates):
                    target_id = candidates[offset]
                    current_content_offsets[content] = offset + 1
                    report["event_id_map"][str(source_id)] = target_id
                    table_report["incoming_rows_unchanged"] += 1
                    continue
                target_id = next_id
                next_id += 1
                new_row = row[:id_column] + (target_id,) + row[id_column + 1 :]
                event_operations.append((source_id, target_id, new_row))
                report["event_id_map"][str(source_id)] = target_id
                table_report["incoming_rows_added"] += 1
            schema_plan["events"] = event_operations
            continue

        if incoming_table is None:
            continue
        row_actions: dict[tuple[Any, ...], tuple[str, tuple[Any, ...]]] = {}
        for key, incoming_row in i_rows.items():
            base_row = b_rows.get(key)
            current_row = c_rows.get(key)
            if base_row is None:
                if current_row is None:
                    row_actions[key] = ("insert", incoming_row)
                    table_report["incoming_rows_added"] += 1
                elif current_row == incoming_row:
                    table_report["incoming_rows_unchanged"] += 1
                else:
                    conflict(report, "primary_key_collision", name, key)
                continue
            if current_row is None:
                continue  # A deletion conflict was already recorded.
            if incoming_row == base_row:
                table_report["incoming_rows_unchanged"] += 1
            elif current_row == base_row:
                row_actions[key] = ("update", incoming_row)
                table_report["incoming_rows_updated"] += 1
            elif current_row == incoming_row:
                table_report["incoming_rows_unchanged"] += 1
            else:
                conflict(report, "row_conflict", name, key)
        if row_actions:
            ordered_actions = [(key, *row_actions[key]) for key in incoming_table.order if key in row_actions]
            schema_plan["rows"][name] = ordered_actions

    # Any baseline row absent from either descendant is a hard stop. This also
    # catches append-only event deletions before their merge logic runs.
    for name, base_table in sorted(base.tables.items()):
        current_table = current.tables.get(name)
        incoming_table = incoming.tables.get(name)
        if current_table is None or incoming_table is None:
            continue
        for key in base_table.rows:
            if key not in current_table.rows:
                conflict(report, "row_deletion", name, key, "current deleted a baseline row")
            if key not in incoming_table.rows:
                conflict(report, "row_deletion", name, key, "incoming deleted a baseline row")

    report["current_foreign_key_violation_count"] = sum(current.foreign_key_errors.values())
    return report, schema_plan


def equivalent_paths(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(str(right.resolve(strict=False)))


def validate_output_path(output: Path, inputs: tuple[Path, ...]) -> Path:
    resolved = output.resolve(strict=False)
    if any(equivalent_paths(resolved, source) for source in inputs):
        raise MergeError("output path must not replace an input database")
    if os.path.lexists(resolved):
        raise MergeError("output path already exists")
    if not resolved.parent.is_dir():
        raise MergeError("output directory does not exist")
    return resolved


def apply_plan(current: Snapshot, base: Snapshot, report: dict[str, Any], plan: dict[str, Any], output: Path) -> None:
    resolved = validate_output_path(output, (base.path, current.path))
    # The incoming source is checked by the caller before this point.
    fd, temp_name = tempfile.mkstemp(prefix=f".{resolved.name}.merge-", suffix=".sqlite3", dir=resolved.parent)
    os.close(fd)
    temporary = Path(temp_name)
    destination: sqlite3.Connection | None = None
    try:
        assert current.con is not None
        destination = sqlite3.connect(temporary, timeout=15)
        current.con.backup(destination)
        destination.close()
        destination = None

        destination = sqlite3.connect(temporary, timeout=15)
        destination.execute("PRAGMA foreign_keys=OFF")
        destination.execute("BEGIN IMMEDIATE")
        for sql in plan["create_tables"]:
            destination.execute(sql)

        # Insert/update rows in source rowid order. Some readers use rowid as
        # the stable tie-breaker for observations written by the same actor.
        for table_name, actions in sorted(plan["rows"].items()):
            table = next((snapshot.tables.get(table_name) for snapshot in (current,) if table_name in snapshot.tables), None)
            if table is None:
                # Newly added table schema is taken from incoming; column order
                # is captured in the plan at analysis time below.
                columns = plan["columns"][table_name]
                primary_key = plan["primary_keys"][table_name]
            else:
                columns, primary_key = table.columns, table.primary_key
            quoted_table = quote_ident(table_name)
            quoted_columns = ",".join(quote_ident(column) for column in columns)
            placeholders = ",".join("?" for _ in columns)
            pk_where = " AND ".join(f"{quote_ident(column)}=?" for column in primary_key)
            for key, action, row in actions:
                if action == "insert":
                    destination.execute(f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})", row)
                else:
                    assignments = ",".join(f"{quote_ident(column)}=?" for column in columns)
                    destination.execute(
                        f"UPDATE {quoted_table} SET {assignments} WHERE {pk_where}",
                        row + tuple(key),
                    )

        event_columns = plan["columns"].get("events")
        if plan["events"]:
            if event_columns is None:
                event_columns = current.tables["events"].columns
            quoted_columns = ",".join(quote_ident(column) for column in event_columns)
            placeholders = ",".join("?" for _ in event_columns)
            for _, _, row in plan["events"]:
                destination.execute(f"INSERT INTO {quote_ident('events')} ({quoted_columns}) VALUES ({placeholders})", row)

        for sql in plan["create_indexes"]:
            destination.execute(sql)

        destination.execute(f"PRAGMA user_version={current.user_version}")
        destination.commit()
        destination.execute("PRAGMA foreign_keys=ON")
        integrity = [row[0] for row in destination.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise MergeError("output integrity_check did not return ok")
        output_foreign_keys = Counter(tuple(row) for row in destination.execute("PRAGMA foreign_key_check"))
        for violation, count in output_foreign_keys.items():
            if count > current.foreign_key_errors.get(violation, 0):
                raise MergeError("foreign key violations increased in output")
        report["result"].update({
            "user_version": int(destination.execute("PRAGMA user_version").fetchone()[0]),
            "integrity_check": "ok",
            "foreign_key_violation_count": sum(output_foreign_keys.values()),
        })
        destination.close()
        destination = None

        if os.name == "nt":
            # Windows rename fails rather than replacing an existing file.
            os.rename(temporary, resolved)
        else:
            # A hard link gives POSIX the same atomic no-clobber publication.
            os.link(temporary, resolved)
            temporary.unlink()
        report["result"]["output_created"] = True
    except Exception:
        if destination is not None:
            try:
                destination.rollback()
            except sqlite3.Error:
                pass
            destination.close()
        for candidate in (temporary, Path(str(temporary) + "-journal"), Path(str(temporary) + "-wal"), Path(str(temporary) + "-shm")):
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def run(base_path: Path, current_path: Path, incoming_path: Path, apply: bool,
        output_path: Path | None) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "failed", "conflicts": [], "tables": {}, "event_id_map": {}}
    base = current = incoming = None
    try:
        base = Snapshot("base", base_path).open()
        current = Snapshot("current", current_path).open()
        incoming = Snapshot("incoming", incoming_path).open()
        report, plan = analyze(base, current, incoming)
        # Metadata needed when a table itself is incoming-only.
        for snapshot in (base, current, incoming):
            for name, table in snapshot.tables.items():
                plan["columns"][name] = table.columns
                plan["primary_keys"][name] = table.primary_key
        if report["conflicts"]:
            report["status"] = "conflict"
            return report
        if not apply:
            report["status"] = "dry_run_clean"
            return report
        if output_path is None:
            raise MergeError("--apply requires --output")
        validate_output_path(output_path, (base_path, current_path, incoming_path))
        apply_plan(current, base, report, plan, output_path)
        report["status"] = "applied"
        return report
    except MergeError as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        return report
    except (sqlite3.Error, OSError) as exc:
        report["status"] = "failed"
        report["error"] = f"database reconciliation failed ({type(exc).__name__})"
        return report
    finally:
        for snapshot in (incoming, current, base):
            if snapshot is not None:
                snapshot.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="shared baseline SQLite snapshot")
    parser.add_argument("--current", type=Path, required=True, help="snapshot whose contents/schema are retained")
    parser.add_argument("--incoming", type=Path, required=True, help="snapshot whose independent changes are merged")
    parser.add_argument("--output", type=Path, help="new output path; never replaces a file")
    parser.add_argument("--apply", action="store_true", help="create output after a clean full comparison")
    parser.add_argument("--report", type=Path, help="write the JSON report to this path")
    args = parser.parse_args(argv)
    if args.report and any(equivalent_paths(args.report, path) for path in (args.base, args.current, args.incoming, args.output) if path):
        report = {"status": "failed", "error": "report path must not overlap an input or output database"}
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    report = run(args.base, args.current, args.incoming, args.apply, args.output)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(rendered + "\n", encoding="utf-8")
        except OSError:
            print("could not write report file", file=sys.stderr)
            return 2
    return 0 if report["status"] in {"dry_run_clean", "applied"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
