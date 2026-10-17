"""Bounded opt-in real searches for Learning V1; no production database access."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.learning_v1 import EXPERIMENT, ROOT, digest, save_json, stamp
from tools.collect_adapter import build_policy, build_queries, fetch_bsk_candidates


def run(task_file: Path, browser_id: str, bsk_path: Path) -> dict:
    task = json.loads(task_file.read_text(encoding="utf-8"))
    key = task["experiment_key"]
    if key not in {"zhaojun", "tohru", "ruby"}:
        raise ValueError("Unknown experiment key")
    if task.get("preferred_sources") != ["pinterest"]:
        raise ValueError("This runner uses the reviewed visible Pin adapter only; other sources need a separate explicit record")
    queries = build_queries(task, for_browser=True)
    if len(queries) + int(task.get("prior_discovery_queries", 0)) > 8:
        raise ValueError("Task would exceed eight primary queries")
    if key == "ruby":
        from tools.learning_v1 import check_freeze
        check_freeze()
    folder = EXPERIMENT / "search" / key
    folder.mkdir(parents=True, exist_ok=True)
    # Claim once before network work. A failed run is evidence, not a reason
    # to silently restart the query budget under the same identity.
    with (folder / "started.json").open("x", encoding="utf-8") as stream:
        json.dump({"at": stamp(), "task_digest": digest(task), "queries": queries}, stream, ensure_ascii=False)
    save_json(folder / "task.json", task)
    started = time.monotonic()
    candidates, images, query_log, _ = fetch_bsk_candidates(
        str(bsk_path), browser_id, task, min(20, int(task.get("target_count", 12))), build_policy(task))
    for filename, content in images.items():
        path = folder / "images" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    for item in candidates:
        original = folder / item["file"]
        item["asset_sha"] = hashlib.sha256(original.read_bytes()).hexdigest()
        item["original_path"] = str(original.resolve())
        item["review_status"] = "unreviewed"
    report = {"schema_version": 2, "experiment_key": key, "at": stamp(), "elapsed_seconds": round(time.monotonic()-started, 3),
              "adapter_sha256": hashlib.sha256((ROOT / "tools/collect_adapter.py").read_bytes()).hexdigest(),
              "candidate_count": len(candidates), "query_log": query_log,
              "query_count_including_prior": len(query_log)+int(task.get("prior_discovery_queries", 0)),
              "candidates": candidates, "status": "CANDIDATES_NEED_VISUAL_REVIEW" if candidates else "NO_CANDIDATES",
              "human_acceptance": "PENDING", "original_creator_verified": False}
    save_json(folder / "manifest.json", report)
    with zipfile.ZipFile(folder / "received.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(report, ensure_ascii=False, indent=2))
        for filename, content in images.items():
            archive.writestr("images/"+filename, content)
    return {k:v for k,v in report.items() if k != "candidates"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--bsk", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.task_file, args.browser, args.bsk), ensure_ascii=False, indent=2))
