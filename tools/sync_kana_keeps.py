import os
import sys
import json
from pathlib import Path

if not os.environ.get("LAB_DATA_DIR"):
    os.environ["LAB_DATA_DIR"] = r"D:\AI PROJECTS\photography-reference-lab-data"

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from ref_lab.config import Settings
from ref_lab.service import Library, encode, state_for
from ref_lab.models import CandidateInput, Source

lib = Library(Settings.from_env())

m_kana_path = Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-arima-kana-100\manifest.json")
m_kana = json.loads(m_kana_path.read_text(encoding="utf-8"))
chosen_indices = [1, 2, 3, 4, 15, 34, 46, 49, 58, 72]
chosen_items = [d for d in m_kana if d["index"] in chosen_indices]

img_dir = Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-arima-kana-100\images")
proj_id = "d9344449981d48e39ec24dbe92f93234"
proj = lib.project(proj_id)

print(f"Target project: {proj['character']} ({proj['id']})")
print(f"Chosen items count: {len(chosen_items)}")

for item in chosen_items:
    img_path = img_dir / item["filename"]
    raw_bytes = img_path.read_bytes()
    asset = lib.ingest_asset(raw_bytes, item["filename"])
    
    # Check if this asset is already in refs for this project
    with lib.db.connection() as con:
        cur = con.execute("SELECT id, decision, data FROM refs WHERE project_id=? AND asset_sha=?", (proj_id, asset["id"]))
        row = cur.fetchone()
        
    if row:
        ref_id, decision, data_json = row
        d = json.loads(data_json)
        d["decision"] = "keep"
        d["lane"] = "field"
        d["preflight_filtered"] = False
        d["preflight_override"] = True
        d["rejected_at"] = None
        st = state_for(d, proj, True)
        d["state"] = st
        with lib.db.transaction() as con:
            con.execute("UPDATE refs SET decision='keep', state=?, data=? WHERE id=?", (st, encode(d), ref_id))
        print(f"Updated existing #{item['index']:03d} -> keep: {item['title'][:25]} ({ref_id[:8]})")
    else:
        # Add new candidate
        cand = CandidateInput(
            asset_sha=asset["id"],
            title=item.get("title") or "未命名参考",
            source=Source(
                page_url=item.get("page_url", "") if item.get("page_url", "").startswith("http") else "",
                image_url=item.get("image_url", "") if item.get("image_url", "").startswith("http") else "",
                title=item.get("title", ""),
                author=item.get("author", ""),
                search_query=item.get("query", ""),
            ),
            discovery_intent="exact_character",
            discovery_reason=item.get("verdict_desc", "人类审美精选"),
            import_key=f"user_keep_{item['filename']}"
        )
        res = lib.add_candidate(proj_id, cand, decision="keep", actor="human")
        print(f"Added new #{item['index']:03d} -> keep: {item['title'][:25]} ({res['reference']['id'][:8]})")

# Print summary
refs = lib.references(proj_id, limit=200)["items"]
kept = [r for r in refs if r.get("decision") == "keep"]
print(f"Successfully verified Kana project: total {len(refs)} refs, {len(kept)} kept!")

