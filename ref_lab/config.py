"""Explicit runtime configuration; no secrets in repository data or browser storage."""
from __future__ import annotations

import json
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
if not WEB_DIR.is_dir():
    WEB_DIR = Path(sys.prefix) / "share" / "photography-reference-lab" / "web"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    token: str
    public_origin: str = "http://127.0.0.1:8765"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_body_bytes: int = 64 * 1024 * 1024
    max_pixels: int = 40_000_000
    web_dir: Path = WEB_DIR
    no_auth: bool = False

    def __post_init__(self) -> None:
        origin = urlsplit(self.public_origin)
        if origin.scheme not in {"http", "https"} or not origin.hostname:
            raise ValueError("LAB_PUBLIC_ORIGIN must be an http(s) origin")
        if origin.username or origin.password or origin.path not in {"", "/"} or origin.query or origin.fragment:
            raise ValueError("LAB_PUBLIC_ORIGIN must not include credentials, a path or query")
        if not self.no_auth and len(self.token) < 24:
            raise ValueError("LAB_ACCESS_TOKEN must be at least 24 characters")

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir_env = os.environ.get("LAB_DATA_DIR", "")
        if not data_dir_env:
            runtime_json = ROOT / ".local" / "windows-runtime.json"
            if runtime_json.is_file():
                try:
                    stored = json.loads(runtime_json.read_text(encoding="utf-8"))
                    if stored.get("data_dir"):
                        data_dir_env = stored["data_dir"]
                except Exception:
                    pass
        if not data_dir_env and (ROOT / "data").is_dir():
            data_dir_env = str(ROOT / "data")
        data_dir = Path(data_dir_env if data_dir_env else ROOT / ".local").expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        no_auth = (
            os.environ.get("LAB_NO_AUTH", "").lower() in {"1", "true", "yes"}
            or (data_dir / "no-auth").exists()
            or (ROOT / "data" / "no-auth").exists()
            or (ROOT / ".local" / "no-auth").exists()
        )
        token = os.environ.get("LAB_ACCESS_TOKEN", "")
        if not token:
            token_file = data_dir / "access-token"
            if not token_file.exists():
                try:
                    with token_file.open("x", encoding="utf-8") as out:
                        out.write(secrets.token_urlsafe(32))
                    token_file.chmod(0o600)
                except FileExistsError:
                    pass
            token = token_file.read_text(encoding="utf-8").strip() if token_file.exists() else secrets.token_urlsafe(32)
        return cls(data_dir=data_dir, token=token,
                   public_origin=os.environ.get("LAB_PUBLIC_ORIGIN", "http://127.0.0.1:8765").rstrip("/"),
                   no_auth=no_auth)
