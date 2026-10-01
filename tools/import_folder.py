"""Batch import images from a local folder into Photography Reference Lab.

Usage examples:
  # Import to a project (creates project if not exists)
  python tools/import_folder.py "D:\\Photos\\婚纱" --project "婚纱"

  # Import to independent inspiration library
  python tools/import_folder.py "D:\\Photos\\婚纱" --inspiration
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ref_lab.config import Settings
from ref_lab.models import ProjectInput, CandidateInput, Source
from ref_lab.service import Library, Problem

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_images(folder: Path, recursive: bool = False) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files = []
    for p in folder.glob(pattern):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(p)
    return sorted(files)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Batch import local image folder to Reference Lab")
    parser.add_argument("folder", help="Path to directory containing images")
    parser.add_argument("--project", "-p", help="Target project character name (e.g. '婚纱')")
    parser.add_argument("--costume", "-c", default="", help="Optional costume/version (e.g. '白纱外景')")
    parser.add_argument("--inspiration", "-i", action="store_true", help="Import directly to independent inspiration library")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan subdirectories recursively")
    parser.add_argument("--data-dir", default=os.environ.get("LAB_DATA_DIR", str(REPO_ROOT / "data")), help="Data directory")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"Error: Folder does not exist: {folder}", file=sys.stderr)
        sys.exit(1)

    images = find_images(folder, args.recursive)
    if not images:
        print(f"No supported images (.jpg, .jpeg, .png, .webp) found in {folder}")
        sys.exit(0)

    print(f"Found {len(images)} images in {folder}")

    os.environ["LAB_DATA_DIR"] = args.data_dir
    settings = Settings.from_env()
    lib = Library(settings)

    project_id = None
    if not args.inspiration:
        char_name = (args.project or folder.name).strip()
        # Find or create project
        existing = [p for p in lib.projects() if p.get("character") == char_name]
        if existing:
            project = existing[0]
            project_id = project["id"]
            print(f"Using existing project: [{char_name}] (ID: {project_id})")
        else:
            project = lib.create_project(ProjectInput(character=char_name, costume=args.costume, brief="外部导入参考图片"))
            project_id = project["id"]
            print(f"Created new project: [{char_name}] (ID: {project_id})")

    created = 0
    skipped = 0
    errors = 0

    for idx, img_path in enumerate(images, 1):
        try:
            content = img_path.read_bytes()
            if len(content) > settings.max_upload_bytes:
                print(f"  [{idx}/{len(images)}] Skipped (exceeds size limit): {img_path.name}")
                skipped += 1
                continue

            asset = lib.ingest_asset(content, img_path.name)
            title = img_path.stem[:100]

            if args.inspiration:
                from ref_lab.models import InspirationInput
                src = Source(obtained_as="as_received", author="朋友分享", page_url="")
                # Check if already in inspiration
                try:
                    lib.create_inspiration(InspirationInput(
                        asset_sha=asset["id"],
                        title=title,
                        source=src,
                        preference="朋友分享的婚纱/人像参考",
                    ))
                    created += 1
                except Exception:
                    skipped += 1
            else:
                input_data = CandidateInput(
                    asset_sha=asset["id"],
                    title=title,
                    source=Source(obtained_as="as_received", author="朋友分享", page_url=""),
                    discovery_intent="transferable_pose",
                    discovery_reason="外部朋友分享导入",
                )
                res = lib.add_candidate(project_id, input_data)
                if res.get("created"):
                    created += 1
                else:
                    skipped += 1
            
            if idx % 10 == 0 or idx == len(images):
                print(f"  Progress: {idx}/{len(images)} (Imported: {created}, Skipped/Existing: {skipped})")
        except Exception as e:
            print(f"  Error importing {img_path.name}: {e}")
            errors += 1

    print("\n==========================================")
    print(f"Import complete!")
    print(f"  Total processed: {len(images)}")
    print(f"  Newly added:     {created}")
    print(f"  Skipped/Exists:  {skipped}")
    print(f"  Errors:          {errors}")
    if project_id:
        print(f"  Now available in web UI under project: [{char_name}]")
    else:
        print(f"  Now available in web UI under: [我的审美库]")
    print("==========================================")


if __name__ == "__main__":
    main()
