import yaml
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
with open(ROOT / "data" / "references.yaml", "r", encoding="utf-8") as f:
    items = yaml.safe_load(f)

pose_items = [r for r in items if r.get("category") == "03_POSE"]
print(f"Total POSE items: {len(pose_items)}")

for i, p in enumerate(pose_items):
    file_path = ROOT / p["file"]
    w, h = 0, 0
    if file_path.exists():
        with Image.open(file_path) as im:
            w, h = im.size
    source = p.get("source", {}) if isinstance(p.get("source"), dict) else {}
    url = source.get("url", "")
    author = source.get("author", "")
    pid = p.get("id", "")
    pfile = p.get("file", "")
    pri = p.get("priority", "")
    print(f"[{i+1:02d}] {pid} | {w}x{h} | {pri} | {author} | {pfile}")
    print(f"     URL: {url}")
