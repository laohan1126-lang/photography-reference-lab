#!/usr/bin/env python3
"""Strict local search adapter for Photography Reference Lab.

This adapter searches and downloads candidate images. It deliberately does NOT
claim visual identity/modality verification: no vision model runs here, so it
returns Schema 2 packages without preflight fields.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote
from uuid import uuid4
import zipfile

import httpx
from PIL import Image, ImageOps


POSITIVE_COSPLAY_MARKERS = (
    "cosplay", "coser", " cos ", "cos正片", "cos 正片", "正片", "场照",
    "返图", "出镜", "写真", "棚拍", "摄影", "漫展",
)
NEGATIVE_TYPE_MARKERS = (
    "游戏截图", "游戏画面", "游戏cg", "游戏 cg", "皮肤特效", "特效设计", "技能特效",
    "官方立绘", "立绘", "插画", "同人图", "同人画", "原画", "壁纸", "海报",
    "concept art", "illustration", "fanart", "fan art", "wallpaper", "render",
    "3d model", "3d模型", "建模", "模型展示", "皮肤展示", "角色展示",
    "商品图", "商品展示", "服装展示", "人台", "假人", "mannequin", "cos服",
)
NEGATIVE_QUERY_TERMS = (
    "游戏截图", "游戏画面", "皮肤特效", "特效设计", "插画", "立绘", "原画",
    "壁纸", "CG", "建模", "模型", "商品图", "服装展示", "人台",
)
NEGATION_WORDS = ("不要", "不需要", "排除", "禁止", "别找", "不要找")


def parse_arguments() -> tuple[Path, Path]:
    parser = argparse.ArgumentParser(description="Photography Reference Lab strict local collector")
    parser.add_argument("positional_args", nargs="*", help="Positional task_file and result_file")
    parser.add_argument("--task-file", dest="task_file", help="Path to task file or AGENT_TASK.md")
    parser.add_argument("--task-dir", dest="task_dir", help="Path to unpacked task directory")
    parser.add_argument("--result-file", dest="result_file", help="Path to output result.zip")
    args = parser.parse_args()

    task_file = args.task_file or args.task_dir
    result_file = args.result_file
    if not task_file and args.positional_args:
        task_file = args.positional_args[0]
    if not result_file and len(args.positional_args) > 1:
        result_file = args.positional_args[1]
    if not task_file or not result_file:
        sys.stderr.write("Error: task_file and result_file must be specified.\n")
        sys.exit(1)
    return Path(task_file), Path(result_file)


def load_job_info(task_path: Path) -> tuple[dict, Path]:
    task_dir = task_path.parent if task_path.is_file() else task_path
    job_file = task_dir / "job.json"
    if not job_file.is_file():
        matches = list(task_dir.glob("**/job.json"))
        if not matches:
            sys.stderr.write(f"Error: job.json not found in {task_dir}\n")
            sys.exit(1)
        job_file = matches[0]
        task_dir = job_file.parent

    data = json.loads(job_file.read_text(encoding="utf-8"))
    job = data.get("job") if isinstance(data, dict) and "job" in data else data
    if "project" in data and isinstance(data["project"], dict) and not job.get("project_snapshot"):
        job["project_snapshot"] = data["project"]
    return job, task_dir


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _note_fragments(notes: str) -> list[str]:
    parts = re.split(r"[\n。；;！!？?]+", notes or "")
    return [
        p.strip()[:80] for p in parts
        if p.strip() and not any(word in p for word in NEGATION_WORDS)
    ][:4]


def build_policy(job: dict) -> dict:
    project = job.get("project_snapshot") or {}
    character = (project.get("character") or "").strip()
    costume = (project.get("costume") or "").strip()
    work = (project.get("work") or "").strip()
    notes = (job.get("notes") or "").strip()
    notes_lower = notes.lower()
    require_cosplay = any(k in notes_lower for k in ("cos", "cosplay", "正片", "场照", "真人", "实拍", "返图"))
    require_character = bool(character)
    require_costume = bool(costume) and any(k in notes_lower for k in ("该皮肤", "这个皮肤", "本皮肤", "同皮肤", "只找", "仅找", "限定"))
    portrait_only = any(k in notes_lower for k in ("竖图", "竖版", "竖构图", "竖幅"))
    return {
        "character": character,
        "costume": costume,
        "work": work,
        "notes": notes,
        "positive_note_fragments": _note_fragments(notes),
        "require_cosplay": require_cosplay,
        "require_character": require_character,
        "require_costume": require_costume,
        "portrait_only": portrait_only,
    }


def _negative_suffix() -> str:
    return " ".join(f"-{term}" for term in NEGATIVE_QUERY_TERMS)


def build_queries(job: dict) -> list[str]:
    policy = build_policy(job)
    character, costume, work = policy["character"], policy["costume"], policy["work"]
    core = " ".join(x for x in (work, character, costume) if x).strip()
    generated: list[str] = []

    if core:
        generated.extend([
            f"{core} cosplay 正片",
            f"{core} coser 摄影",
            f"{core} cos 返图",
        ])
    for fragment in policy["positive_note_fragments"]:
        if core and fragment not in core:
            generated.append(f"{core} {fragment}")
        elif fragment:
            generated.append(fragment)

    # Old generic job queries are allowed only when they retain the requested skin.
    for query in job.get("queries") or []:
        q = str(query).strip()
        if not q:
            continue
        if policy["require_costume"] and costume and costume.lower() not in q.lower():
            continue
        generated.append(q)

    suffix = _negative_suffix() if policy["require_cosplay"] else ""
    result: list[str] = []
    for query in generated:
        strict = f"{query} {suffix}".strip()
        if strict not in result:
            result.append(strict)
    return result


def result_metadata_allowed(record: dict, policy: dict) -> tuple[bool, str]:
    title = _normal(str(record.get("t") or ""))
    desc = _normal(str(record.get("desc") or ""))
    page = _normal(str(record.get("purl") or ""))
    combined = f" {title} {desc} {page} "

    for marker in NEGATIVE_TYPE_MARKERS:
        if marker.lower() in combined:
            return False, f"negative_type:{marker}"

    if policy["require_cosplay"] and not any(marker in combined for marker in POSITIVE_COSPLAY_MARKERS):
        return False, "missing_cosplay_evidence"

    character = _normal(policy["character"])
    costume = _normal(policy["costume"])
    if policy["require_character"] and character and character not in combined:
        return False, "missing_character"
    if policy["require_costume"] and costume and costume not in combined:
        return False, "missing_costume"
    return True, "accepted_metadata"


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    gray = ImageOps.exif_transpose(image).convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    value = 0
    for y in range(hash_size):
        for x in range(hash_size):
            value = (value << 1) | int(pixels[y * (hash_size + 1) + x] > pixels[y * (hash_size + 1) + x + 1])
    return f"{value:016x}"


def hamming_distance(left: str, right: str) -> int:
    if len(left) != len(right):
        return 64
    return (int(left, 16) ^ int(right, 16)).bit_count()


def validate_downloaded_image(raw: bytes, policy: dict) -> tuple[bool, str, str]:
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            if getattr(image, "n_frames", 1) != 1:
                return False, "", "animated_or_multiframe"
            width, height = image.size
            if min(width, height) < 480 or max(width, height) < 720:
                return False, "", "too_small"
            if policy["portrait_only"] and height <= width:
                return False, "", "not_portrait"
            fmt = (image.format or "").lower()
            if fmt not in {"jpeg", "jpg", "png", "webp"}:
                return False, "", "unsupported_format"
            ext = "jpg" if fmt in {"jpeg", "jpg"} else fmt
            dhash = compute_dhash(image)
            return True, ext, dhash
    except Exception:
        return False, "", "invalid_image"


def fetch_bing_candidates(queries: list[str], target_count: int, policy: dict) -> tuple[list[dict], dict[str, bytes], list[dict]]:
    client = httpx.Client(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"},
        follow_redirects=True,
        timeout=12.0,
    )
    seen_shas: set[str] = set()
    seen_dhashes: list[str] = []
    seen_urls: set[str] = set()
    candidates: list[dict] = []
    images: dict[str, bytes] = {}
    query_log: list[dict] = []

    for query in queries:
        if len(candidates) >= target_count:
            break
        kept = 0
        rejected_metadata = 0
        rejected_image = 0
        rejected_duplicate = 0
        search_url = (
            f"https://cn.bing.com/images/async?q={quote(query)}&first=1&count=60"
            "&qft=+filterui:photo-photo+filterui:imagesize-large&form=IRFLTR"
        )
        try:
            resp = client.get(search_url)
            if resp.status_code != 200:
                query_log.append({"query": query, "source": "bing_images", "kept": 0, "stop_reason": f"HTTP {resp.status_code}"})
                continue
            for raw_record in re.findall(r'm="([^"]+)"', resp.text):
                if len(candidates) >= target_count:
                    break
                try:
                    record = json.loads(html.unescape(raw_record))
                except Exception:
                    continue

                allowed, reason = result_metadata_allowed(record, policy)
                if not allowed:
                    rejected_metadata += 1
                    continue

                image_url = str(record.get("murl") or "").strip()
                page_url = str(record.get("purl") or search_url).strip()
                if not image_url or image_url in seen_urls:
                    rejected_duplicate += 1
                    continue
                seen_urls.add(image_url)

                try:
                    image_response = client.get(image_url, headers={"Referer": page_url}, timeout=8.0)
                    content_type = image_response.headers.get("content-type", "").lower()
                    if image_response.status_code != 200 or len(image_response.content) < 10_000 or not content_type.startswith("image/"):
                        rejected_image += 1
                        continue
                    image_bytes = image_response.content
                except Exception:
                    rejected_image += 1
                    continue

                valid, ext, dhash = validate_downloaded_image(image_bytes, policy)
                if not valid:
                    rejected_image += 1
                    continue
                sha = hashlib.sha256(image_bytes).hexdigest()
                if sha in seen_shas or any(hamming_distance(dhash, old) <= 3 for old in seen_dhashes):
                    rejected_duplicate += 1
                    continue

                seen_shas.add(sha)
                seen_dhashes.append(dhash)
                filename = f"{sha[:16]}.{ext}"
                images[filename] = image_bytes
                title = str(record.get("t") or record.get("desc") or f"{policy['character']} {policy['costume']} 参考")[:350]
                desc = str(record.get("desc") or "")[:800]
                candidates.append({
                    "id": f"cand-{len(candidates) + 1:03d}",
                    "file": f"images/{filename}",
                    "title": title,
                    "source": {
                        "page_url": page_url[:2000],
                        "image_url": image_url[:2000],
                        "author": "",
                        "title": title,
                        "search_query": query[:350],
                        "rights": "unknown",
                        "source_confirmed": False,
                        "obtained_as": "as_received",
                    },
                    "discovery_intent": "exact_character",
                    "discovery_reason": "严格按本轮角色/皮肤/COS要求筛选的公开图片搜索候选；尚未做视觉身份确认。",
                    "discovery_url": search_url[:2000],
                    "notes": desc,
                })
                kept += 1

            query_log.append({
                "query": query,
                "source": "bing_images_photo_filter",
                "kept": kept,
                "stop_reason": (
                    f"kept={kept}; metadata_filtered={rejected_metadata}; "
                    f"image_filtered={rejected_image}; duplicate_filtered={rejected_duplicate}"
                ),
            })
        except Exception as exc:
            query_log.append({
                "query": query,
                "source": "bing_images_photo_filter",
                "kept": kept,
                "stop_reason": f"exception:{type(exc).__name__}",
            })

    return candidates, images, query_log


def main() -> None:
    task_path, result_file = parse_arguments()
    job, _ = load_job_info(task_path)
    policy = build_policy(job)
    target_count = min(int(job.get("target_count") or 30), 40)
    queries = build_queries(job)
    candidates, images, query_log = fetch_bing_candidates(queries, target_count, policy)

    manifest = {
        # Search-only adapter: no fake visual preflight.
        "schema_version": 2,
        "job_id": job["id"],
        "batch_id": uuid4().hex[:16],
        "candidates": candidates,
        "execution_report": {
            "producer": "local_collection_adapter_search_only",
            "status": "completed" if candidates else "blocked",
            "summary": (
                f"严格检索得到 {len(candidates)} 个候选；未运行视觉模型，未宣称角色/模态已通过。"
                if candidates else
                "严格检索没有得到满足硬条件的候选；宁可少图，不用插画/游戏图凑数。"
            ),
            "source_checks": [{
                "source": "bing_images_photo_filter",
                "status": "usable" if candidates else "untested",
                "detail": "使用 Photo + Large 搜索过滤，并在导入前执行角色/皮肤/COS元数据硬约束。",
            }],
            "query_log": query_log,
            "gaps": [] if candidates else ["没有足够满足用户硬要求的候选；请调整搜索词或改用 BrowserSkill 人工/Agent 搜索。"],
        },
    }

    result_file.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(result_file, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for filename, data in images.items():
            archive.writestr(f"images/{filename}", data)
    print(f"Collection complete: {len(candidates)} candidates saved to {result_file}")


if __name__ == "__main__":
    main()
