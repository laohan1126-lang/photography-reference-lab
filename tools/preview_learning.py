"""Serve only the learning UI on loopback, without opening the owner's database.

Run: .venv/Scripts/python.exe tools/preview_learning.py
Private samples live in .local/learning-preview, outside Git and the package.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from ref_lab.learning_preview import STATIC_FILES, preview_router


def make_preview(reference_url: str = "http://127.0.0.1:18766/") -> FastAPI:
    target = urlsplit(reference_url)
    if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost"} or target.username or target.password:
        raise ValueError("The reference workspace must be a local HTTP URL")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.include_router(preview_router(ROOT / "web"))

    @app.get("/")
    def reference():
        return RedirectResponse(reference_url)

    @app.get("/static/{filename}")
    def static(filename: str):
        if filename not in STATIC_FILES:
            raise HTTPException(404)
        return FileResponse(ROOT / "web" / filename, headers={"Cache-Control": "no-cache"})

    return app


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18767)
    parser.add_argument("--reference-url", default="http://127.0.0.1:18766/")
    args = parser.parse_args()
    print(f"UI prototype: http://127.0.0.1:{args.port}/learning", flush=True)
    uvicorn.run(make_preview(args.reference_url), host="127.0.0.1", port=args.port, log_level="warning")
