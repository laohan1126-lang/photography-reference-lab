#!/usr/bin/env python3
"""Render the human-readable Markdown view from the canonical JSON manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "id": "ID",
    "local_file": "本地文件",
    "fallback_file": "备用文件",
    "source_platform": "来源平台",
    "source_note_title": "来源笔记",
    "source_author": "作者",
    "source_url": "来源链接",
    "search_keyword": "搜索词",
    "natural_width": "原始宽度",
    "natural_height": "原始高度",
    "saved_width": "保存宽度",
    "saved_height": "保存高度",
    "file_size": "文件字节",
    "capture_method": "采集方式",
    "title": "标题",
    "gender": "性别",
    "primary_category": "主分类",
    "finder_route": "检索路线",
    "pose_type": "姿势类型",
    "scene": "场景",
    "shot_size_quick": "景别",
    "reference_value": "参考价值",
    "quick_use": "使用建议",
    "field_usability": "现场可用性",
    "lighting_difficulty": "布光难度",
    "style_archetype": "风格类型",
    "why_learn": "参考价值说明",
    "pose_analysis": "动作分析",
    "camera_analysis": "机位分析",
    "lighting_analysis": "灯光分析",
    "field_direction": "现场指令",
    "duplicate_group": "去重组",
    "duplicate_decision": "去重判断",
    "source_metadata_status": "来源元数据状态",
    "search_keyword_status": "搜索词状态",
}


def workspace_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as error:
        raise ValueError("paths must stay inside the workspace") from error
    return path


def append_timing(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def display_value(key: str, value) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        text = "、".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)

    if key == "local_file":
        try:
            text = Path(text).resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            pass
        tick = chr(96)
        return f"{tick}{text}{tick}"
    if key == "source_url" and text.startswith("https://"):
        return f"<{text}>"
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\n  ")


def render(manifest: dict) -> str:
    records = manifest.get("READY_FOR_NOTION_IMPORT", [])
    if not isinstance(records, list):
        raise ValueError("READY_FOR_NOTION_IMPORT must be a list")
    summary = manifest.get("summary", {})
    title = manifest.get("batch") or "摄影参考图批次"
    count = summary.get("final_assets", len(records)) if isinstance(summary, dict) else len(records)
    lines = [
        f"# {title}",
        "",
        f"- 状态：{manifest.get('status', '未标注')}",
        f"- 最终资产：{count} 张",
    ]
    if isinstance(summary, dict):
        for key in (
            "candidate_cards_browsed_approx",
            "notes_opened_approx",
            "images_analyzed_approx",
            "downloaded_candidates",
            "fallback_screenshots",
        ):
            if key in summary:
                lines.append(f"- {key}：{summary[key]}")
    lines.append("")

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each manifest record must be an object")
        record_id = record.get("id", "未编号")
        record_title = record.get("title", "未命名")
        lines.extend((f"## {record_id} — {record_title}", ""))
        for key, value in record.items():
            if key in {"id", "title"}:
                continue
            label = LABELS.get(key, key)
            lines.append(f"- {label}：{display_value(key, value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="staging/manifest.json")
    parser.add_argument("--output", default="staging/manifest.generated.md")
    parser.add_argument("--timings", default="staging/batch-timings.jsonl")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    summary = {"stage": "render", "record_count": 0, "status": "ok"}
    exit_code = 0
    try:
        source = workspace_path(args.input)
        target = workspace_path(args.output)
        timings_path = workspace_path(args.timings)
        if len({source, target, timings_path}) != 3:
            raise ValueError("input, output, and timings paths must be different")
        manifest = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest JSON must contain an object")
        summary["batch_id"] = manifest.get("batch")
        rendered = render(manifest)
        summary["record_count"] = len(manifest.get("READY_FOR_NOTION_IMPORT", []))
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
        print(f"Rendered {len(manifest.get('READY_FOR_NOTION_IMPORT', []))} records to {target.relative_to(ROOT)}")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        summary["status"] = "error"
        summary["error"] = str(error)
        exit_code = 2

    summary["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["started_at"] = started_at.isoformat(timespec="seconds")
    summary["elapsed_seconds"] = round(time.monotonic() - started_clock, 3)
    summary["output_file"] = args.output
    try:
        append_timing(workspace_path(args.timings), summary)
    except (OSError, ValueError) as error:
        print(f"Could not write timing summary: {error}", file=sys.stderr)
        exit_code = 2
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
