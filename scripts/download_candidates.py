#!/usr/bin/env python3
"""Download previously observed Xiaohongshu image URLs in small batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
WORKERS = 4
MAX_BYTES = 16 * 1024 * 1024

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
SECRET_QUERY_KEYS = {"auth", "authorization", "access_token", "cookie", "secret", "sign", "signature", "token", "xsec_token"}


def workspace_path(value: str) -> Path:
    path = Path(value)
    path = (ROOT / path if not path.is_absolute() else path).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as error:
        raise ValueError("paths must stay inside the workspace") from error
    return path


def validate_url(value: str, *, image: bool) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("URLs must be copied exactly, without surrounding whitespace")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise ValueError("invalid URL") from error

    host = (parts.hostname or "").lower()
    allowed = (
        host == "xhscdn.com" or host.endswith(".xhscdn.com")
        if image
        else host == "xiaohongshu.com" or host.endswith(".xiaohongshu.com")
    )
    if (
        parts.scheme != "https"
        or not allowed
        or parts.username
        or parts.password
        or port not in (None, 443)
        or parts.fragment
        or (not image and (parts.query or not parts.path.startswith("/explore/")))
        or (
            image
            and {key.lower() for key, _ in parse_qsl(parts.query, keep_blank_values=True)}
            & SECRET_QUERY_KEYS
        )
    ):
        raise ValueError("URL is outside the permitted Xiaohongshu source")
    return value


def read_candidates(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"candidate file not found: {path.relative_to(ROOT)}")
    required = ("batch_id", "id", "source_note_title", "source_author", "search_keyword")
    candidates = []
    ids = set()
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"line {number}: invalid JSON") from error
            if not isinstance(item, dict):
                raise ValueError(f"line {number}: expected a JSON object")
            if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required):
                raise ValueError(f"line {number}: batch and source metadata fields are required")

            candidate_id = item["id"].strip()
            id_key = candidate_id.casefold()
            if not ID_PATTERN.fullmatch(candidate_id) or id_key in ids:
                raise ValueError(f"line {number}: invalid or duplicate id")
            ids.add(id_key)
            source_url = validate_url(item.get("source_url"), image=False)
            current_src = validate_url(item.get("currentSrc"), image=True)
            dimensions = (item.get("image_index"), item.get("natural_width"), item.get("natural_height"))
            if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in dimensions):
                raise ValueError(f"line {number}: image index and dimensions must be positive integers")

            candidates.append(
                {
                    **item,
                    "id": candidate_id,
                    "id_key": id_key,
                    "source_url": source_url,
                    "currentSrc": current_src,
                    "url_hash": hashlib.sha256(current_src.encode()).hexdigest(),
                }
            )
    return candidates


def read_history(path: Path) -> tuple[dict, dict]:
    by_id, by_url = {}, {}
    if not path.exists():
        return by_id, by_url
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"download result line {number}: invalid JSON") from error
            if isinstance(record, dict) and record.get("status") in {"downloaded", "skipped_existing"}:
                by_id[str(record.get("id", "")).casefold()] = record
                by_url[record.get("current_src_sha256", "")] = record
    return by_id, by_url


def webp_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 20 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("response is not a WebP file")
    riff_end = int.from_bytes(data[4:8], "little") + 8
    if riff_end != len(data):
        raise ValueError("invalid WebP container length")

    canvas, bitstream = None, None
    offset = 12
    while offset < riff_end:
        if offset + 8 > riff_end:
            raise ValueError("truncated WebP chunk header")
        kind = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        start, end = offset + 8, offset + 8 + size
        padded_end = end + (size & 1)
        if padded_end > riff_end:
            raise ValueError("truncated WebP chunk")
        chunk = data[start:end]

        if kind == b"VP8X":
            if size < 10:
                raise ValueError("truncated WebP VP8X header")
            canvas = (
                1 + int.from_bytes(chunk[4:7], "little"),
                1 + int.from_bytes(chunk[7:10], "little"),
            )
        elif kind == b"VP8L":
            if size < 5 or chunk[0] != 0x2F:
                raise ValueError("invalid WebP VP8L header")
            bits = int.from_bytes(chunk[1:5], "little")
            bitstream = ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        elif kind == b"VP8 ":
            if size < 10 or chunk[3:6] != b"\x9d\x01\x2a":
                raise ValueError("invalid WebP VP8 frame header")
            bitstream = (
                int.from_bytes(chunk[6:8], "little") & 0x3FFF,
                int.from_bytes(chunk[8:10], "little") & 0x3FFF,
            )
        offset = padded_end

    if offset != riff_end or not (canvas or bitstream):
        raise ValueError("WebP image dimensions are unavailable")
    return canvas or bitstream


def file_info(path: Path) -> tuple[str, tuple[int, int]] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            return None
        return hashlib.sha256(data).hexdigest(), webp_dimensions(data)
    except (OSError, ValueError):
        return None


def result(candidate: dict, status: str, local_file: str, **extra) -> dict:
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "id": candidate["id"],
        "batch_id": candidate["batch_id"],
        "status": status,
        "current_src_sha256": candidate["url_hash"],
        "local_file": local_file,
        **extra,
    }


def append_result(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_timing(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        try:
            validate_url(new_url, image=True)
        except ValueError:
            raise HTTPError(new_url, code, "redirect target refused", headers, file)
        return super().redirect_request(request, file, code, message, headers, new_url)


def fetch(current_src: str) -> bytes:
    opener = build_opener(SafeRedirect())
    request = Request(current_src, headers={"Accept": "image/webp"})
    for attempt in range(3):
        try:
            with opener.open(request, timeout=20) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                if response.headers.get_content_type().lower() != "image/webp":
                    raise ValueError("response is not image/webp")
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
                    raise ValueError("response is oversized or not a WebP file")
                return data
        except HTTPError as error:
            error.close()
            if 500 <= error.code < 600 and attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError(f"HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError):
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError("network error after three attempts") from None
    raise ValueError("network error after three attempts")


def download(candidate: dict, target: Path, relative: str) -> dict:
    data = fetch(candidate["currentSrc"])
    width, height = webp_dimensions(data)
    if (width, height) != (candidate["natural_width"], candidate["natural_height"]):
        raise ValueError(
            f"saved dimensions {width}x{height} do not match observed dimensions "
            f"{candidate['natural_width']}x{candidate['natural_height']}"
        )
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".part", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return result(
        candidate,
        "downloaded",
        relative,
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        content_type="image/webp",
        saved_width=width,
        saved_height=height,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="staging/candidates.jsonl")
    parser.add_argument("--out-dir", default="images")
    parser.add_argument("--results", default="staging/download-results.jsonl")
    parser.add_argument("--timings", default="staging/batch-timings.jsonl")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    summary = {
        "stage": "download",
        "batch_ids": [],
        "candidate_count": 0,
        "downloaded": 0,
        "skipped": 0,
        "duplicates": 0,
        "failed": 0,
        "conflicts": 0,
        "bytes_downloaded": 0,
        "status": "ok",
    }
    exit_code = 0
    try:
        candidates = read_candidates(workspace_path(args.input))
        output_dir = workspace_path(args.out_dir)
        results_path = workspace_path(args.results)
        timings_path = workspace_path(args.timings)
        if len({workspace_path(args.input), output_dir, results_path, timings_path}) != 4:
            raise ValueError("input, output, results, and timings paths must be different")
        by_id, by_url = read_history(results_path)
        summary["candidate_count"] = len(candidates)
        summary["batch_ids"] = sorted({item["batch_id"] for item in candidates})
        if not candidates:
            print("No candidate records.")
        else:
            jobs, immediate, pending, duplicates, conflicts = [], [], {}, {}, []
            for candidate in candidates:
                url_hash = candidate["url_hash"]
                target = output_dir / f"{candidate['id'].lower()}.webp"
                relative = target.relative_to(ROOT).as_posix()
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    conflicts.append(f"{candidate['id']}: output is not a regular file")
                    continue
                prior = by_id.get(candidate["id_key"])
                if prior and (
                    prior.get("current_src_sha256") != url_hash
                    or prior.get("local_file") != relative
                ):
                    conflicts.append(f"{candidate['id']}: id already maps to another URL or output path")
                    continue
                if not prior and target.exists():
                    conflicts.append(f"{candidate['id']}: existing output has no matching result checkpoint")
                    continue

                if prior:
                    info = file_info(target)
                    if info and info[0] == prior.get("sha256"):
                        if info[1] != (candidate["natural_width"], candidate["natural_height"]):
                            conflicts.append(f"{candidate['id']}: checkpointed output dimensions do not match candidate")
                            continue
                        immediate.append(
                            result(
                                candidate,
                                "skipped_existing",
                                relative,
                                bytes=target.stat().st_size,
                                sha256=info[0],
                                saved_width=info[1][0],
                                saved_height=info[1][1],
                            )
                        )
                        continue
                else:
                    old_url = by_url.get(url_hash)
                    if old_url:
                        old_path = workspace_path(old_url.get("local_file", ""))
                        info = file_info(old_path)
                        if info and info[0] == old_url.get("sha256"):
                            if info[1] != (candidate["natural_width"], candidate["natural_height"]):
                                conflicts.append(f"{candidate['id']}: duplicate output dimensions do not match candidate")
                                continue
                            immediate.append(
                                result(
                                    candidate,
                                    "duplicate_url",
                                    old_url["local_file"],
                                    duplicate_of=old_url["id"],
                                    bytes=old_path.stat().st_size,
                                    sha256=info[0],
                                    saved_width=info[1][0],
                                    saved_height=info[1][1],
                                )
                            )
                            continue

                if url_hash in pending:
                    duplicates.setdefault(url_hash, []).append((candidate, relative))
                else:
                    pending[url_hash] = candidate
                    jobs.append((candidate, target, relative))

            summary["conflicts"] = len(conflicts)
            if conflicts:
                raise ValueError("; ".join(conflicts))
            output_dir.mkdir(parents=True, exist_ok=True)

            def save(record: dict) -> None:
                append_result(results_path, record)
                status = record["status"]
                if status == "downloaded":
                    summary["downloaded"] += 1
                    summary["bytes_downloaded"] += record.get("bytes", 0)
                elif status == "skipped_existing":
                    summary["skipped"] += 1
                elif status == "duplicate_url":
                    summary["duplicates"] += 1
                elif status == "failed":
                    summary["failed"] += 1
                print(f"{record['id']}: {status}")

            for record in immediate:
                save(record)

            outcomes = {}
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                futures = {pool.submit(download, *job): job for job in jobs}
                for future in as_completed(futures):
                    candidate, target, relative = futures[future]
                    try:
                        record = future.result()
                    except (OSError, ValueError) as error:
                        record = result(candidate, "failed", relative, error=str(error))
                    outcomes[candidate["url_hash"]] = record
                    save(record)

            for url_hash, entries in duplicates.items():
                canonical = outcomes[url_hash]
                for candidate, relative in entries:
                    expected = (candidate["natural_width"], candidate["natural_height"])
                    saved = (canonical.get("saved_width"), canonical.get("saved_height"))
                    if canonical["status"] == "downloaded" and saved == expected:
                        record = result(
                            candidate,
                            "duplicate_url",
                            canonical["local_file"],
                            duplicate_of=canonical["id"],
                            bytes=canonical["bytes"],
                            sha256=canonical["sha256"],
                            saved_width=canonical["saved_width"],
                            saved_height=canonical["saved_height"],
                        )
                    elif canonical["status"] != "downloaded":
                        record = result(
                            candidate,
                            "failed",
                            relative,
                            error=f"duplicate source download failed for {canonical['id']}",
                        )
                    else:
                        record = result(
                            candidate,
                            "failed",
                            relative,
                            error=f"duplicate source dimensions {saved[0]}x{saved[1]} do not match observed dimensions {expected[0]}x{expected[1]}",
                        )
                    save(record)

            print(
                f"Candidates: {len(candidates)}; downloads: {summary['downloaded']}; "
                f"skipped/duplicates: {summary['skipped'] + summary['duplicates']}; "
                f"failed: {summary['failed']}"
            )
            if summary["failed"]:
                summary["status"] = "partial"
                exit_code = 1
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        summary["status"] = "error"
        summary["error"] = str(error)
        exit_code = 2

    summary["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["started_at"] = started_at.isoformat(timespec="seconds")
    summary["elapsed_seconds"] = round(time.monotonic() - started_clock, 3)
    completed = summary["downloaded"] + summary["skipped"] + summary["duplicates"]
    summary["images_per_second"] = round(completed / summary["elapsed_seconds"], 3) if summary["elapsed_seconds"] else 0
    summary["new_downloads_per_second"] = round(summary["downloaded"] / summary["elapsed_seconds"], 3) if summary["elapsed_seconds"] else 0
    try:
        append_timing(workspace_path(args.timings), summary)
    except (OSError, ValueError) as error:
        print(f"Could not write timing summary: {error}", file=sys.stderr)
        exit_code = 2
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
