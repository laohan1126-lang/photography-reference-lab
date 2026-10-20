"""Isolated re-verification of real collage batches.

For a private copy of a previous run directory this tool:

* re-processes every original with the **current** algorithm (the copy is
  disposable; original evidence directories are never touched),
* checks the original bytes still hash to their recorded SHA,
* checks every derived tile: parent binding, crop rectangle, size, file SHA,
  and that the tile pixels equal a fresh crop of the decoded original at the
  recorded rectangle,
* reports the canonical counts and any failure.

Usage:
    python -m tools.verify_collage_batches --batch DIR [--batch DIR ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from ref_lab import collage
from ref_lab.collection_counts import compute


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(run: Path, row: dict) -> Path:
    recorded = Path(str(row.get("original_path") or ""))
    try:
        if recorded.is_file() and _sha(recorded) == row.get("asset_sha"):
            return recorded
    except OSError:
        pass
    candidate = run / "images" / recorded.name
    if candidate.is_file() and _sha(candidate) == row.get("asset_sha"):
        return candidate
    raise SystemExit(f"找不到原始图片：{recorded}")


def _pixels_equal(tile_path: Path, original_path: Path, crop) -> tuple[bool, str]:
    try:
        with Image.open(original_path) as opened:
            opened.load()
            display = ImageOps.exif_transpose(opened).convert("RGB")
        left, top, width, height = (int(value) for value in crop)
        if left < 0 or top < 0 or width <= 0 or height <= 0:
            return False, "crop_rectangle_invalid"
        if left + width > display.width or top + height > display.height:
            return False, "crop_outside_original"
        expected = np.asarray(display.crop((left, top, left + width, top + height)))
        with Image.open(tile_path) as tile:
            tile.load()
            actual = np.asarray(tile.convert("RGB"))
    except (OSError, ValueError) as exc:
        return False, type(exc).__name__
    if expected.shape != actual.shape:
        return False, "pixel_shape_mismatch"
    return bool(np.array_equal(expected, actual)), "pixels_match" if np.array_equal(expected, actual) else "pixels_differ"


def verify_batch(run: Path) -> dict:
    run = run.resolve()
    received = json.loads((run / "received.json").read_text("utf-8-sig"))
    rows = received.get("candidates") if isinstance(received, dict) else received
    rows = list(rows or [])
    problems: list[dict] = []
    before: dict[str, str] = {}
    resolved = []
    for row in rows:
        path = _resolve(run, row)
        before[row["asset_sha"]] = _sha(path)
        row = {**row, "original_path": str(path)}
        resolved.append(row)
    records = {}
    for row in resolved:
        records[row["asset_sha"]] = collage.process_original(run, row)
    after = {}
    for row in resolved:
        path = Path(row["original_path"])
        after[row["asset_sha"]] = _sha(path)
        if before[row["asset_sha"]] != after[row["asset_sha"]]:
            problems.append({"asset_sha": row["asset_sha"], "problem": "original_changed"})
    items = []
    for row in resolved:
        record = records[row["asset_sha"]]
        original = Path(row["original_path"])
        tile_reports = []
        for index, child in enumerate(record.get("children") or [], 1):
            path = Path(child.get("path") or "")
            tile = {"index": index, "child_sha": child.get("child_sha"),
                    "crop": child.get("crop"), "size": child.get("size"),
                    "status": child.get("status")}
            if not path.is_file():
                tile["pixel_check"] = "missing_file"
                problems.append({"asset_sha": row["asset_sha"], "child_sha": child.get("child_sha"),
                                 "problem": "child_file_missing"})
            else:
                ok, reason = _pixels_equal(path, original, child.get("crop") or [])
                tile["pixel_check"] = reason
                if _sha(path) != child.get("child_sha"):
                    tile["pixel_check"] = "file_sha_mismatch"
                    ok = False
                if not ok:
                    problems.append({"asset_sha": row["asset_sha"],
                                     "child_sha": child.get("child_sha"), "problem": reason})
            tile_reports.append(tile)
        items.append({"asset_sha": row["asset_sha"], "status": record["status"],
                      "layout": record["layout"], "algorithm_version": record.get("algorithm_version"),
                      "original_size": record.get("original_size"), "children": tile_reports})
    counts = compute(run, resolved, records)
    return {"run": str(run), "items": items, "counts": counts,
            "problems": problems, "originals_unchanged": before == after}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    reports = [verify_batch(batch) for batch in args.batch]
    for report in reports:
        print(f"\n== {report['run']}")
        for item in report["items"]:
            valid = sum(1 for tile in item["children"] if tile["status"] == "valid")
            print(f"  {item['asset_sha'][:12]} {item['original_size']} {item['layout']:12s} "
                  f"{item['status']:16s} v{item['algorithm_version']} 子图 {len(item['children'])} 合格 {valid}")
        print("  counts:", json.dumps(report["counts"], ensure_ascii=False))
        print("  originals_unchanged:", report["originals_unchanged"],
              "problems:", len(report["problems"]))
        for problem in report["problems"][:10]:
            print("   !", problem)
    out = Path(args.batch[0]).resolve().parent / "verification.json"
    out.write_text(json.dumps(reports, ensure_ascii=False, indent=2), "utf8")
    print("\nreport:", out)
    failed = any(not report["originals_unchanged"] or report["problems"] for report in reports)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
