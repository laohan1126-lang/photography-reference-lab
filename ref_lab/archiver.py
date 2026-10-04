"""Project confirmed references auto-archive manager.

Organizes kept references into human-readable directory:
    <data_dir>/exports/<character>/已确认/ref-lab_<reference-and-asset-hash>_<title>.jpg
Preserves underlying CAS original bytes in assets/ while providing
a clean, single-folder archive for photography and model sharing.
"""
from __future__ import annotations

import hashlib
import json
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


MANAGED_FILENAME = re.compile(r"^ref-lab_[a-f0-9]{64}_.+\.jpg$")


def get_reference_archive_filename(ref: dict[str, Any]) -> str:
    """Human title is a label; reference and received bytes define identity."""
    reference_hash = hashlib.sha256(json.dumps([ref["id"], ref["asset_sha"]]).encode("utf-8")).hexdigest()
    title = sanitize_filename(ref.get("title") or "参考图", max_length=40)
    return f"ref-lab_{reference_hash}_{title}.jpg"


def get_reference_archive_path(data_dir: Path, project: dict, ref: dict) -> Path:
    return get_project_archive_dir(data_dir, project) / get_reference_archive_filename(ref)


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


def sync_project_confirmed_archive(library: Library, project_id: str, *, archive_dir: Path | None = None) -> dict[str, Any]:
    """Project committed K selections into their shared character folder.

    A writer transaction serializes snapshots and file updates. Original CAS and
    files without this exporter's managed namespace are never removed.
    """
    errors: list[str] = []
    mapping: dict[str, str] = {}
    expected: set[str] = set()
    with library.db.transaction() as con:
        projects = [json.loads(row[0]) for row in con.execute("SELECT data FROM projects")]
        project = next(p for p in projects if p["id"] == project_id)
        folder = archive_dir or get_project_archive_dir(library.settings.data_dir, project)
        folder.mkdir(parents=True, exist_ok=True)
        shared_projects = {p["id"] for p in projects if not p.get("archived_at") and get_project_archive_dir(library.settings.data_dir, p) == folder}
        refs = [json.loads(row[0]) for row in con.execute("SELECT data FROM refs WHERE decision='keep'")]
        for ref in refs:
            if ref["project_id"] not in shared_projects or ref.get("detached_at") or ref.get("lane") != "field" or not ref.get("asset_sha"):
                continue
            target = folder / get_reference_archive_filename(ref)
            expected.add(target.name)
            row = con.execute("SELECT data FROM assets WHERE id=?", (ref["asset_sha"],)).fetchone()
            asset = json.loads(row[0]) if row else None
            source = library.assets.path(asset, "original") if asset else None
            if not source or not source.is_file():
                errors.append(f"Reference {ref['id']}: original asset unavailable")
                continue
            if not target.is_file() or target.stat().st_size == 0:
                if not export_asset_as_jpeg(source, target):
                    errors.append(f"Reference {ref['id']}: JPEG export failed")
                    continue
            mapping[ref["id"]] = str(target)
        # Keep older exports when their replacements failed; retry after a successful sync.
        if not errors:
            for existing in folder.iterdir():
                if existing.is_file() and MANAGED_FILENAME.fullmatch(existing.name) and existing.name not in expected:
                    try:
                        existing.unlink()
                    except OSError as exc:
                        errors.append(f"Could not remove derived export {existing.name}: {exc}")
    return {"archive_dir": str(folder), "count": len(mapping), "mapping": mapping, "errors": errors}
