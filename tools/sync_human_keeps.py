import sys
import json
from pathlib import Path

if not sys.stdout.encoding.lower().startswith('utf'):
    sys.stdout.reconfigure(encoding='utf-8')

from ref_lab.config import Settings
from ref_lab.service import Library, encode, state_for

lib = Library(Settings.from_env())

# 王昭君
m_zhaojun = json.loads(Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-changye-huansheng-100\manifest.json").read_text(encoding="utf-8"))
chosen_zhaojun = [d["title"] for d in m_zhaojun if d["index"] in [3, 4, 5, 6, 26, 28, 36, 44, 45, 50, 59, 61, 62, 66, 67, 81, 90, 93]]

# 有马加奈
m_kana = json.loads(Path(r"D:\AI PROJECTS\photography-reference-lab\inspections\inspection-arima-kana-100\manifest.json").read_text(encoding="utf-8"))
chosen_kana = [d["title"] for d in m_kana if d["index"] in [1, 2, 3, 4, 15, 34, 46, 49, 58, 72]]

with lib.db.transaction() as con:
    # 1. Update 王昭君
    proj_z = lib.project("37541e718c1140e4bbdd7c31278f6e83")
    rows_z = con.execute("SELECT id, data FROM refs WHERE project_id='37541e718c1140e4bbdd7c31278f6e83'").fetchall()
    for row in rows_z:
        d = json.loads(row[1])
        if d.get("title") in chosen_zhaojun:
            d["decision"] = "keep"
            d["lane"] = "field"
            d["preflight_filtered"] = False
            d["preflight_override"] = True
            d["rejected_at"] = None
            st = state_for(d, proj_z, True)
            d["state"] = st
            con.execute("UPDATE refs SET decision='keep', state=?, data=? WHERE id=?", (st, encode(d), row[0]))
            print(f"王昭君 Keep: {d['title'][:25]}")

    # 2. Update 有马加奈
    proj_k = lib.project("d9344449981d48e39ec24dbe92f93234")
    rows_k = con.execute("SELECT id, data FROM refs WHERE project_id='d9344449981d48e39ec24dbe92f93234'").fetchall()
    for row in rows_k:
        d = json.loads(row[1])
        if d.get("title") in chosen_kana:
            d["decision"] = "keep"
            d["lane"] = "field"
            d["preflight_filtered"] = False
            d["preflight_override"] = True
            d["rejected_at"] = None
            st = state_for(d, proj_k, True)
            d["state"] = st
            con.execute("UPDATE refs SET decision='keep', state=?, data=? WHERE id=?", (st, encode(d), row[0]))
            print(f"有马加奈 Keep: {d['title'][:25]}")

print("Sync completed!")

