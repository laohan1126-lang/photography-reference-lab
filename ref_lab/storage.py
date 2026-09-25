"""Immutable, content-addressed received files, with separate display derivatives."""
from __future__ import annotations

import hashlib
import io
import os
import tempfile
import warnings
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from .config import Settings
from .db import now

FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class AssetStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.data_dir / "assets"
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, metadata: dict, variant: str = "original") -> Path:
        sha = metadata["id"]
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("Invalid asset digest")
        if variant not in {"original", "preview", "thumb"}:
            raise ValueError("Unknown image variant")
        suffix = metadata["ext"] if variant == "original" else "jpg"
        if suffix not in {"jpg", "png", "webp"}:
            raise ValueError("Invalid image extension")
        return self.root / sha[:2] / sha / f"{variant}.{suffix}"

    def ingest(self, content: bytes, filename: str = "") -> dict:
        if not content or len(content) > self.settings.max_upload_bytes:
            raise ValueError("Empty image or image exceeds the 20 MiB upload limit")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    fmt = image.format
                    if fmt not in FORMATS or getattr(image, "n_frames", 1) != 1:
                        raise ValueError("Only single-frame JPEG, PNG and WebP images are supported")
                    if image.width * image.height > self.settings.max_pixels:
                        raise ValueError("Image exceeds pixel safety limit")
                    image.verify()
                with Image.open(io.BytesIO(content)) as image:
                    image.load()
                    display = ImageOps.exif_transpose(image).convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError("Image is corrupt, unsupported or too large") from exc
        sha = hashlib.sha256(content).hexdigest()
        ext, mime = FORMATS[fmt]
        tiny = display.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(tiny.get_flattened_data()) if hasattr(tiny, "get_flattened_data") else list(tiny.getdata())
        bits = sum((pixels[y * 9 + x] > pixels[y * 9 + x + 1]) << (y * 8 + x)
                   for y in range(8) for x in range(8))
        meta = {"id": sha, "ext": ext, "mime": mime, "bytes": len(content),
                "width": display.width, "height": display.height, "dhash": f"{bits:016x}",
                "received_name": Path(filename.replace("\\", "/")).name[:200], "created_at": now()}
        original = self.path(meta)
        if original.exists():
            if hashlib.sha256(original.read_bytes()).hexdigest() != sha:
                raise ValueError("Stored original failed integrity check; refusing overwrite")
        else:
            atomic_write(original, content)
        for variant, size in (("preview", 2000), ("thumb", 360)):
            target = self.path(meta, variant)
            if not target.exists():
                derivative = display.copy()
                derivative.thumbnail((size, size), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                derivative.save(out, "JPEG", quality=90, optimize=True)
                atomic_write(target, out.getvalue())
        return meta

    def verify(self, metadata: dict) -> bool:
        path = self.path(metadata)
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["id"]
