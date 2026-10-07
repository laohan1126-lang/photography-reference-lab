"""Read-only, private UI-prototype assets. No Library, models or database writes."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

STATIC_FILES = {"learning.css", "learning.js", "learning-icons.json", "learning-atlas.json"}


def preview_router(web_dir: Path) -> APIRouter:
    router = APIRouter()
    samples = web_dir.parent / ".local" / "learning-preview"

    @router.get("/learning")
    def learning_page():
        return FileResponse(web_dir / "learning.html", media_type="text/html",
                            headers={"Cache-Control": "no-cache"})

    # The application's /api middleware supplies the existing authentication.
    # The standalone preview only binds loopback and exposes this explicit set.
    @router.get("/api/learning-preview")
    def learning_manifest():
        path = samples / "manifest.json"
        if not path.is_file():
            return JSONResponse({"items": []})
        if path.is_symlink():
            raise HTTPException(404)
        return FileResponse(path, media_type="application/json", headers={"Cache-Control": "no-store"})

    @router.get("/api/learning-preview/{filename}")
    def learning_image(filename: str):
        if not re.fullmatch(r"P[0-9]+\.(?:jpg|jpeg|png|webp|avif)", filename):
            raise HTTPException(404)
        path = samples / filename
        if not path.is_file() or path.is_symlink() or path.resolve().parent != samples.resolve():
            raise HTTPException(404)
        return FileResponse(path, headers={"Cache-Control": "private, no-store"})

    return router
