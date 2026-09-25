import json
import sys
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

with open("staging/manifest.json", "r", encoding="utf-8") as f:
    m = json.load(f)

ready = m.get("READY_FOR_NOTION_IMPORT", [])
print(f"Total candidates: {len(ready)}")

for r in ready:
    fname = Path(r["local_file"]).name
    fpath = Path("images") / fname
    w, h = 0, 0
    if fpath.exists():
        with Image.open(fpath) as im:
            w, h = im.size
    cid = r.get("id")
    ptype = r.get("pose_type", "")
    scene = r.get("scene_and_shot", "")
    author = r.get("source_author", "")
    title = r.get("source_note_title", "")
    print(f"[{cid}] {fname} | {w}x{h} | {ptype} | Author: {author} | Title: {title}")
