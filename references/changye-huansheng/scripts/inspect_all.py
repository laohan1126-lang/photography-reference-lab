import yaml
from pathlib import Path

root = Path("references/changye-huansheng")
with open(root / "data" / "references.yaml", "r", encoding="utf-8") as f:
    items = yaml.safe_load(f)

print(f"Total: {len(items)}")
for it in items:
    print(f"{it['id']} | {it['category']} | {it['priority']} | {it['file']}")
