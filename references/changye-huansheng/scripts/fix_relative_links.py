import re
from pathlib import Path

docs_dir = Path("references/changye-huansheng/docs")

pattern = re.compile(r'file:///d:[^"\)]*?/references/changye-huansheng/(refs/[^"\)]+)')

for p in docs_dir.glob("*.md"):
    txt = p.read_text(encoding="utf-8")
    new_txt, count = pattern.subn(r'../\1', txt)
    if count > 0:
        p.write_text(new_txt, encoding="utf-8")
        print(f"Replaced {count} absolute links in {p.name}")

# Also check root md files
root_dir = Path("references/changye-huansheng")
pattern_root = re.compile(r'file:///d:[^"\)]*?/references/changye-huansheng/(refs/[^"\)]+)')
for p in root_dir.glob("*.md"):
    txt = p.read_text(encoding="utf-8")
    new_txt, count = pattern_root.subn(r'\1', txt)
    if count > 0:
        p.write_text(new_txt, encoding="utf-8")
        print(f"Replaced {count} absolute links in root {p.name}")

print("Relative links fixed successfully!")
