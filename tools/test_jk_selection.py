import sys
import json
from pathlib import Path

if not sys.stdout.encoding.lower().startswith('utf'):
    sys.stdout.reconfigure(encoding='utf-8')

p = Path('inspections/inspection-jk-100/manifest.json')
items = json.loads(p.read_text(encoding='utf-8'))
print(f'Total items: {len(items)}')

for it in items[:35]:
    idx = it['index']
    t = it.get('title', '')
    author = it.get('author', '')
    dims = it.get('dimensions', '')
    fn = it.get('filename', '')
    print(f"#{idx:03d} | {t} | by {author} | {dims} | {fn}")
