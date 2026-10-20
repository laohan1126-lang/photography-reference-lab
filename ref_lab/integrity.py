"""Cheap, cached content verification for polling views.

The candidate queue is polled about once per second. Re-reading every original
and every derived tile on each poll would be both slow and pointless: a file only
changes when its size or modification time changes. Results are therefore cached
by ``(resolved path, size, mtime_ns)`` and invalidated automatically when the
file changes.

This is only a view-level optimisation. Opening an image for display still reads
its bytes and compares the full SHA (``collection_queue.original_bytes``); the
cache never authorises serving changed content.
"""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path

_LOCK = threading.RLock()
_CACHE: dict[str, dict] = {}


def _stat_key(path: Path) -> dict | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        stat = path.stat()
    except OSError:
        return None
    return {"size": int(stat.st_size), "mtime_ns": int(stat.st_mtime_ns)}


def file_sha(path: Path) -> str | None:
    """Full SHA-256 of the current bytes, or ``None`` when unreadable."""
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    sha = hashlib.sha256(raw).hexdigest()
    stat = _stat_key(path)
    if stat is not None:
        with _LOCK:
            _CACHE[str(path)] = {**stat, "sha": sha}
    return sha


def sha_matches(path, expected: str) -> bool:
    """True only when the file currently hashes to ``expected``.

    The hash is reused while the file's size and mtime are unchanged; a changed
    file is re-hashed instead of trusting the previous result.
    """
    path = Path(path)
    expected = str(expected or "")
    if not expected:
        return False
    stat = _stat_key(path)
    if stat is None:
        return False
    key = str(path)
    with _LOCK:
        cached = _CACHE.get(key)
    if cached and cached.get("size") == stat["size"] and cached.get("mtime_ns") == stat["mtime_ns"]:
        return cached.get("sha") == expected
    return file_sha(path) == expected


def reset_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def cache_entries() -> int:
    with _LOCK:
        return len(_CACHE)
