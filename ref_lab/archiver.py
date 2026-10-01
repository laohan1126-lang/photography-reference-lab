"""Project confirmed references auto-archive manager.

Organizes kept references into human-readable directory:
    <data_dir>/exports/<character>/已确认/<idx>_<title>.jpg
Preserves underlying CAS original bytes in assets/ while providing
a clean, single-folder archive for photography and model sharing.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

if TYPE_CHECKING:
    from .service import Library

logger = logging.getLogger(__name__)

INVALID_CHARS_RE = re.compile(r'[\\/*?:"<>|\r\n\t]+')


def sanitize_filename(name: str | None, max_length: int = 40) -> str:
    """Sanitize directory or file names for cross-platform filesystem safety."""
    if not name:
        return "未命名"
    cleaned = INVALID_CHARS_RE.sub("_", name).strip("._ ")
    if not cleaned:
        cleaned = "未命名"
    return cleaned[:max_length].rstrip("._ ")


def get_project_archive_dir(data_dir: Path, project: dict[str, Any]) -> Path:
    """Return the confirmed archive folder: <data_dir>/exports/<character>/已确认."""
    char = sanitize_filename(project.get("character") or "未分类角色", max_length=40)
    return data_dir / "exports" / char / "已确认"


def get_reference_archive_filename(index: int, ref: dict[str, Any]) -> str:
    """Generate clean, ordered filename: 01_标题.jpg."""
    safe_title = sanitize_filename(ref.get("title") or "参考图", max_length=40)
    return f"{index:02d}_{safe_title}.jpg"


def export_asset_as_jpeg(src_path: Path, dest_path: Path) -> bool:
    """Safely convert any image asset (WebP, PNG, JPG) to high-quality JPEG."""
    if not src_path.is_file():
        logger.warning(f"Source asset missing: {src_path}")
        return False

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp.jpg")

    try:
        with Image.open(src_path) as im:
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                rgba_im = im.convert("RGBA")
                bg.paste(rgba_im, mask=rgba_im.split()[3])
                rgb_im = bg
            elif im.mode != "RGB":
                rgb_im = im.convert("RGB")
            else:
                rgb_im = im

            rgb_im.save(temp_path, format="JPEG", quality=95, optimize=True)

        if temp_path.is_file():
            temp_path.replace(dest_path)
            return True
    except Exception as e:
        logger.error(f"Failed to convert {src_path} to JPEG at {dest_path}: {e}")
        if temp_path.is_file():
            try:
                temp_path.unlink()
            except OSError:
                pass
        return False
    return False


def sync_project_confirmed_archive(library: Library, project_id: str) -> dict[str, Any]:
    """Synchronize all confirmed (decision == 'keep') references into the project's archive folder.

    - Creates <data_dir>/exports/<character>/已确认/
    - Converts each kept reference's original asset to <idx>_<title>.jpg
    - Cleans up stale images of references that are no longer kept
    - Returns a summary with archive_dir and mapped references
    """
    project = library.project(project_id)
    archive_dir = get_project_archive_dir(library.settings.data_dir, project)
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Fetch kept references for this project
    all_refs = library.references(project_id, limit=2000, include_rejected=False)["items"]
    kept_refs = [
        r for r in all_refs
        if r.get("decision") == "keep" and not r.get("detached_at") and r.get("asset_sha")
    ]

    expected_files: set[str] = set()
    ref_to_archive_path: dict[str, str] = {}

    for idx, ref in enumerate(kept_refs, 1):
        filename = get_reference_archive_filename(idx, ref)
        dest_file = archive_dir / filename
        expected_files.add(dest_file.name)
        ref_to_archive_path[ref["id"]] = str(dest_file)

        # Retrieve CAS asset
        try:
            asset = library.asset(ref["asset_sha"])
            src_path = library.assets.path(asset, "original")
        except Exception as e:
            logger.warning(f"Could not locate asset for reference {ref['id']}: {e}")
            continue

        # Export if destination does not exist or has zero size
        if not dest_file.is_file() or dest_file.stat().st_size == 0:
            export_asset_as_jpeg(src_path, dest_file)

    # Remove any extra .jpg/.jpeg/.png/.webp in the archive folder that are no longer kept
    try:
        for existing in archive_dir.iterdir():
            if existing.is_file() and existing.name not in expected_files:
                if existing.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    try:
                        existing.unlink()
                        logger.info(f"Removed unconfirmed archive file: {existing}")
                    except OSError:
                        pass
    except Exception as e:
        logger.warning(f"Error cleaning stale files in {archive_dir}: {e}")

    return {
        "archive_dir": str(archive_dir),
        "count": len(expected_files),
        "mapping": ref_to_archive_path
    }
