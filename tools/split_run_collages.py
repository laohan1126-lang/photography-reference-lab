"""Offline collage-splitting audit over an existing collection run.

Reads the originals already received by a previous real run (never the network,
never a model), runs the deterministic local splitter, and writes a private report
plus derived tiles. The originals are only read: their SHA is re-checked before
and after.

    python -m tools.split_run_collages --run .local/run-15-20261020-evidence
    python -m tools.split_run_collages --run ... --repeat   # prove idempotency

Outputs (inside the run directory):
    derived/<child_sha>.png     lossless crops, content addressed
    derived.json                one record per parent_sha
    collage-report.json         machine readable audit
    collage-report.html         human readable side-by-side view
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ref_lab.collage import (STATUS_NO_COLLAGE, DerivedStore, process_original,  # noqa: E402
                             summarize_records)

STATUS_LABELS = {
    "no_collage": "单图（不拆分）",
    "split_ok": "拆分成功（全部子图合格）",
    "split_partial": "部分成功（保留合格子图）",
    "needs_manual_crop": "待人工裁切（规则不可靠）",
    "low_resolution": "子图全部低画质（拒绝交付）",
    "duplicate_only": "子图全部与历史重复（不重复计数）",
    "failed": "处理失败（原图保留）",
}


def load_received(run: Path) -> list[dict]:
    path = run / "received.json"
    if not path.is_file():
        raise SystemExit(f"缺少 {path}")
    data = json.loads(path.read_text("utf-8-sig"))
    rows = data.get("candidates") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise SystemExit("received.json 结构不可识别")
    return rows


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_original(run: Path, row: dict) -> tuple[Path, bool]:
    """Return the original file for a recorded row.

    A private evidence copy can move the run directory, so a recorded absolute
    path may no longer exist. Falling back to ``images/<same name>`` is safe: the
    file is only accepted when its content hash equals the recorded ``asset_sha``.
    """
    recorded = Path(str(row.get("original_path") or ""))
    try:
        inside = recorded.resolve().is_relative_to((run / "images").resolve())
    except (OSError, RuntimeError):
        inside = False
    try:
        if inside and recorded.is_file() and sha_of(recorded) == str(row.get("asset_sha")):
            return recorded, False
    except (OSError, PermissionError):
        pass
    candidate = run / "images" / recorded.name
    try:
        if candidate.is_file() and sha_of(candidate) == str(row.get("asset_sha")):
            return candidate, True
    except (OSError, PermissionError):
        pass
    raise SystemExit(f"找不到原始图片：{recorded}")


def render_html(report: dict, run: Path) -> str:
    parts = []
    for item in report["items"]:
        parent = Path(item["original_path"])
        child_cards = []
        for index, child in enumerate(item.get("children", []), 1):
            quality = child.get("quality") or {}
            rel = Path(child["path"]).name
            child_cards.append(
                f'<figure><img src="derived/{rel}" alt="子图{index}">'
                f'<figcaption>#{index} · {child["size"][0]}×{child["size"][1]} · '
                f'裁切 x{child["crop"][0]} y{child["crop"][1]} w{child["crop"][2]} h{child["crop"][3]} · '
                f'清晰度 {quality.get("sharpness")} · {child["status"]}'
                f'{(" · 与历史重复 " + str(child.get("duplicate_of"))[:12]) if child.get("duplicate_of") else ""}'
                f'</figcaption></figure>')
        parts.append(
            f'<section><h2>{item["index"]:02d} · {item["sha"][:16]} · {STATUS_LABELS.get(item["status"], item["status"])}</h2>'
            f'<p>原图 {item["original_size"][0]}×{item["original_size"][1]} · 布局 {item["layout"]} · '
            f'检测 {item["rows"]}×{item["cols"]} · 子图 {len(item.get("children", []))} 张 · '
            f'耗时 {item["elapsed_seconds"]} 秒 · SHA 未改变 {item["sha_unchanged"]} · {item.get("reason", "")}</p>'
            f'<div class="pair"><figure><img src="{item["gallery_name"]}" alt="原图"><figcaption>原图（不覆盖、不删除）</figcaption></figure>'
            f'<div class="children">{"".join(child_cards) or "<p>没有生成子图</p>"}</div></div></section>')
    totals = report["totals"]
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>拼图离线验收</title><style>'
            'body{margin:0;background:#f4f2ec;color:#232721;font:15px/1.6 system-ui}'
            'main{max-width:1200px;margin:auto;padding:24px}h1{font-size:26px}'
            'section{border-top:1px solid #cbc6ba;padding:22px 0}'
            '.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:18px}'
            '.children{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;align-content:start}'
            'figure{margin:0}img{display:block;max-width:100%;max-height:70vh;margin:auto;background:#ddd}'
            '.children img{max-height:220px}figcaption{font-size:12px;color:#41463f;padding-top:4px}'
            'a{color:#1f5c42}</style><main><h1>拼图离线验收 · ' + str(len(report["items"])) + ' 张原图</h1>'
            '<p>只读旧运行目录的原图；原图字节与 SHA 不变，派生图是无损 PNG 裁切。'
            '低画质子图已拒绝，原图与其子图不会同时计入可用照片。</p>'
            f'<p>总计：拼图 {totals["collages"]} 张，有效子图 {totals["derived_valid"]} 张，'
            f'拒绝子图 {totals["derived_rejected"]} 张，重复子图 {totals["derived_duplicate"]} 张，'
            f'待人工裁切 {totals["collage_needs_manual"]} 张。</p>'
            + ''.join(parts) + '</main></html>')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="run directory with images/ and received.json")
    parser.add_argument("--repeat", action="store_true", help="process twice and report idempotency")
    parser.add_argument("--gallery", action="store_true", help="copy originals into gallery/ for the HTML report")
    parser.add_argument("--only", nargs="*", default=[], help="restrict to these SHA prefixes")
    args = parser.parse_args(argv)
    run = args.run.resolve()
    rows = load_received(run)
    if args.only:
        rows = [row for row in rows if any(str(row["asset_sha"]).startswith(prefix) for prefix in args.only)]
    resolved = {}
    for row in rows:
        path, remapped = resolve_original(run, row)
        row["original_path"] = str(path)
        resolved[row["asset_sha"]] = remapped
    before = {row["asset_sha"]: sha_of(Path(row["original_path"])) for row in rows}
    existing_files = {path.name for path in (run / "derived").glob("*.png")} if (run / "derived").is_dir() else set()

    def one_pass() -> list[dict]:
        items = []
        for index, row in enumerate(rows, 1):
            started = time.monotonic()
            record = process_original(run, row)
            elapsed = time.monotonic() - started
            gallery = ""
            if args.gallery:
                target = run / "gallery" / Path(row["original_path"]).name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copyfile(row["original_path"], target)
                gallery = target.name
            items.append({
                "index": index, "sha": row["asset_sha"], "original_path": str(row["original_path"]),
                "gallery_name": gallery,
                "path_remapped": bool(resolved.get(row["asset_sha"])),
                "status": record["status"], "layout": record["layout"],
                "rows": record["rows"], "cols": record["cols"],
                "original_size": record["original_size"], "reason": record.get("reason", ""),
                "elapsed_seconds": record["elapsed_seconds"],
                "children": [{key: value for key, value in child.items() if key not in {"_image"}}
                             for child in record.get("children", [])],
                "reused": bool(record.get("reused")),
                "wall_seconds": round(elapsed, 3),
            })
        return items

    first = one_pass()
    second = []
    if args.repeat:
        second = one_pass()
    after = {row["asset_sha"]: sha_of(Path(row["original_path"])) for row in rows}
    for item in first:
        item["sha_unchanged"] = before.get(item["sha"]) == after.get(item["sha"])
        item["sha_after"] = after.get(item["sha"], "")
    after_files = {path.name for path in (run / "derived").glob("*.png")}
    records = DerivedStore(run).items()
    totals = summarize_records(records)
    report = {
        "run": str(run),
        "generated_at": time.time(),
        "items": first,
        "totals": totals,
        "originals_unchanged": before == after,
        "derived_files_before": len(existing_files),
        "derived_files_after": len(after_files),
        "repeat": {
            "enabled": bool(args.repeat),
            "all_reused": all(item["reused"] for item in second) if second else None,
            "same_child_count": ([len(item["children"]) for item in second] == [len(item["children"]) for item in first]
                                 if second else None),
            "derived_files_after_repeat": len({path.name for path in (run / "derived").glob("*.png")})
            if args.repeat else None,
        },
    }
    (run / "collage-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf8")
    (run / "collage-report.html").write_text(render_html(report, run), "utf8")
    for item in first:
        children = item["children"]
        usable = sum(1 for child in children if child["status"] == "valid")
        print(f'{item["index"]:02d} {item["sha"][:12]} {item["original_size"][0]}x{item["original_size"][1]} '
              f'{item["layout"]:12s} {STATUS_LABELS.get(item["status"], item["status"])} '
              f'子图 {len(children)} 合格 {usable} 耗时 {item["elapsed_seconds"]:.3f}s')
        for child in children:
            print(f'     child {child["child_sha"][:12]} crop={child["crop"]} size={child["size"]} '
                  f'sharp={child["quality"]["sharpness"]} status={child["status"]}')
    print("\n总计：", json.dumps(totals, ensure_ascii=False))
    print("原图不变：", report["originals_unchanged"],
          "· 派生文件：", report["derived_files_before"], "→", report["derived_files_after"])
    if args.repeat:
        print("重复执行全部复用：", report["repeat"]["all_reused"],
              "· 子图数量一致：", report["repeat"]["same_child_count"],
              "· 派生文件：", report["repeat"]["derived_files_after_repeat"])
    return 0 if report["originals_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
