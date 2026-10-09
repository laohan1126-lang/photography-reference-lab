"""Private, hash-checked serving for teaching frames linked from learning notes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response


_MEDIA_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _is_redirect(path: Path) -> bool:
    junction_check = getattr(path, "is_junction", None)
    return path.is_symlink() or (callable(junction_check) and junction_check())


def router(web_dir: Path) -> APIRouter:
    """Serve only media named in this checkout's generated learning bundle."""
    web_dir = Path(web_dir)
    local_dir = web_dir.parent / ".local"
    media_dir = local_dir / "learning-note-media"
    api = APIRouter()

    @api.get("/api/learning-note-media/{media_id}")
    def note_media(media_id: str):
        if not _MEDIA_ID.fullmatch(media_id):
            raise HTTPException(404)
        bundle = web_dir / "learning-atlas.json"
        try:
            payload = json.loads(bundle.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise HTTPException(404)
        content = payload.get("learning_content", {}) if isinstance(payload, dict) else {}
        entries = content.get("media", []) if isinstance(content, dict) else []
        if not isinstance(entries, list):
            raise HTTPException(404)
        matches = [entry for entry in entries
                   if isinstance(entry, dict) and entry.get("id") == media_id]
        if len(matches) != 1:
            raise HTTPException(404)
        entry = matches[0]
        digest = entry.get("sha256")
        filename = entry.get("filename")
        if (not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                or filename not in {f"{digest}.jpg", f"{digest}.png"}):
            raise HTTPException(404)
        formats = {
            ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
            ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
        }
        extension = Path(filename).suffix
        magic, media_type = formats[extension]

        # The directory and filename are fixed by code and the digest-checked bundle.
        # Reject symlinked components and verify containment before reading bytes.
        if _is_redirect(local_dir) or _is_redirect(media_dir) or not media_dir.is_dir():
            raise HTTPException(404)
        path = media_dir / filename
        if _is_redirect(path):
            raise HTTPException(404)
        try:
            local_root = local_dir.resolve(strict=True)
            media_root = media_dir.resolve(strict=True)
            resolved = path.resolve(strict=True)
            if (media_root != local_root / "learning-note-media"
                    or resolved.parent != media_root or not resolved.is_file()):
                raise HTTPException(404)
            body = resolved.read_bytes()
        except (OSError, RuntimeError):
            raise HTTPException(404)
        if not body.startswith(magic) or hashlib.sha256(body).hexdigest() != digest:
            raise HTTPException(404)
        return Response(body, media_type=media_type,
                        headers={"Cache-Control": "private, no-store",
                                 "X-Content-Type-Options": "nosniff"})

    return api
