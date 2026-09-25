"""Operational entry point for local Codex / Antigravity execution."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path
from .config import ROOT, Settings
from .db import encode
from .export import build_pack
from .imports import migrate_legacy
from .models import AnalysisResult, PackInput
from .policy import state_for
from .service import Library, Problem


def doctor(library: Library, repair_derived: bool = False) -> dict:
    report = {"database": "", "assets_checked": 0, "missing_or_corrupt": [], "missing_derivatives": [], "foreign_key_errors": [], "states_reindexed": 0}
    with library.db.read() as con:
        report["database"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        report["foreign_key_errors"] = [list(r) for r in con.execute("PRAGMA foreign_key_check")]
        assets = [json.loads(row[0]) for row in con.execute("SELECT data FROM assets")]
    for asset in assets:
        report["assets_checked"] += 1
        if not library.assets.verify(asset):
            report["missing_or_corrupt"].append(asset["id"])
        else:
            missing = [variant for variant in ("preview", "thumb") if not library.assets.path(asset, variant).is_file()]
            if missing:
                if repair_derived: library.assets.ingest(library.assets.path(asset).read_bytes(), asset["received_name"])
                else: report["missing_derivatives"].append({"sha": asset["id"], "variants": missing})
    with library.db.transaction() as con:
        corrupt = set(report["missing_or_corrupt"])
        for asset in assets:
            asset["integrity"] = "failed" if asset["id"] in corrupt else "ok"
            con.execute("UPDATE assets SET data=? WHERE id=?", (encode(asset), asset["id"]))
        refs = [json.loads(row[0]) for row in con.execute("SELECT data FROM refs")]
        for ref in refs:
            from .service import row_data
            project = row_data(con, "projects", ref["project_id"])
            state = state_for(ref, project, library._asset_exists(con, ref))
            if state != ref["state"]:
                if ref.get("asset_sha") in corrupt:
                    ref["accepted_fingerprint"] = None
                library._save(con, ref, project, "state.reindexed", {"state": state}, actor="doctor")
                report["states_reindexed"] += 1
    report["ok"] = report["database"] == "ok" and not any(report[k] for k in ("missing_or_corrupt", "missing_derivatives", "foreign_key_errors"))
    return report


def backup(library: Library, output: Path) -> dict:
    if output.exists(): raise ValueError("Backup destination already exists; refusing overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        snapshot = Path(temp) / "library.sqlite3"
        with library.db.read() as source, sqlite3.connect(snapshot) as destination:
            source.backup(destination)
        with sqlite3.connect(snapshot) as con:
            assets = [json.loads(row[0]) for row in con.execute("SELECT data FROM assets")]
        try:
            with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "library.sqlite3")
                for asset in assets:
                    if not library.assets.verify(asset): raise ValueError(f"Cannot back up corrupt or missing asset {asset['id']}")
                    for variant in ("original", "preview", "thumb"):
                        path = library.assets.path(asset, variant)
                        archive.write(path, str(path.relative_to(library.settings.data_dir)))
                archive.writestr("README.txt", "Private backup. Access tokens and provider secrets are intentionally excluded. Stop the server; restore only into a new, empty LAB_DATA_DIR, then run doctor before use.\n")
        except Exception:
            output.unlink(missing_ok=True)
            raise
    return {"backup": str(output.resolve()), "assets": len(assets), "secrets_included": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Photography Reference Lab")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run the private website")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--allow-remote", action="store_true")
    sub.add_parser("token", help="Print local access token; never commit this output")
    migrate = sub.add_parser("migrate-legacy")
    migrate.add_argument("--root", type=Path, default=ROOT / "references/changye-huansheng")
    migrate.add_argument("--project-id", default=None)
    check = sub.add_parser("doctor")
    check.add_argument("--repair-derived", action="store_true")
    save = sub.add_parser("backup")
    save.add_argument("--output", type=Path, required=True)
    export = sub.add_parser("export-pack")
    export.add_argument("--project", required=True)
    export.add_argument("--mode", choices=("field", "inspiration"), default="field")
    export.add_argument("--output", type=Path, required=True)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--job", required=True)
    analyze.add_argument("--confirm-external-images", action="store_true", help="Explicitly permit sending selected preview images to OpenAI API; API billing is separate")
    collect = sub.add_parser("collect")
    collect.add_argument("--job", required=True)
    collect.add_argument("--cdp", default="http://127.0.0.1:9222")
    collect.add_argument("--search", action="store_true", help="Navigate visible Pinterest search pages; otherwise capture the current page only")
    sync = sub.add_parser("sync-notion")
    sync.add_argument("--task", type=Path, required=True)
    sync.add_argument("--commit", default="")
    sub.add_parser("schema", help="Print analysis result JSON schema")
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.command == "token":
            print(settings.token)
            return 0
        if args.command == "schema":
            print(json.dumps(AnalysisResult.model_json_schema(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "serve":
            if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_remote:
                raise ValueError("Non-loopback binding requires --allow-remote and a protected deployment")
            if args.host not in {"127.0.0.1", "localhost", "::1"} and not os.environ.get("LAB_ACCESS_TOKEN"):
                raise ValueError("Remote binding requires an explicit LAB_ACCESS_TOKEN")
            import uvicorn
            from .api import create_app
            print(f"Private reference library: {settings.public_origin}")
            print("Unlock token: run `python -m ref_lab token` locally. Do not commit or publicly share it.")
            uvicorn.run(create_app(settings), host=args.host, port=args.port)
            return 0
        library = Library(settings)
        if args.command == "migrate-legacy": report = migrate_legacy(library, args.root, args.project_id)
        elif args.command == "doctor": report = doctor(library, args.repair_derived)
        elif args.command == "backup": report = backup(library, args.output)
        elif args.command == "export-pack":
            if args.output.exists(): raise ValueError("Output exists; refusing overwrite")
            result = build_pack(library, args.project, PackInput(mode=args.mode))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(result), str(args.output))
            report = {"pack": str(args.output.resolve())}
        elif args.command == "analyze":
            if not args.confirm_external_images:
                raise ValueError("分析会向 OpenAI API 发送所选图片。明确同意后添加 --confirm-external-images；不消耗 ChatGPT 对话额度，而是独立 API 计费。")
            from .providers import OpenAIAnalyzer, run_analysis_job
            analyzer = OpenAIAnalyzer(os.environ.get("OPENAI_API_KEY", ""), os.environ.get("LAB_ANALYSIS_MODEL", ""))
            report = run_analysis_job(library, args.job, analyzer)
        elif args.command == "collect":
            from .collector import collect_job
            report = collect_job(library, args.job, args.cdp, search=args.search)
        elif args.command == "sync-notion":
            from .providers import sync_task_to_notion
            report = sync_task_to_notion(args.task, settings.data_dir / "notion-receipts", args.commit)
        else: raise ValueError("Unknown command")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report.get("ok") is False or report.get("errors") else 0
    except (ValueError, OSError, Problem, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
