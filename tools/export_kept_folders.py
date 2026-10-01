import os
import shutil
import re
from pathlib import Path
import sys
from PIL import Image

if not os.environ.get("LAB_DATA_DIR"):
    os.environ["LAB_DATA_DIR"] = r"D:\AI PROJECTS\photography-reference-lab-data"

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from ref_lab.config import Settings
from ref_lab.service import Library

lib = Library(Settings.from_env())
export_base = Path(r"D:\AI PROJECTS\photography-reference-lab-data\exports")
export_base.mkdir(parents=True, exist_ok=True)

# Map projects to folders (including aliases)
projects_map = {
    "37541e718c1140e4bbdd7c31278f6e83": ["王昭君_已保留参考", "王昭君·长夜焕生_已保留参考"],
    "9cf98c1a2f174edc86413c0127cb01f2": ["西施_已保留参考"],
    "d9344449981d48e39ec24dbe92f93234": ["有马加奈_已保留参考"],
    "82c18730e7d1461ea0bac521ecb3414e": ["jk_已保留参考", "JK制服摄影_已保留参考"]
}

for pid, folder_names in projects_map.items():
    refs = lib.references(pid, limit=200)["items"]
    kept = [r for r in refs if r.get("decision") == "keep"]
    primary_name = folder_names[0]
    p_dir = export_base / primary_name
    if p_dir.exists():
        shutil.rmtree(p_dir)
    p_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"{primary_name}: exporting {len(kept)} images as PNG to {p_dir}")
    for idx, r in enumerate(kept, 1):
        asset = lib.asset(r["asset_sha"])
        src_path = lib.assets.path(asset, "original")
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', r["title"]).strip()[:35]
        target_file = p_dir / f"{idx:02d}_{safe_title}.png"
        try:
            with Image.open(src_path) as im:
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA" if "transparency" in im.info else "RGB")
                # Lanczos 2x resampling for crisp WeChat display if resolution is 640px
                w, h = im.size
                if w <= 640:
                    out_im = im.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
                else:
                    out_im = im
                out_im.save(target_file, format="PNG", optimize=True)
        except Exception as e:
            print(f"  Error converting {src_path} to PNG: {e}")

    # Synchronize to alias folders if any
    for alias_name in folder_names[1:]:
        alias_dir = export_base / alias_name
        if alias_dir.exists():
            shutil.rmtree(alias_dir)
        shutil.copytree(p_dir, alias_dir)
        print(f"  Synchronized alias folder: {alias_name}")

print("\nAll exports converted to WeChat-compatible PNG successfully!")
