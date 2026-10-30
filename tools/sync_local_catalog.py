"""Refresh the local, offline human-readable image catalogue."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ref_lab.local_catalog import CatalogError, refresh_catalog  # noqa: E402
from ref_lab.catalog_exports import export_character_catalog, load_export_settings, save_export_settings  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只读刷新 data/我的参考图")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--source-root", type=Path, action="append", default=[])
    parser.add_argument("--remember-inventory", action="store_true",
                        help="保存本次盘点输入与源边界，供以后双击刷新复用")
    parser.add_argument("--export-character", action="append", default=[],
                        help="导出该角色的全部派生 JPG；显式导出后保存设置，供普通刷新续用")
    parser.add_argument("--open", action="store_true", help="刷新后打开离线索引")
    args = parser.parse_args(argv)
    try:
        report = refresh_catalog(repo_root=args.repo_root, data_dir=args.data_dir,
                                 output=args.output, inventory=args.inventory,
                                 source_roots=args.source_root, remember_inventory=args.remember_inventory,
                                 log=lambda message: print(message, file=sys.stderr))
        catalog_root = Path(report["output"])
        characters = args.export_character or load_export_settings(catalog_root)
        exports = []
        if characters:
            data_dir = catalog_root.parent
            for character in characters:
                exports.append(export_character_catalog(catalog_root, data_dir, character))
            if args.export_character:
                save_export_settings(catalog_root, characters)
    except (CatalogError, OSError, ValueError) as exc:
        print(f"刷新未完成：{exc}", file=sys.stderr)
        return 1
    summary = report["summary"] if "summary" in report else {key: report[key] for key in
              ("images", "available", "missing_or_corrupt", "project_references", "projects", "roles", "unknown")}
    if exports:
        summary["exports"] = exports
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if report["errors"]:
        print(f"有 {len(report['errors'])} 项未能纳入或校验；详见 manifest.json 的 errors。", file=sys.stderr)
        for error in report["errors"][:20]:
            print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
    export_errors = [error for export in exports for error in export["errors"]]
    if export_errors:
        print(f"有 {len(export_errors)} 项导出文件被保留；详见各自导出目录的 manifest.json。", file=sys.stderr)
        for error in export_errors[:20]:
            print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
    index = Path(report["output"]) / "index.html"
    if args.open and index.is_file():
        if os.name == "nt":
            os.startfile(index)  # type: ignore[attr-defined]
        else:
            import webbrowser
            webbrowser.open(index.as_uri())
    return 0 if report["ok"] and all(export["ok"] for export in exports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
