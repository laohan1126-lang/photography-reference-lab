import re
from pathlib import Path

p = Path(r"C:\Users\Dell\.gemini\antigravity\brain\f55fae5b-19d0-49df-9214-fbb37f761bc3\.system_generated\steps\948\content.md")
text = p.read_text(encoding="utf-8", errors="ignore")
urls = re.findall(r'(https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp))', text, re.IGNORECASE)
for u in set(urls):
    print(u)
