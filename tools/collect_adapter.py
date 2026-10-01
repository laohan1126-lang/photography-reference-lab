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
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

try:
    from tools.collage_splitter import CollageSplitter
except ImportError:
    try:
        from collage_splitter import CollageSplitter
    except ImportError:
        CollageSplitter = None


POSITIVE_COSPLAY_MARKERS = (
    "cosplay", "coser", " cos ", "cos正片", "cos 正片", "正片", "场照",
    "返图", "出镜", "写真", "棚拍", "摄影", "漫展", "自拍", "出片", "拍了",
    "📷", "动作参考", "妆面", "毛娘", "试衣", "后期", "成片", "出cos",
    "姿势分享", "姿势", "捞捞", "客片", "约拍", "同框",
)
NEGATIVE_TYPE_MARKERS = (
    "游戏截图", "游戏画面", "游戏cg", "游戏 cg", "皮肤特效", "特效设计", "技能特效",
    "官方立绘", "立绘", "插画", "同人图", "同人画", "原画", "壁纸", "海报",
    "concept art", "illustration", "fanart", "fan art", "wallpaper", "render",
    "3d model", "3d模型", "建模", "模型展示", "皮肤展示", "角色展示",
    "商品图", "商品展示", "服装展示", "人台", "假人", "mannequin",
    "cos服", "c服", "出服", "求服", "转单", "闲鱼", "出租", "出物",
    "裙撑", "做裙", "做衣服", "打版", "材料", "剪裁", "缝纫", "代工", "假发",
    "求助", "怎么整理", "如何整理", "难打理", "整理教程", "穿戴教程",
    "制作教程", "改造教程", "收纳教程", "怎么穿", "怎么做",
    "哪家好", "避雷", "测评", "店铺", "手办", "雕像", "粘土",
    "大家都在搜", "连招", "出装", "铭文", "上分", "对局",
    "大全套", "换物", "免押金", "同人", "恶搞", "段子",
    "对比", "详细对比", "盘点", "版型", "体验馆", "一条龙", "骗钱", "跑路", "拍的什么东西", "挂人", "三视图",
    "对镜自拍", "对镜拍", "试衣间", "各家", "出格裙", "山正", "好价", "急抛", "拼单",
    "搭子", "求搭子", "找搭子", "求一个", "蹲搭子", "组队", "扩列", "招募", "约拍搭子", "求队友",
    "道具展示", "道具制作", "自制道具", "道具自制", "翅膀",
    "聊天记录", "求问", "问问", "求返图", "捞返图", "求图", "有没有人拍到", "捞捞",
)
NEGATIVE_QUERY_TERMS = (
    "游戏截图", "游戏画面", "皮肤特效", "特效设计", "插画", "立绘", "原画",
    "壁纸", "CG", "建模", "模型", "商品图", "服装展示", "人台", "搭子",
)
NEGATION_WORDS = ("不要", "不需要", "排除", "禁止", "别找", "不要找")


def parse_arguments() -> tuple[Path, Path, bool]:
    parser = argparse.ArgumentParser(description="Photography Reference Lab strict local collector")
    parser.add_argument("positional_args", nargs="*", help="Positional task_file and result_file")
    parser.add_argument("--task-file", dest="task_file", help="Path to task file or AGENT_TASK.md")
    parser.add_argument("--task-dir", dest="task_dir", help="Path to unpacked task directory")
    parser.add_argument("--result-file", dest="result_file", help="Path to output result.zip")
    parser.add_argument(
        "--allow-bing-fallback", action="store_true",
        help="Only then may the collector use Bing images when no BrowserSkill "
             "browser is reachable.  Without this the run fails loudly instead.",
    )
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
    return Path(task_file), Path(result_file), args.allow_bing_fallback


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
    explicit_non_cosplay = any(k in notes_lower for k in ("不限cos", "非cos", "无需cos", "不仅cos", "不限真人"))
    require_cosplay = not explicit_non_cosplay
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


def _character_aliases(name: str) -> list[str]:
    name = _normal(name)
    if not name:
        return []
    aliases = [name]
    if len(name) == 3:
        aliases.append(name[1:])  # 王昭君 -> 昭君
        aliases.append(f"{name[1:]}{name[0]}")  # 王昭君 -> 昭君王
    elif "·" in name:
        aliases.extend(p for p in name.split("·") if p)
    return aliases


def result_metadata_allowed(record: dict, policy: dict) -> tuple[bool, str]:
    """Conservatively classify discovery metadata before downloading a candidate.

    Search-page membership is only discovery context.  Social cards that omit
    the requested character/costume/cosplay evidence are not accepted blindly;
    Xiaohongshu callers may resolve them by opening the visible detail page and
    re-running this function with the detail text/tags.
    """
    title = _normal(str(record.get("t") or ""))
    desc = _normal(str(record.get("desc") or ""))
    author = _normal(str(record.get("author") or ""))
    full_text = _normal(str(record.get("full_text") or ""))
    page = _normal(str(record.get("purl") or ""))
    combined = f" {title} {desc} {author} {full_text} {page} "

    for marker in NEGATIVE_TYPE_MARKERS:
        if marker.lower() in combined:
            return False, f"negative_type:{marker}"

    char_aliases = _character_aliases(policy["character"])
    has_character = any(a in combined for a in char_aliases) if char_aliases else True
    costume = _normal(policy["costume"])
    has_costume = (costume in combined) if costume else True
    has_cosplay = any(marker in combined for marker in POSITIVE_COSPLAY_MARKERS)

    is_social = any(host in page for host in ("xiaohongshu.com", "pinterest.com", "xhslink.com"))
    if is_social:
        missing: list[str] = []
        if policy["require_cosplay"] and not has_cosplay:
            missing.append("cosplay")
        if policy["require_character"] and not has_character:
            # A literal match on the specifically requested costume plus an
            # explicit cosplay/photo signal is enough for discovery admission.
            # This is not a visual identity PASS; preflight remains uncertain.
            has_specific_costume_signal = (
                policy["require_costume"] and has_costume and has_cosplay
            )
            if not has_specific_costume_signal:
                missing.append("character")
        if policy["require_costume"] and not has_costume:
            missing.append("costume")
        if missing:
            return False, "needs_detail_evidence:" + ",".join(missing)
        return True, "accepted_social_metadata"

    if policy["require_cosplay"] and not has_cosplay:
        return False, "missing_cosplay_evidence"
    if policy["require_character"] and not has_character:
        return False, "missing_character"
    if policy["require_costume"] and not has_costume:
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
    if not raw or len(raw) < 1_000:
        return False, "", "file_too_small"
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            if getattr(image, "n_frames", 1) != 1:
                return False, "", "animated_or_multiframe"
            width, height = image.size
            if max(width, height) < 600 or min(width, height) < 240:
                return False, "", "too_small"
            aspect = width / height
            if aspect < 0.45 or aspect > 2.2:
                return False, "", "extreme_aspect_ratio"
            if policy["portrait_only"] and height <= width:
                return False, "", "not_portrait"
            fmt = (image.format or "").lower()
            if fmt not in {"jpeg", "jpg", "png", "webp"}:
                return False, "", "unsupported_format"
            ext = "jpg" if fmt in {"jpeg", "jpg"} else fmt
            dhash = compute_dhash(image)

            # Sanity check: detect solid pure-white e-commerce backgrounds (mannequins, product catalogs)
            # and solid text screenshots (notes, chat screenshots)
            rgb = image.convert("RGB")
            thumb = rgb.resize((64, 64), Image.Resampling.BOX)
            pixels = list(thumb.get_flattened_data() if hasattr(thumb, "get_flattened_data") else thumb.getdata())
            total_px = len(pixels)
            near_whites = sum(1 for (r, g, b) in pixels if r > 240 and g > 240 and b > 240)
            white_ratio = near_whites / total_px
            if white_ratio > 0.60:
                return False, "", "ecommerce_white_background_or_document"

            return True, ext, dhash
    except Exception:
        return False, "", "invalid_image"


def process_and_expand_image(
    img_bytes: bytes,
    ext: str,
    meta: dict,
    seen_shas: set[str],
    seen_dhashes: list[str],
    allow_split: bool = True,
) -> list[tuple[str, bytes, dict]]:
    """Check image for multi-panel collage layout and split into individual action cards.

    If CollageSplitter recognizes the image as a multi-grid collage, it slices out
    each sub-panel, applies high-DPI super-sampling/sharpening, and returns independent
    candidate items. Otherwise, returns the original image.
    """
    items = []
    split_done = False

    if allow_split and CollageSplitter is not None:
        try:
            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                pil_img_rgb = pil_img.convert("RGB")
                res = CollageSplitter().split(pil_img_rgb)
                sub_imgs = res.get("sub_images") or []
                if res.get("is_collage") and len(sub_imgs) > 1:
                    orig_title = meta.get("title", "")
                    valid_slices = []
                    for idx, sub_img in enumerate(sub_imgs):
                        sw, sh = sub_img.size
                        if sw < 200 or sh < 200:
                            continue
                        sub_aspect = sw / sh
                        if sub_aspect < 0.48 or sub_aspect > 2.1:
                            continue
                        valid_slices.append((idx, sub_img))
                        if len(valid_slices) >= 2:
                            break

                    for idx, sub_img in valid_slices:
                        sw, sh = sub_img.size
                        scale = max(1, int(round(650.0 / max(sw, sh))))
                        if scale > 1:
                            target_w = sw * scale
                            target_h = sh * scale
                            hi_res = sub_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            hi_res = hi_res.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))
                            out_img = ImageEnhance.Contrast(hi_res).enhance(1.05)
                        else:
                            out_img = sub_img

                        buf = io.BytesIO()
                        save_fmt = "JPEG" if ext.lower() in ("jpg", "jpeg") else ext.upper()
                        if save_fmt not in ("JPEG", "PNG", "WEBP"):
                            save_fmt = "JPEG"
                        out_img.save(buf, format=save_fmt, quality=95)
                        sub_bytes = buf.getvalue()

                        sub_sha = hashlib.sha256(sub_bytes).hexdigest()
                        sub_dhash = compute_dhash(out_img)
                        if sub_sha in seen_shas or any(hamming_distance(sub_dhash, old) <= 3 for old in seen_dhashes):
                            continue
                        seen_shas.add(sub_sha)
                        seen_dhashes.append(sub_dhash)

                        sub_fn = f"{sub_sha[:16]}.{ext}"
                        sub_title = f"【动作#{idx+1:02d}】{orig_title}"[:350]
                        sub_meta = dict(meta)
                        sub_meta["title"] = sub_title
                        if "source" in sub_meta and isinstance(sub_meta["source"], dict):
                            sub_meta["source"] = dict(sub_meta["source"])
                            sub_meta["source"]["obtained_as"] = "platform_variant"
                        sub_meta["discovery_reason"] = (
                            meta.get("discovery_reason", "") + f" (从多宫格拼图自动拆解动作#{idx+1:02d})"
                        )[:400]
                        items.append((sub_fn, sub_bytes, sub_meta))
                    if items:
                        split_done = True
        except Exception:
            split_done = False

    if not split_done:
        sha = hashlib.sha256(img_bytes).hexdigest()
        with Image.open(io.BytesIO(img_bytes)) as pil_img:
            dhash = compute_dhash(pil_img)
        if sha not in seen_shas and not any(hamming_distance(dhash, old) <= 3 for old in seen_dhashes):
            seen_shas.add(sha)
            seen_dhashes.append(dhash)
            fn = f"{sha[:16]}.{ext}"
            items.append((fn, img_bytes, meta))

    return items


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
                title = str(record.get("t") or record.get("desc") or f"{policy['character']} {policy['costume']} 参考")[:350]
                desc = str(record.get("desc") or "")[:800]
                base_meta = {
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
                }
                expanded_items = process_and_expand_image(image_bytes, ext, base_meta, seen_shas, seen_dhashes, allow_split=False)
                if not expanded_items:
                    rejected_duplicate += 1
                    continue

                for fn, raw_data, cand_meta in expanded_items:
                    images[fn] = raw_data
                    cand_meta["id"] = f"cand-{len(candidates) + 1:03d}"
                    cand_meta["file"] = f"images/{fn}"
                    candidates.append(cand_meta)
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


def bsk_candidates() -> list[str]:
    """Every BrowserSkill binary worth probing, without username-specific paths.

    Windows is the primary runtime, so PATH and the current user's ~/.local/bin
    are preferred.  WSL/Linux remains a compatibility path and may probe a
    Windows user's mounted bsk.exe, but availability is still proven later by
    `browsers --json`, never by file existence alone.
    """
    found: list[str] = []

    def add(path: str | None) -> None:
        if path and path not in found and os.path.isfile(path):
            found.append(path)

    for name in ("bsk", "bsk.exe"):
        add(shutil.which(name))

    home = Path.home()
    add(str(home / ".local" / "bin" / ("bsk.exe" if os.name == "nt" else "bsk")))

    if os.name != "nt":
        windows_users = Path("/mnt/c/Users")
        if windows_users.is_dir():
            for candidate in sorted(windows_users.glob("*/.local/bin/bsk.exe")):
                add(str(candidate))

    return found


def probe_bsk_browsers(bsk_bin: str, env: dict[str, str], timeout: int = 8) -> list[dict]:
    """Browsers this specific binary can actually see right now."""
    try:
        completed = subprocess.run(
            [bsk_bin, "browsers", "--json"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env, timeout=timeout,
        )
        browsers = json.loads(completed.stdout)
        return browsers if isinstance(browsers, list) else []
    except Exception:
        return []


def _pick_browser(browsers: list[dict]) -> str | None:
    for browser in browsers:
        if browser.get("browser_name") == "edge":
            return browser.get("instance_id")
    if os.name == "nt":
        # Windows primary runtime is Edge. Never silently fall back to Chrome
        # where user credentials/profiles do not exist.
        return None
    return browsers[0].get("instance_id") if browsers else None


def select_browserskill(env: dict[str, str] | None = None) -> tuple[str | None, str | None]:
    """Return the first (binary, browser id) pair that reaches a live browser.

    Existence is not availability: every candidate is probed until one actually
    reports a connected browser.  Returns (None, None) when none can, so the
    caller can report the real reason instead of quietly searching elsewhere.
    """
    env = env or {**os.environ, "BSK_AUTO_START": "0"}
    for candidate in bsk_candidates():
        browser_id = _pick_browser(probe_bsk_browsers(candidate, env))
        if browser_id:
            return candidate, browser_id
    return None, None


def nudge_extension(env: dict[str, str], candidates: list[str]) -> tuple[str | None, str | None]:
    """Last resort: open the extension page once, then re-probe candidates."""
    powershell_bin = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell_bin:
        return None, None
    try:
        subprocess.run(
            [powershell_bin, "-Command",
             "Start-Process msedge.exe extension://emacgiaaaiojkkpkddmmdfhmokgmnikg/popup.html"],
            capture_output=True, timeout=5,
        )
        for _ in range(5):
            time.sleep(1)
            for candidate in candidates:
                browser_id = _pick_browser(probe_bsk_browsers(candidate, env))
                if browser_id:
                    return candidate, browser_id
    except Exception:
        pass
    return None, None


# A note page carries a note id; the keyword search page does not.  Real
# Xiaohongshu note links are also only readable while their xsec_token is
# present, so accept either link form but never the aggregate search page.
_XHS_NOTE_URL = re.compile(r"xiaohongshu\.com/(?:explore|search_result)/[0-9a-f]{16,32}(?:[/?#]|$)")


def _is_note_url(page_url: str) -> bool:
    return bool(_XHS_NOTE_URL.search(page_url or ""))


def wait_for_cards(
    bsk_bin: str, session_id: str, extract_js: str, env: dict[str, str],
    attempts: int = 5, delay: float = 2.0, settle: int = 1,
) -> list[dict]:
    """Poll the search page until its lazily-loaded cover images actually appear.

    A fixed sleep is a race: Xiaohongshu renders result cards over time, and a
    page sampled too early yields almost nothing, which looks identical to
    "no matches" and silently produced empty batches.  Stop once the card
    count stops growing, so a healthy page is not taxed the full budget.
    """
    best: list[dict] = []
    stable = 0
    for attempt in range(attempts):
        if attempt:
            time.sleep(delay)
        completed = subprocess.run(
            [bsk_bin, "evaluate", "--session", session_id, "--json", extract_js],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, timeout=15,
        )
        try:
            raw = json.loads(completed.stdout)
        except Exception:
            raw = None
        cards = raw.get("value", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        if not isinstance(cards, list):
            cards = []
        if len(cards) > len(best):
            best = cards
            stable = 0
        elif best:
            # Still nothing new, but only give up once cards have appeared:
            # an empty first sample usually just means the page is still
            # rendering, not that there were no results.
            stable += 1
            if stable >= settle:
                break
    return best


def fetch_xhs_detail_metadata(
    bsk_bin: str, session_id: str, page_url: str, env: dict[str, str]
) -> dict:
    """Read visible Xiaohongshu detail metadata and gallery image URLs for a note.

    Extracts note title, description, tags, body, and all high-resolution image
    URLs in the note gallery (via window.__INITIAL_STATE__.note.noteDetailMap,
    falling back to DOM slider elements).
    """
    if not _is_note_url(page_url):
        # Never inspect the search-result page as if it were one note: its
        # aggregate text/tags could incorrectly validate an unrelated card.
        return {}
    try:
        subprocess.run(
            [bsk_bin, "navigate", page_url, "--session", session_id,
             "--wait-until", "domcontentloaded", "--timeout", "25s"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, timeout=30,
        )
        time.sleep(2.0)
        js = """(() => {
            let noteTitle = '';
            let noteDesc = '';
            const gallery_urls = [];
            try {
                const state = window.__INITIAL_STATE__;
                if (state?.note?.noteDetailMap) {
                    for (const k of Object.keys(state.note.noteDetailMap)) {
                        const note = state.note.noteDetailMap[k]?.note;
                        if (note) {
                            if (note.title && !noteTitle) noteTitle = note.title;
                            if (note.desc && !noteDesc) noteDesc = note.desc;
                            if (note.imageList) {
                                for (const img of note.imageList) {
                                    const u = img.urlDefault || (img.infoList && img.infoList[1]?.url) || (img.infoList && img.infoList[0]?.url);
                                    if (u && !gallery_urls.includes(u)) {
                                        gallery_urls.push(u);
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (e) {}

            const title = noteTitle || document.querySelector('#detail-title, .title')?.innerText?.trim() || '';
            const desc = noteDesc || document.querySelector('#detail-desc, .desc, .content')?.innerText?.trim() || '';
            const tags = Array.from(document.querySelectorAll('a[href*="/search_result/"]'))
                .map(a => a.innerText?.trim() || '')
                .filter(Boolean);
            const root = document.querySelector('.note-container, [role="dialog"], .note-scroller');
            const body = root?.innerText?.trim() || '';

            if (gallery_urls.length === 0) {
                const domImgs = Array.from(document.querySelectorAll('.swiper-slide img, .note-slider img, .media-container img, .note-container img'))
                    .map(i => i.currentSrc || i.src)
                    .filter(u => u && u.includes('xhscdn.com') && !u.includes('avatar'));
                for (const u of domImgs) {
                    if (!gallery_urls.includes(u)) gallery_urls.push(u);
                }
            }

            return {
                title,
                desc,
                tags,
                body: body.slice(0, 2400),
                purl: location.href,
                gallery_urls
            };
        })()"""
        p = subprocess.run(
            [bsk_bin, "evaluate", "--session", session_id, "--json", js],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, timeout=10,
        )
        payload = json.loads(p.stdout)
        value = payload.get("value", {}) if isinstance(payload, dict) else {}
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def download_gallery_images(
    bsk_bin: str, session_id: str, urls: list[str], env: dict[str, str], timeout: int = 30
) -> list[dict]:
    """Download multiple images concurrently in browser context via fetch."""
    if not urls:
        return []
    fetch_js = f"""(async () => {{
        const urls = {json.dumps(urls)};
        const downloaded = [];
        for (const u of urls) {{
            try {{
                const resp = await fetch(u);
                if (!resp.ok) continue;
                const blob = await resp.blob();
                const b64 = await new Promise((resolve) => {{
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.readAsDataURL(blob);
                }});
                if (b64 && b64.includes(',')) {{
                    downloaded.push({{ url: u, data: b64 }});
                }}
            }} catch (e) {{}}
        }}
        return downloaded;
    }})()"""
    try:
        p = subprocess.run(
            [bsk_bin, "evaluate", "--session", session_id, "--json", fetch_js],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, timeout=timeout
        )
        val = json.loads(p.stdout)
        items = val.get("value", []) if isinstance(val, dict) else []
        return items if isinstance(items, list) else []
    except Exception:
        return []


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
    note_kept_counts: dict[str, int] = {}
    note_dhashes: dict[str, list[str]] = {}

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
                    const link = item.querySelector('a[href*="xsec_token"]')
                        || item.querySelector('a[href*="/explore/"]')
                        || item.querySelector('a[href*="/search_result/"]');
                    const titleEl = item.querySelector('.title, .desc, a.title span, span.title') || item.querySelector('a:not(.user) span');
                    const authorEl = item.querySelector('.author, .name, .user-name, a.user span');
                    if (img && (img.currentSrc || img.src)) {
                        const src = img.currentSrc || img.src;
                        if (src.includes('xhscdn.com') && !src.includes('avatar') && img.naturalWidth >= 180) {
                            cards.push({
                                title: titleEl?.innerText?.trim() || img.alt?.trim() || '',
                                author: authorEl?.innerText?.trim() || '',
                                full_text: item.innerText?.trim() || '',
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

            cards = wait_for_cards(bsk_bin, session_id, extract_js, env)

            detail_checks = 0
            max_detail_checks = max(8, min(24, target_count * 3))
            for card in cards:
                if len(candidates) >= target_count:
                    break
                card_purl = str(card.get("purl") or "").strip()
                record = {
                    "t": card["title"],
                    "desc": card["desc"],
                    "author": card.get("author", ""),
                    "full_text": card.get("full_text", ""),
                    "purl": card_purl,
                }
                allowed, reason = result_metadata_allowed(record, policy)

                detail = None
                # A voice-line/poetic title may omit the character and cosplay
                # words on the search card.  Resolve only those ambiguous XHS
                # cards by opening the visible detail page and using its body /
                # hashtags; never accept merely because search returned it.
                if (
                    not allowed
                    and reason.startswith("needs_detail_evidence:")
                    and detail_checks < max_detail_checks
                    and _is_note_url(card_purl)
                ):
                    detail_checks += 1
                    detail = fetch_xhs_detail_metadata(
                        bsk_bin, session_id, card_purl, env
                    )
                    if detail:
                        detail_text = " ".join([
                            str(detail.get("desc") or ""),
                            " ".join(str(x) for x in (detail.get("tags") or [])),
                            str(detail.get("body") or ""),
                        ])
                        record = {
                            **record,
                            "t": str(detail.get("title") or record["t"]),
                            "desc": str(detail.get("desc") or record["desc"]),
                            "full_text": f"{record['full_text']} {detail_text}",
                            "purl": str(detail.get("purl") or record["purl"]),
                        }
                        allowed, reason = result_metadata_allowed(record, policy)

                if not allowed:
                    rejected_metadata += 1
                    continue

                downloaded_batch = []
                if _is_note_url(card_purl):
                    if detail is None:
                        detail = fetch_xhs_detail_metadata(
                            bsk_bin, session_id, card_purl, env
                        )
                    gallery_urls = [u for u in detail.get("gallery_urls", []) if u and u not in seen_urls]
                    if gallery_urls:
                        urls_to_fetch = gallery_urls[:min(len(gallery_urls), 8)]
                        downloaded_batch = download_gallery_images(
                            bsk_bin, session_id, urls_to_fetch, env, timeout=20
                        )

                # Fallback to single card cover image if gallery extraction was empty or failed
                if not downloaded_batch:
                    cover_url = card.get("image_url", "").strip()
                    if cover_url and cover_url not in seen_urls:
                        downloaded_batch = download_gallery_images(
                            bsk_bin, session_id, [cover_url], env, timeout=15
                        )

                if not downloaded_batch:
                    rejected_image += 1
                    continue

                total_downloaded = len(downloaded_batch)
                raw_title = str(detail.get("title") if detail else None) or str(card.get("title")) or f"{policy['character']} 小红书参考"
                raw_title = raw_title[:350]
                note_desc = str(detail.get("desc") if detail else None) or str(card.get("desc") or "")
                note_page_url = str(detail.get("purl") if detail else None) or card_purl or xhs_url
                clean_note_url = note_page_url.split("?")[0] if "?" in note_page_url else note_page_url

                for img_idx, item in enumerate(downloaded_batch):
                    if len(candidates) >= target_count:
                        break
                    img_url = item.get("url") or ""
                    b64_data = item.get("data") or ""
                    if not b64_data or "," not in b64_data:
                        rejected_image += 1
                        continue
                    seen_urls.add(img_url)

                    try:
                        img_bytes = base64.b64decode(b64_data.split(",", 1)[1])
                    except Exception:
                        rejected_image += 1
                        continue

                    valid, ext, dhash = validate_downloaded_image(img_bytes, policy)
                    if not valid:
                        rejected_image += 1
                        continue

                    # Secondary slide filtering (P2, P3...):
                    # Filter out micro-burst duplicate shots (hamming distance < 6)
                    if img_idx > 0:
                        prev_dhashes = note_dhashes.get(clean_note_url, [])
                        if prev_dhashes and any(hamming_distance(dhash, old_dh) < 6 for old_dh in prev_dhashes):
                            rejected_duplicate += 1
                            continue

                    card_title = f"{raw_title} (P{img_idx+1}/{total_downloaded})" if total_downloaded > 1 else raw_title
                    disc_reason = (
                        f"通过 BrowserSkill 检索「{query}」在小红书图集发现 (P{img_idx+1}/{total_downloaded})"
                        if total_downloaded > 1
                        else f"通过 BrowserSkill 检索「{query}」在小红书发现"
                    )

                    base_meta = {
                        "title": card_title,
                        "source": {
                            "page_url": note_page_url[:2000],
                            "image_url": img_url[:2000],
                            "author": str(card.get("author") or "")[:200],
                            "title": card_title,
                            "search_query": query[:350],
                            "rights": "unknown",
                            "source_confirmed": False,
                            "obtained_as": "platform_variant",
                        },
                        "discovery_intent": "exact_character" if policy["require_cosplay"] else "transferable_pose",
                        "discovery_reason": disc_reason,
                        "discovery_url": xhs_url[:2000],
                        "notes": note_desc[:800],
                    }

                    expanded_items = process_and_expand_image(img_bytes, ext, base_meta, seen_shas, seen_dhashes, allow_split=False)
                    if not expanded_items:
                        rejected_duplicate += 1
                        continue

                    for fn, raw_data, cand_meta in expanded_items:
                        if len(candidates) >= target_count:
                            break
                        images[fn] = raw_data
                        cand_meta["id"] = f"cand-{len(candidates) + 1:03d}"
                        cand_meta["file"] = f"images/{fn}"
                        candidates.append(cand_meta)
                        kept += 1
                        note_kept_counts[clean_note_url] = note_kept_counts.get(clean_note_url, 0) + 1
                        note_dhashes.setdefault(clean_note_url, []).append(dhash)

            query_log.append({
                "query": query,
                "source": "xiaohongshu",
                "kept": kept,
                "stop_reason": (
                    f"kept={kept}; metadata_filtered={rejected_metadata}; "
                    f"detail_checked={detail_checks}; "
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

                pins = wait_for_cards(bsk_bin, session_id, pin_js, env)

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

                    title = str(pin.get("title") or f"{policy['character']} Pinterest 参考")[:350]
                    desc = str(pin.get("desc") or "")[:800]
                    base_meta = {
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
                    }
                    expanded_items = process_and_expand_image(img_bytes, ext, base_meta, seen_shas, seen_dhashes, allow_split=False)
                    if not expanded_items:
                        rejected_duplicate += 1
                        continue

                    for fn, raw_data, cand_meta in expanded_items:
                        images[fn] = raw_data
                        cand_meta["id"] = f"cand-{len(candidates) + 1:03d}"
                        cand_meta["file"] = f"images/{fn}"
                        candidates.append(cand_meta)
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
    task_path, result_file, allow_bing_fallback = parse_arguments()
    job, _ = load_job_info(task_path)
    policy = build_policy(job)
    target_count = min(int(job.get("target_count") or 30), 40)

    candidates: list[dict] = []
    images: dict[str, bytes] = {}
    query_log: list[dict] = []
    source_checks: list[dict] = []
    producer = "local_collection_adapter_search_only"

    # 1. 使用真正连得上浏览器的 BrowserSkill (小红书 + Pinterest)
    env = {**os.environ, "BSK_AUTO_START": "0"}
    bsk_bin, browser_id = select_browserskill(env)
    if not bsk_bin:
        bsk_bin, browser_id = nudge_extension(env, bsk_candidates())
    if bsk_bin and browser_id:
        producer = "local_browserskill_adapter"
        candidates, images, query_log = fetch_bsk_candidates(
            bsk_bin, browser_id, job, target_count, policy
        )
        source_checks.append({
            "source": "xiaohongshu",
            "status": "usable" if any(q.get("source") == "xiaohongshu" and q.get("kept", 0) > 0 for q in query_log) else "untested",
            "detail": "通过本地 BrowserSkill Edge 实例访问小红书检索真人参考。",
        })
        source_checks.append({
            "source": "pinterest",
            "status": "usable" if any(q.get("source") == "pinterest" and q.get("kept", 0) > 0 for q in query_log) else "untested",
            "detail": "在小红书后通过 BrowserSkill 访问 Pinterest 补充参考。",
        })

    # 2. 没有可用浏览器时不得静默改用 Bing：本任务要求小红书真人 COS 正片，
    #    Bing 结果不是同一个来源，悄悄替换会让受阻看起来像搜到了。
    browserskill_missing = ""
    if not (bsk_bin and browser_id):
        browserskill_missing = (
            "BrowserSkill 没有可用的浏览器：已探测 " + (
                "、".join(bsk_candidates()) or "（未找到任何 bsk 可执行文件）"
            ) + "，但没有一个能连上已装扩展的浏览器。"
            "请启动带 BrowserSkill 扩展的 Edge 并确认 bsk doctor 全部 ok；"
            "只有明确接受 Bing 备用检索时才使用 --allow-bing-fallback。"
        )
        source_checks.append({
            "source": "browserskill",
            "status": "blocked",
            "detail": browserskill_missing,
        })
        if not allow_bing_fallback:
            sys.stderr.write(browserskill_missing + "\n")
        else:
            queries = build_queries(job, for_browser=False)
            candidates, images, query_log = fetch_bing_candidates(queries, target_count, policy)
            source_checks.append({
                "source": "bing_images_photo_filter",
                "status": "usable" if candidates else "untested",
                "detail": "调用方显式允许 Bing 备用检索；这不是小红书来源。",
            })

    summary_text = (
        f"严格检索得到 {len(candidates)} 个候选；未运行视觉模型，未宣称角色/模态已通过。"
        if candidates else
        (browserskill_missing if browserskill_missing
         else "严格检索没有得到满足硬条件的候选；宁可少图，不用插画/游戏图凑数。")
    )
    gaps = (
        [browserskill_missing] if browserskill_missing
        else ([] if candidates else ["没有足够满足用户硬要求的候选；请调整搜索词或改用人工检索。"])
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
            "gaps": gaps,
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
