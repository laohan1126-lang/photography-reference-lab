#!/usr/bin/env python3
"""Download and catalog reference images for photography projects."""

import csv
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_DIR = ROOT / "references" / "changye-huansheng"
INDEX_CSV = REF_DIR / "index.csv"

import ssl

def get_ssl_context():
    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()

CSV_COLUMNS = [
    "ID",
    "filename",
    "category",
    "resolution",
    "suitable_for",
    "feasibility",
    "source_url",
    "image_url",
    "author",
    "search_keyword",
    "value_notes",
    "added_at"
]

def ensure_index_csv():
    if not INDEX_CSV.exists():
        REF_DIR.mkdir(parents=True, exist_ok=True)
        with open(INDEX_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)

def get_image_info(data: bytes) -> tuple[str, int, int]:
    # Check WebP
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        riff_end = int.from_bytes(data[4:8], "little") + 8
        offset = 12
        while offset < min(len(data), riff_end):
            kind = data[offset : offset + 4]
            size = int.from_bytes(data[offset + 4 : offset + 8], "little")
            start = offset + 8
            chunk = data[start : start + size]
            if kind == b"VP8X" and size >= 10:
                w = 1 + int.from_bytes(chunk[4:7], "little")
                h = 1 + int.from_bytes(chunk[7:10], "little")
                return "webp", w, h
            elif kind == b"VP8L" and size >= 5 and chunk[0] == 0x2F:
                b1, b2, b3, b4 = chunk[1:5]
                w = 1 + (((b2 & 0x3F) << 8) | b1)
                h = 1 + (((b4 & 0xF) << 10) | (b3 << 2) | ((b2 & 0xC0) >> 6))
                return "webp", w, h
            elif kind == b"VP8 " and size >= 10:
                w = int.from_bytes(chunk[6:8], "little") & 0x3FFF
                h = int.from_bytes(chunk[8:10], "little") & 0x3FFF
                return "webp", w, h
            offset += 8 + size + (size & 1)
        return "webp", 0, 0
    # Check JPEG
    elif len(data) >= 2 and data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i+1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h = int.from_bytes(data[i+5:i+7], "big")
                w = int.from_bytes(data[i+7:i+9], "big")
                return "jpeg", w, h
            length = int.from_bytes(data[i+2:i+4], "big")
            i += 2 + length
        return "jpeg", 0, 0
    # Check PNG
    elif len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        w = int.from_bytes(data[16:20], "big")
        h = int.from_bytes(data[20:24], "big")
        return "png", w, h
    return "unknown", 0, 0

def add_reference(
    category_subdir: str,
    ref_id: str,
    image_url: str,
    source_url: str,
    author: str,
    search_keyword: str,
    suitable_for: list[str],
    feasibility: str,
    value_notes: str,
    filename_override: str = None
) -> dict:
    ensure_index_csv()
    target_dir = REF_DIR / category_subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(image_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = res.read()
    except Exception:
        import ssl
        unverified_ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=unverified_ctx, timeout=30) as res:
            data = res.read()

    ext, width, height = get_image_info(data)
    if ext == "unknown":
        ext = "jpg"

    if filename_override:
        filename = f"{filename_override}.{ext}" if not filename_override.endswith(f".{ext}") else filename_override
    else:
        filename = f"{ref_id}.{ext}"

    dest_path = target_dir / filename
    with open(dest_path, "wb") as f:
        f.write(data)

    res_str = f"{width}x{height}" if width and height else "unknown"

    record = [
        ref_id,
        f"{category_subdir}/{filename}",
        category_subdir,
        res_str,
        ";".join(suitable_for),
        feasibility,
        source_url,
        image_url,
        author,
        search_keyword,
        value_notes,
        datetime.now(timezone.utc).isoformat(timespec="seconds")
    ]

    with open(INDEX_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(record)

    print(f"[{ref_id}] Saved {filename} ({res_str}, {len(data)} bytes) to {category_subdir}/")
    return {
        "id": ref_id,
        "file": f"{category_subdir}/{filename}",
        "resolution": res_str,
        "size_bytes": len(data)
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            add_reference(**item)
