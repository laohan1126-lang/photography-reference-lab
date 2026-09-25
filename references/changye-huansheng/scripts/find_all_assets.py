import re, glob
from pathlib import Path
from PIL import Image

urls = set()
for f in glob.glob("**/*.*", recursive=True):
    if any(f.endswith(ext) for ext in [".json", ".jsonl", ".md", ".yaml", ".py"]):
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    for m in re.finditer(r"https://sns-webpic[^\s\"\'\<\>]+", line):
                        urls.add(m.group(0))
        except:
            pass

print(f"Total xhscdn image URLs found: {len(urls)}")

# Check local image files
images = []
for p in Path(".").rglob("*.*"):
    if p.suffix.lower() in [".webp", ".jpg", ".jpeg", ".png"]:
        try:
            sz = p.stat().st_size
            if sz > 20000:
                with Image.open(p) as im:
                    w, h = im.size
                    images.append((str(p), w, h, sz))
        except:
            pass

print(f"Total local image files (>20KB): {len(images)}")
