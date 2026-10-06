"""Import a verified Dot Drive batch into the independent study queue.

Dry-run is the default. Raw index and image bytes stay in the private batch
directory; no user choice or Dot note is promoted to an image observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ref_lab.config import Settings
from ref_lab.db import now
from ref_lab.service import Library

BATCH_ID = "dot-drive-20261005"
TOPIC_WORDS = {
    "动作": ("姿", "手势", "手位", "腿", "脚", "重心", "肩", "胯", "站", "坐", "回望", "转身"),
    "光线": ("光", "影", "明暗", "轮廓光", "逆光"),
    "构图": ("构图", "机位", "景别", "画面", "裁切", "留白", "前景", "线条"),
    "环境": ("环境", "背景", "场景", "街道", "林间", "建筑", "空间"),
    "道具": ("道具", "持", "扶", "包", "伞", "书", "花", "剑"),
}


def safe_url(value: str) -> str:
    parsed = urlsplit(value or "")
    return value if parsed.scheme in {"https", "http"} and parsed.hostname else ""


def load_batch(batch_dir: Path) -> tuple[list[dict], dict[tuple[str, str], dict]]:
    source = json.loads((batch_dir / "index.json").read_text(encoding="utf-8"))
    works = source["主候选_待GPT二筛"]
    manifest = [json.loads(line) for line in (batch_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    by_work_file = {(item["number"], item["role"]): item for item in manifest}
    if len(works) != 238 or len(manifest) != 240 or len(by_work_file) != 240:
        raise ValueError("Dot batch is incomplete: expected 238 works and 240 files")
    if len({r["编号"] for r in works}) != 238 or any(r["编号"] == "P256" for r in works):
        raise ValueError("Duplicate ID or excluded P256 in the main batch")
    for record in works:
        number = record["编号"]
        for role, info in (("original", record), ("compatibility", record.get("兼容PNG预览_同一作品"))):
            if not info:
                continue
            entry = by_work_file.get((number, role))
            if not entry or entry["drive_id"] != info["Drive文件ID"]:
                raise ValueError(f"{number}: Drive file ID or role mismatch")
            path = Path(entry["path"])
            if not path.resolve().is_relative_to((batch_dir / "images").resolve()):
                raise ValueError(f"{number}: unsafe image path")
            blob = path.read_bytes()
            if len(blob) != info["文件大小_字节"] or hashlib.sha256(blob).hexdigest() != entry["sha256"]:
                raise ValueError(f"{number}: image bytes no longer match the audited manifest")
    return works, by_work_file


def candidate_data(record: dict, original_sha: str, compatibility_sha: str | None) -> dict:
    note = "\n".join(str(record.get(k, "")) for k in ("助手判断", "现场借鉴"))
    topics = [name for name, words in TOPIC_WORDS.items() if any(word in note for word in words)]
    number = record["编号"]
    timestamp = now()
    return {
        "id": "dot:" + number, "number": number, "batch_id": BATCH_ID,
        "asset_sha": original_sha, "compat_asset_sha": compatibility_sha,
        "original_file_id": record["Drive文件ID"],
        "compat_file_id": (record.get("兼容PNG预览_同一作品") or {}).get("Drive文件ID", ""),
        "received_name": record["图片文件名"], "title": record["主题"],
        "status": "pending", "decision_origin": "unreviewed", "human_note": "",
        "suggested_topics": topics, "topic_origin": "Dot 文案关键词，未逐图视觉复核",
        "source_page": safe_url(record.get("公开出处") or record.get("原帖") or ""),
        "source_image_url": safe_url(record.get("原图链接", "")),
        "drive_url": safe_url(record.get("Google Drive 图片", "")),
        "source_credit": "；".join(filter(None, [record.get("发布者"), record.get("模特署名"), record.get("摄影署名")])),
        "source_restrictions": record.get("作者与来源使用限制", []),
        "dot_notes": record.get("助手判断", ""), "dot_shooting_hint": record.get("现场借鉴", ""),
        "user_feedback_record": record.get("用户反馈", {}),
        "source_record": record, "revision": 1,
        "created_at": timestamp, "updated_at": timestamp,
    }


def make_backup(data_dir: Path, batch_dir: Path) -> Path:
    target_dir = batch_dir / "backups" / hashlib.sha256(str(data_dir).encode("utf-8")).hexdigest()[:12]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "library-before-dot.sqlite3"
    if target.exists():
        with sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True) as saved:
            if saved.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Existing pre-import backup failed integrity check")
        return target
    db_path = data_dir / "library.sqlite3"
    if not db_path.is_file():
        raise ValueError("Target library database is missing")
    with sqlite3.connect(db_path) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    batch_dir = args.batch_dir.resolve()
    data_dir = args.data_dir.resolve()
    works, entries = load_batch(batch_dir)
    print(json.dumps({"dry_run": not args.apply, "works": len(works), "files": len(entries),
                      "target": str(data_dir), "batch_id": BATCH_ID}, ensure_ascii=False), flush=True)
    if not args.apply:
        return 0
    backup = make_backup(data_dir, batch_dir)
    print(json.dumps({"backup": str(backup)}, ensure_ascii=False), flush=True)
    settings = Settings(data_dir=data_dir, token="local-import-token-placeholder-32-characters")
    library = Library(settings, repair_untrusted_preflights=False)
    log_path = batch_dir / "execution_log.jsonl"
    counts = {"created": 0, "existing": 0, "failed": 0}
    for record in works:
        number = record["编号"]
        try:
            primary = entries[(number, "original")]
            original = library.ingest_asset(Path(primary["path"]).read_bytes(), record["图片文件名"])
            compatibility_sha = None
            if record.get("兼容PNG预览_同一作品"):
                companion = entries[(number, "compatibility")]
                companion_asset = library.ingest_asset(Path(companion["path"]).read_bytes(),
                    record["兼容PNG预览_同一作品"]["图片文件名"])
                compatibility_sha = companion_asset["id"]
            result = library.add_study_candidate(candidate_data(record, original["id"], compatibility_sha))
            outcome = "created" if result["created"] else "existing"
            counts[outcome] += 1
            receipt = {"number": number, "status": outcome, "asset_sha": original["id"]}
        except Exception as exc:
            counts["failed"] += 1
            receipt = {"number": number, "status": "failed", "error": str(exc)[:300]}
        with log_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        if sum(counts.values()) % 20 == 0 or receipt["status"] == "failed":
            print(json.dumps({"progress": sum(counts.values()), **counts}, ensure_ascii=False), flush=True)
    print(json.dumps({"final": counts}, ensure_ascii=False), flush=True)
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
