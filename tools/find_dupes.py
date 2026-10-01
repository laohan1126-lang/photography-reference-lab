import sys
import json
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from collect_adapter import compute_dhash, hamming_distance

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

data = json.load(open(r'D:\AI PROJECTS\photography-reference-lab\inspections\inspection-jk-100\manifest.json', encoding='utf-8'))
img_dir = Path(r'D:\AI PROJECTS\photography-reference-lab\inspections\inspection-jk-100\images')

dhashes = []
for it in data:
    fpath = img_dir / it['filename']
    with Image.open(fpath) as img:
        dh = compute_dhash(img)
        dhashes.append((it['index'], it['title'], dh))

dupes = []
for i in range(len(dhashes)):
    for j in range(i + 1, len(dhashes)):
        idx1, t1, dh1 = dhashes[i]
        idx2, t2, dh2 = dhashes[j]
        dist = hamming_distance(dh1, dh2)
        if dist <= 6:
            dupes.append((idx1, idx2, dist, t1[:25], t2[:25]))

print(f"Total pairwise near-duplicates found (dhash <= 6): {len(dupes)}")
for d in dupes:
    print(f"  #{d[0]:03d} vs #{d[1]:03d} (dist={d[2]}): '{d[3]}' vs '{d[4]}'")

