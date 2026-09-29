#!/usr/bin/env python3
"""Strict local search adapter for Photography Reference Lab.

This adapter searches and downloads candidate images. It deliberately does NOT
claim visual identity/modality verification: no vision model runs here, so it
returns Schema 2 packages without preflight fields.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
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


def build_queries(job: dict, for_browser: bool = False) -> list[str]:
    policy = build_policy(job)
    character, costume, work = policy["character"], policy["costume"], policy["work"]
    core = " ".join(x for x in (work, character, costume) if x).strip()
    generated: list[str] = []

    if core:
        generated.extend([
            f"{core} cosplay 正片",
            f"{core} coser 摄影",
            f"{core} cos 返图",
            f"{core} cos 场照",
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

    if for_browser:
        result: list[str] = []
        for query in generated:
            q_clean = query.strip()
            if q_clean and q_clean not in result:
                result.append(q_clean)
        return result

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
    pixels = list(gray.get_flattened_data() if hasattr(gray, "get_flattened_data") else gray.getdata())
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


def find_bsk_bin() -> str | None:
    bin_path = shutil.which("bsk") or shutil.which("bsk.exe")
    if bin_path:
        return bin_path
    win_default = r"C:\Users\Dell\.local\bin\bsk.exe"
    if os.name == "nt" and os.path.isfile(win_default):
        return win_default
    wsl_default = "/mnt/c/Users/Dell/.local/bin/bsk.exe"
    if os.path.isfile(wsl_default):
        return wsl_default
    home_bin = os.path.expanduser("~/.local/bin/bsk")
    if os.path.isfile(home_bin):
        return home_bin
    return None


def get_connected_browser_id(bsk_bin: str) -> str | None:
    env = {**os.environ, "BSK_AUTO_START": "0"}
    try:
        p = subprocess.run([bsk_bin, "browsers", "--json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=5)
        browsers = json.loads(p.stdout)
        if browsers:
            for b in browsers:
                if b.get("browser_name") == "edge":
                    return b["instance_id"]
            return browsers[0]["instance_id"]
    except Exception:
        pass

    powershell_bin = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell_bin:
        cmd = [powershell_bin, "-Command", "Start-Process msedge.exe extension://emacgiaaaiojkkpkddmmdfhmokgmnikg/popup.html"]
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
            for _ in range(5):
                time.sleep(1)
                p = subprocess.run([bsk_bin, "browsers", "--json"], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", env=env, timeout=5)
                browsers = json.loads(p.stdout)
                if browsers:
                    for b in browsers:
                        if b.get("browser_name") == "edge":
                            return b["instance_id"]
                    return browsers[0]["instance_id"]
        except Exception:
            pass
    return None


def fetch_bsk_candidates(
    bsk_bin: str, browser_id: str, job: dict, target_count: int, policy: dict
) -> tuple[list[dict], dict[str, bytes], list[dict]]:
    env = {**os.environ, "BSK_AUTO_START": "0"}
    try:
        start_p = subprocess.run([bsk_bin, "session", "start", "--browser", browser_id, "--json"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10)
        sess_data = json.loads(start_p.stdout)
        session_id = sess_data.get("session_id")
    except Exception as exc:
        sys.stderr.write(f"Failed to start BrowserSkill session: {exc}\n")
        return [], {}, []

    if not session_id:
        return [], {}, []

    seen_shas: set[str] = set()
    seen_dhashes: list[str] = []
    seen_urls: set[str] = set()
    candidates: list[dict] = []
    images: dict[str, bytes] = {}
    query_log: list[dict] = []

    browser_queries = build_queries(job, for_browser=True)

    try:
        # Phase 1: 优先小红书 (Xiaohongshu)
        for query in browser_queries:
            if len(candidates) >= target_count:
                break
            kept = 0
            rejected_metadata = 0
            rejected_image = 0
            rejected_duplicate = 0

            xhs_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}"
            subprocess.run(
                [bsk_bin, "navigate", xhs_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=30
            )
            time.sleep(3.5)

            extract_js = """(() => {
                const cards = [];
                const items = document.querySelectorAll('section, div.note-item, div.search-card');
                for (const item of items) {
                    const img = item.querySelector('img');
                    const link = item.querySelector('a[href*="/search_result/"], a[href*="/explore/"]');
                    const titleEl = item.querySelector('.title, .desc, a.title span, span.title') || item.querySelector('a:not(.user) span');
                    const authorEl = item.querySelector('.author, .name, .user-name, a.user span');
                    if (img && (img.currentSrc || img.src)) {
                        const src = img.currentSrc || img.src;
                        if (src.includes('xhscdn.com') && !src.includes('avatar') && img.naturalWidth >= 180) {
                            cards.push({
                                title: titleEl?.innerText?.trim() || img.alt?.trim() || '',
                                author: authorEl?.innerText?.trim() || '',
                                desc: titleEl?.innerText?.trim() || img.alt?.trim() || '',
                                purl: link?.href || location.href,
                                image_url: src,
                                width: img.naturalWidth,
                                height: img.naturalHeight
                            });
                        }
                    }
                }
                return cards;
            })()"""

            eval_p = subprocess.run(
                [bsk_bin, "evaluate", "--session", session_id, "--json", extract_js],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10
            )
            try:
                raw_eval = json.loads(eval_p.stdout)
                cards = raw_eval.get("value", []) if isinstance(raw_eval, dict) else (raw_eval if isinstance(raw_eval, list) else [])
            except Exception:
                cards = []

            for card in cards:
                if len(candidates) >= target_count:
                    break
                allowed, reason = result_metadata_allowed({
                    "t": card["title"],
                    "desc": card["desc"],
                    "purl": card["purl"]
                }, policy)
                if not allowed:
                    rejected_metadata += 1
                    continue

                img_url = card.get("image_url", "").strip()
                if not img_url or img_url in seen_urls:
                    rejected_duplicate += 1
                    continue
                seen_urls.add(img_url)

                fetch_js = f"""(async () => {{
                    try {{
                        const resp = await fetch({json.dumps(img_url)});
                        if (!resp.ok) return null;
                        const blob = await resp.blob();
                        const reader = new FileReader();
                        return await new Promise((resolve) => {{
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        }});
                    }} catch (e) {{
                        return null;
                    }}
                }})()"""
                fetch_p = subprocess.run(
                    [bsk_bin, "evaluate", "--session", session_id, "--json", fetch_js],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=12
                )
                try:
                    fetch_val = json.loads(fetch_p.stdout).get("value")
                except Exception:
                    fetch_val = None

                if not fetch_val or "," not in fetch_val:
                    rejected_image += 1
                    continue

                try:
                    img_bytes = base64.b64decode(fetch_val.split(",", 1)[1])
                except Exception:
                    rejected_image += 1
                    continue

                valid, ext, dhash = validate_downloaded_image(img_bytes, policy)
                if not valid:
                    rejected_image += 1
                    continue

                sha = hashlib.sha256(img_bytes).hexdigest()
                if sha in seen_shas or any(hamming_distance(dhash, old) <= 3 for old in seen_dhashes):
                    rejected_duplicate += 1
                    continue

                seen_shas.add(sha)
                seen_dhashes.append(dhash)
                filename = f"{sha[:16]}.{ext}"
                images[filename] = img_bytes
                title = str(card.get("title") or f"{policy['character']} 小红书参考")[:350]
                desc = str(card.get("desc") or "")[:800]
                candidates.append({
                    "id": f"cand-{len(candidates) + 1:03d}",
                    "file": f"images/{filename}",
                    "title": title,
                    "source": {
                        "page_url": str(card.get("purl") or xhs_url)[:2000],
                        "image_url": img_url[:2000],
                        "author": str(card.get("author") or "")[:200],
                        "title": title,
                        "search_query": query[:350],
                        "rights": "unknown",
                        "source_confirmed": False,
                        "obtained_as": "platform_variant",
                    },
                    "discovery_intent": "exact_character" if policy["require_cosplay"] else "transferable_pose",
                    "discovery_reason": f"通过 BrowserSkill 检索「{query}」在小红书发现",
                    "discovery_url": xhs_url[:2000],
                    "notes": desc,
                })
                kept += 1

            query_log.append({
                "query": query,
                "source": "xiaohongshu",
                "kept": kept,
                "stop_reason": (
                    f"kept={kept}; metadata_filtered={rejected_metadata}; "
                    f"image_filtered={rejected_image}; duplicate_filtered={rejected_duplicate}"
                ),
            })

        # Phase 2: 其次 Pinterest (若数量不足且未达标)
        if len(candidates) < target_count:
            for query in browser_queries:
                if len(candidates) >= target_count:
                    break
                kept = 0
                rejected_metadata = 0
                rejected_image = 0
                rejected_duplicate = 0

                pin_url = f"https://www.pinterest.com/search/pins/?q={quote(query)}"
                subprocess.run(
                    [bsk_bin, "navigate", pin_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=30
                )
                time.sleep(3.0)

                pin_js = """(() => {
                    const pins = [];
                    const imgs = Array.from(document.querySelectorAll("img")).filter(img => {
                        return (img.src.includes("pinimg.com") || (img.currentSrc && img.currentSrc.includes("pinimg.com")))
                            && img.naturalWidth >= 200 && img.naturalHeight >= 200;
                    });
                    for (const img of imgs) {
                        const link = img.closest('a');
                        pins.push({
                            title: img.alt || '',
                            desc: img.alt || '',
                            purl: link?.href || location.href,
                            image_url: img.currentSrc || img.src,
                            width: img.naturalWidth,
                            height: img.naturalHeight
                        });
                    }
                    return pins;
                })()"""

                eval_p = subprocess.run(
                    [bsk_bin, "evaluate", "--session", session_id, "--json", pin_js],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=10
                )
                try:
                    raw_eval = json.loads(eval_p.stdout)
                    pins = raw_eval.get("value", []) if isinstance(raw_eval, dict) else (raw_eval if isinstance(raw_eval, list) else [])
                except Exception:
                    pins = []

                for pin in pins:
                    if len(candidates) >= target_count:
                        break
                    allowed, reason = result_metadata_allowed({
                        "t": pin["title"],
                        "desc": pin["desc"],
                        "purl": pin["purl"]
                    }, policy)
                    if not allowed:
                        rejected_metadata += 1
                        continue

                    img_url = pin.get("image_url", "").strip()
                    if not img_url or img_url in seen_urls:
                        rejected_duplicate += 1
                        continue
                    seen_urls.add(img_url)

                    try:
                        resp = httpx.get(img_url, timeout=8.0)
                        if resp.status_code == 200 and len(resp.content) > 10_000:
                            img_bytes = resp.content
                        else:
                            rejected_image += 1
                            continue
                    except Exception:
                        rejected_image += 1
                        continue

                    valid, ext, dhash = validate_downloaded_image(img_bytes, policy)
                    if not valid:
                        rejected_image += 1
                        continue

                    sha = hashlib.sha256(img_bytes).hexdigest()
                    if sha in seen_shas or any(hamming_distance(dhash, old) <= 3 for old in seen_dhashes):
                        rejected_duplicate += 1
                        continue

                    seen_shas.add(sha)
                    seen_dhashes.append(dhash)
                    filename = f"{sha[:16]}.{ext}"
                    images[filename] = img_bytes
                    title = str(pin.get("title") or f"{policy['character']} Pinterest 参考")[:350]
                    desc = str(pin.get("desc") or "")[:800]
                    candidates.append({
                        "id": f"cand-{len(candidates) + 1:03d}",
                        "file": f"images/{filename}",
                        "title": title,
                        "source": {
                            "page_url": str(pin.get("purl") or pin_url)[:2000],
                            "image_url": img_url[:2000],
                            "author": "",
                            "title": title,
                            "search_query": query[:350],
                            "rights": "unknown",
                            "source_confirmed": False,
                            "obtained_as": "platform_variant",
                        },
                        "discovery_intent": "exact_character" if policy["require_cosplay"] else "transferable_pose",
                        "discovery_reason": f"通过 BrowserSkill 检索「{query}」在 Pinterest 发现",
                        "discovery_url": pin_url[:2000],
                        "notes": desc,
                    })
                    kept += 1

                query_log.append({
                    "query": query,
                    "source": "pinterest",
                    "kept": kept,
                    "stop_reason": (
                        f"kept={kept}; metadata_filtered={rejected_metadata}; "
                        f"image_filtered={rejected_image}; duplicate_filtered={rejected_duplicate}"
                    ),
                })
    finally:
        subprocess.run([bsk_bin, "session", "stop", session_id],
                       capture_output=True, text=True, env=env, timeout=5)

    return candidates, images, query_log


def main() -> None:
    task_path, result_file = parse_arguments()
    job, _ = load_job_info(task_path)
    policy = build_policy(job)
    target_count = min(int(job.get("target_count") or 30), 40)

    candidates: list[dict] = []
    images: dict[str, bytes] = {}
    query_log: list[dict] = []
    source_checks: list[dict] = []
    producer = "local_collection_adapter_search_only"

    # 1. 优先尝试本地已连接的 BrowserSkill Edge 实例 (小红书 + Pinterest)
    bsk_bin = find_bsk_bin()
    browser_id = get_connected_browser_id(bsk_bin) if bsk_bin else None
    if bsk_bin and browser_id:
        producer = "local_browserskill_adapter"
        candidates, images, query_log = fetch_bsk_candidates(
            bsk_bin, browser_id, job, target_count, policy
        )
        source_checks.append({
            "source": "xiaohongshu",
            "status": "usable" if any(q.get("source") == "xiaohongshu" and q.get("kept", 0) > 0 for q in query_log) else "untested",
            "detail": "优先通过本地 BrowserSkill Edge 实例访问小红书检索真人参考。",
        })
        source_checks.append({
            "source": "pinterest",
            "status": "usable" if any(q.get("source") == "pinterest" and q.get("kept", 0) > 0 for q in query_log) else "untested",
            "detail": "在小红书后通过 BrowserSkill 访问 Pinterest 补充参考。",
        })

    # 2. 仅在未连接/未安装 BrowserSkill 时，降级走备用 Bing
    if not query_log and not (bsk_bin and browser_id):
        queries = build_queries(job, for_browser=False)
        candidates, images, query_log = fetch_bing_candidates(queries, target_count, policy)
        source_checks.append({
            "source": "bing_images_photo_filter",
            "status": "usable" if candidates else "untested",
            "detail": "未检测到已连接的 BrowserSkill Edge 实例；使用 Photo + Large 搜索引擎检索。",
        })

    summary_text = (
        f"严格检索得到 {len(candidates)} 个候选；未运行视觉模型，未宣称角色/模态已通过。"
        if candidates else
        "严格检索没有得到满足硬条件的候选；宁可少图，不用插画/游戏图凑数。"
    )

    manifest = {
        # Search-only adapter: no fake visual preflight.
        "schema_version": 2,
        "job_id": job["id"],
        "batch_id": uuid4().hex[:16],
        "candidates": candidates,
        "execution_report": {
            "producer": producer,
            "status": "completed" if candidates else "blocked",
            "summary": summary_text,
            "source_checks": source_checks,
            "query_log": query_log,
            "gaps": [] if candidates else ["没有足够满足用户硬要求的候选；请调整搜索词或改用人工检索。"],
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
