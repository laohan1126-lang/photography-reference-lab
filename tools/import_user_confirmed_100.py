#!/usr/bin/env python3
"""Batch import the 100 human-confirmed aesthetic reference photos into the owner's personal library.
Preserves original bytes, source provenance, human choices, and intent history.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

# Ensure LAB_DATA_DIR is configured
if not os.environ.get("LAB_DATA_DIR"):
    os.environ["LAB_DATA_DIR"] = r"D:\AI PROJECTS\photography-reference-lab-data"

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from ref_lab.config import Settings
from ref_lab.models import CandidateInput, Source, ProjectInput
from ref_lab.service import Library
from ref_lab.cli import doctor

BATCH_CONFIGS = [
    {
        "name": "王昭君·长夜焕生",
        "project_id": "37541e718c1140e4bbdd7c31278f6e83",
        "dir": Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-changye-huansheng-100"),
        "chosen": [3, 4, 5, 6, 26, 28, 36, 44, 45, 50, 59, 61, 62, 66, 67, 81, 90, 93],
        "create_project": None
    },
    {
        "name": "有马加奈",
        "project_id": "d9344449981d48e39ec24dbe92f93234",
        "dir": Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-arima-kana-100"),
        "chosen": [1, 2, 3, 4, 15, 34, 46, 49, 58, 72],
        "create_project": None
    },
    {
        "name": "西施",
        "project_id": None, # Will find or create
        "dir": Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-xishi-100"),
        "chosen": [1, 3, 4, 12, 16, 20, 23, 35, 36, 47, 53, 56, 64, 71, 72],
        "create_project": ProjectInput(character="西施", work="王者荣耀", brief="王者荣耀 西施 COS/正片摄影参考")
    },
    {
        "name": "JK摄影",
        "project_id": "82c18730e7d1461ea0bac521ecb3414e",
        "dir": Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-jk-100"),
        "chosen": [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 14, 18, 19, 22, 23, 24, 25, 31, 32, 33, 34, 35, 36, 37, 39, 40, 41, 43, 44, 45, 46, 47, 48, 51, 52, 53, 54, 56, 57, 58, 62, 63, 64, 65, 66, 67, 68, 70, 71, 81, 83, 88, 89, 90, 95, 97, 99],
        "create_project": None
    }
]


def run_import():
    settings = Settings.from_env()
    lib = Library(settings)

    print("==================================================")
    print("开始执行 100 张精选好图正式入库")
    print(f"数据目录: {settings.data_dir}")
    print("==================================================")

    total_imported = 0
    total_skipped = 0

    for batch in BATCH_CONFIGS:
        b_name = batch["name"]
        b_dir = batch["dir"]
        chosen_indices = batch["chosen"]
        manifest_path = b_dir / "manifest.json"
        images_dir = b_dir / "images"

        if not manifest_path.is_file():
            print(f"Warning: Manifest not found for {b_name}, skipping.")
            continue

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        items = [d for d in manifest_data if d["index"] in chosen_indices]

        # Resolve project
        project_id = batch["project_id"]
        if not project_id and batch.get("create_project"):
            # Check if project already exists
            existing_p = [p for p in lib.projects() if p.get("character") == batch["create_project"].character]
            if existing_p:
                project_id = existing_p[0]["id"]
            else:
                new_p = lib.create_project(batch["create_project"])
                project_id = new_p["id"]
                print(f"创建新项目 [{b_name}]: ID={project_id}")

        proj = lib.project(project_id)
        print(f"\n[{b_name}] 目标项目: {proj.get('character')} ({proj.get('work')}) | 计划入库: {len(items)} 张")

        batch_imported = 0
        for item in items:
            img_file = images_dir / item["filename"]
            if not img_file.is_file():
                print(f"  Missing file: {img_file}")
                continue

            raw_bytes = img_file.read_bytes()
            asset = lib.ingest_asset(raw_bytes, item["filename"])

            # Add as candidate with decision="keep"
            intent = "transferable_pose" if b_name == "JK摄影" else "exact_character"
            candidate_input = CandidateInput(
                asset_sha=asset["id"],
                title=item.get("title") or "未命名参考",
                source=Source(
                    page_url=item.get("page_url", "") if item.get("page_url", "").startswith("http") else "",
                    image_url=item.get("image_url", "") if item.get("image_url", "").startswith("http") else "",
                    title=item.get("title", ""),
                    author=item.get("author", ""),
                    search_query=item.get("query", ""),
                ),
                discovery_intent=intent,
                discovery_reason=item.get("verdict_desc", "人类审美精选"),
                import_key=f"user_keep_{item['filename']}"
            )

            try:
                res = lib.add_candidate(project_id, candidate_input, decision="keep", actor="human")
                ref_obj = res["reference"]
                batch_imported += 1
                total_imported += 1
                print(f"  + #{item['index']:03d} 入库成功: {item.get('title')[:25]} (Ref ID: {ref_obj['id'][:8]})")
            except Exception as e:
                # E.g. already in library
                print(f"  ~ #{item['index']:03d} 提示: {e} ({item.get('title')[:20]})")
                total_skipped += 1

        print(f"[{b_name}] 完成入库: {batch_imported}/{len(items)} 张")

    print("\n==================================================")
    print(f"入库汇总: 成功导入 {total_imported} 张, 跳过/已存在 {total_skipped} 张")
    print("==================================================")

    # Run library doctor check
    doc = doctor(lib)
    print(f"Library Doctor 诊断结果: ok={doc['ok']}, assets={doc.get('assets')}, refs={doc.get('refs')}")
    if not doc["ok"]:
        print("Doctor errors:", doc.get("errors"))


if __name__ == "__main__":
    run_import()

