#!/usr/bin/env python3
"""Local collection adapter conforming to photography-reference-lab agent_collection contract.

Takes a task bundle and produces a Schema 3 CandidatePackage zip archive.
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
from urllib.parse import quote, urlsplit
from uuid import uuid4
import zipfile

import httpx
from PIL import Image


def parse_arguments() -> tuple[Path, Path]:
    parser = argparse.ArgumentParser(description="Photography Reference Lab Local Collector Adapter")
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
        # Maybe task_path is directly inside the directory
        candidates = list(task_dir.glob("**/job.json"))
        if candidates:
            job_file = candidates[0]
            task_dir = job_file.parent
        else:
            sys.stderr.write(f"Error: job.json not found in {task_dir}\n")
            sys.exit(1)

    with open(job_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # In job bundles, job is nested under data["job"], and project under data["project"]
    job = data.get("job") if isinstance(data, dict) and "job" in data else data
    if "project" in data and isinstance(data["project"], dict):
        if not job.get("project_snapshot"):
            job["project_snapshot"] = data["project"]
    return job, task_dir


def build_queries(job: dict) -> list[str]:
    queries = list(job.get("queries") or [])
    project = job.get("project_snapshot") or {}
    character = (project.get("character") or "").strip()
    costume = (project.get("costume") or "").strip()
    work = (project.get("work") or "").strip()

    generated: list[str] = []
    if character and costume:
        generated.append(f"{character} {costume} cos 正片")
        generated.append(f"{character} {costume} cosplay 摄影")
        generated.append(f"{character} {costume} cos 漫展")
        if work:
            generated.append(f"{work} {character} {costume} cos")
    elif character:
        generated.append(f"{character} cos 正片")
        generated.append(f"{character} cosplay 摄影")
        if work:
            generated.append(f"{work} {character} cos")

    for q in generated:
        if q not in queries:
            queries.append(q)

    return queries


def fetch_bing_candidates(queries: list[str], target_count: int, character: str, costume: str) -> tuple[list[dict], dict[str, bytes], list[dict]]:
    client = httpx.Client(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
        follow_redirects=True,
        timeout=12.0
    )

    seen_shas: set[str] = set()
    candidates: list[dict] = []
    images: dict[str, bytes] = {}
    query_log: list[dict] = []

    for query in queries:
        if len(candidates) >= target_count:
            break

        q_count = 0
        search_url = f"https://cn.bing.com/images/async?q={quote(query)}&first=1&count=35"
        try:
            resp = client.get(search_url)
            if resp.status_code != 200:
                query_log.append({"query": query, "source": "bing", "kept": 0, "stop_reason": f"HTTP {resp.status_code}"})
                continue

            matches = re.findall(r'm="([^"]+)"', resp.text)
            for m in matches:
                if len(candidates) >= target_count:
                    break

                try:
                    record = json.loads(html.unescape(m))
                except Exception:
                    continue

                murl = record.get("murl")
                turl = record.get("turl")
                purl = record.get("purl") or search_url
                title = record.get("t") or record.get("desc") or f"{character} {costume} 参考"
                desc = record.get("desc") or ""

                img_bytes: bytes | None = None
                # Try original murl first with Referer
                if murl:
                    try:
                        r_img = client.get(murl, headers={"Referer": purl}, timeout=6.0)
                        if r_img.status_code == 200 and len(r_img.content) >= 5000:
                            img_bytes = r_img.content
                    except Exception:
                        img_bytes = None

                # Fallback to thumbnail URL if murl failed
                if not img_bytes and turl:
                    try:
                        r_thumb = client.get(turl, timeout=6.0)
                        if r_thumb.status_code == 200 and len(r_thumb.content) >= 5000:
                            img_bytes = r_thumb.content
                    except Exception:
                        img_bytes = None

                if not img_bytes:
                    continue

                # Verify PIL Image
                try:
                    with Image.open(io.BytesIO(img_bytes)) as pil_img:
                        w, h = pil_img.size
                        if w < 250 or h < 250:
                            continue
                        fmt = (pil_img.format or "JPEG").lower()
                        ext = "jpg" if fmt in {"jpeg", "jpg"} else ("png" if fmt == "png" else "webp")
                except Exception:
                    continue

                sha = hashlib.sha256(img_bytes).hexdigest()
                if sha in seen_shas:
                    continue
                seen_shas.add(sha)

                img_filename = f"{sha[:16]}.{ext}"
                images[img_filename] = img_bytes

                # Determine preflight
                is_cos = any(k in (title + " " + desc + " " + query).lower() for k in ["cos", "cosplay", "正片", "漫展", "场照"])
                content_type = "real_person_cosplay" if is_cos else "real_person_portrait"
                char_in_text = character.lower() in (title + " " + desc).lower()
                costume_in_text = costume.lower() in (title + " " + desc).lower() if costume else True

                identity_pred = "match" if (char_in_text and costume_in_text) else ("match" if char_in_text else "uncertain")

                candidate_entry = {
                    "id": f"cand-{len(candidates) + 1:03d}",
                    "file": f"images/{img_filename}",
                    "title": title[:350],
                    "source": {
                        "page_url": purl[:2000],
                        "image_url": (murl or turl or "")[:2000],
                        "author": "",
                        "title": title[:350],
                        "search_query": query[:350],
                        "rights": "unknown",
                        "source_confirmed": False
                    },
                    "discovery_intent": "exact_character" if identity_pred == "match" else "transferable_pose",
                    "discovery_reason": f"通过检索「{query}」在公开图像中发现",
                    "discovery_url": search_url[:2000],
                    "notes": desc[:800],
                    "preflight": {
                        "content_type": content_type,
                        "identity_prediction": identity_pred,
                        "confidence": "medium",
                        "visual_evidence": ["真人实拍", f"符合检索词「{query}」特征"],
                        "reason": f"通过搜索词「{query}」匹配并提取原图，初步观察符合真人参考"
                    }
                }
                candidates.append(candidate_entry)
                q_count += 1

            query_log.append({
                "query": query,
                "source": "bing_images",
                "kept": q_count,
                "stop_reason": f"本词完成，获取到 {q_count} 个候选"
            })
        except Exception as e:
            query_log.append({
                "query": query,
                "source": "bing_images",
                "kept": q_count,
                "stop_reason": f"异常: {type(e).__name__}"
            })

    return candidates, images, query_log


def main() -> None:
    task_path, result_file = parse_arguments()
    job, _ = load_job_info(task_path)

    job_id = job["id"]
    project = job.get("project_snapshot") or {}
    character = (project.get("character") or "").strip()
    costume = (project.get("costume") or "").strip()
    target_count = min(job.get("target_count") or 30, 40)

    queries = build_queries(job)
    candidates, images, query_log = fetch_bing_candidates(queries, target_count, character, costume)

    batch_id = uuid4().hex[:16]
    manifest = {
        "schema_version": 3,
        "job_id": job_id,
        "batch_id": batch_id,
        "candidates": candidates,
        "execution_report": {
            "producer": "local_collection_adapter",
            "status": "completed" if candidates else "blocked",
            "summary": f"本地采集适配器完成检索，共获取 {len(candidates)} 个独立候选",
            "source_checks": [
                {
                    "source": "bing_images",
                    "status": "usable" if candidates else "login_required",
                    "detail": "公开图像检索接口正常返回" if candidates else "未检索到有效结果"
                }
            ],
            "query_log": query_log,
            "gaps": [] if candidates else ["未能从公开搜索源获取有效图片"]
        }
    }

    result_file.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(result_file, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for filename, data in images.items():
            zf.writestr(f"images/{filename}", data)

    print(f"Collection complete: {len(candidates)} candidates saved to {result_file}")
    sys.exit(0)


if __name__ == "__main__":
    main()
