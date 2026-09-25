#!/usr/bin/env python3
"""Dedicated Anime & Honor of Kings Cosplay Reference Collector via Edge / Pinterest.

Focuses 100% on:
- Honor of Kings female characters (Wang Zhaojun, Diaochan, Daqiao, Xishi, Zhenji, Irene)
- Similar anime cryogenic/scepter/goddess cosplay (Shenhe, Furina, Jingliu)
- Anime convention field photography poses (Comiket / 漫展出片实战姿势)
Eliminates all Western commercial fashion / gothic / non-anime noise.
"""

import base64
import io
import json
import time
import urllib.parse
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "staging/cosplay_downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = ROOT / "staging/cosplay_manifest.json"

SEARCH_PLAN = [
    {
        "category": "WANG_ZHAOJUN_HOK",
        "title": "王者荣耀·王昭君及同系法师神女Cos",
        "queries": [
            "王者荣耀 王昭君 cos 摄影",
            "王昭君 乞巧织情 cos",
            "王者荣耀 西施 cos 摄影",
            "王者荣耀 貂蝉 cos 摄影",
            "王者荣耀 大乔 cos 摄影",
            "王者荣耀 甄姬 cos"
        ]
    },
    {
        "category": "ANIME_SCEPTER_GODDESS",
        "title": "动漫二次元法杖/神女高冷Cosplay",
        "queries": [
            "申鹤 cos 摄影 姿势",
            "芙宁娜 cos 摄影 手杖",
            "镜流 cos 摄影",
            "Shenhe cosplay photoshoot",
            "Furina cosplay scepter",
            "杖 ポーズ コスプレ 女性"
        ]
    },
    {
        "category": "CONVENTION_FIELD_POSES",
        "title": "漫展现场实战出片姿势 (低机位/回眸/防人流)",
        "queries": [
            "漫展 拍照姿势 女角色 cos",
            "コミケ コスプレ 撮影 ポーズ",
            "cosplay turn back reference anime",
            "cosplay low angle photography anime female",
            "anime cosplay cape dynamic photography"
        ]
    }
]

def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)

def run_cosplay_collector(max_per_query=8):
    existing_items = []
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
        except Exception:
            existing_items = []

    seen_urls = {x.get("url") for x in existing_items}
    records = list(existing_items)

    print("Launching visible Microsoft Edge for Anime & HOK Cosplay Discovery...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 950},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0"
        )
        page = context.new_page()

        for group in SEARCH_PLAN:
            cat = group["category"]
            cat_dir = OUT_DIR / cat
            cat_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n==========================================")
            print(f"Targeting: {group['title']} ({cat})")
            print(f"==========================================")

            for query in group["queries"]:
                print(f"\n--> Searching: {query} ...")
                encoded_q = urllib.parse.quote(query)
                search_url = f"https://www.pinterest.com/search/pins/?q={encoded_q}"

                try:
                    page.goto(search_url, timeout=30000)
                    time.sleep(3)

                    # Smooth scroll to trigger lazy loading
                    for _ in range(3):
                        page.mouse.wheel(0, 1000)
                        time.sleep(1.2)

                    # Extract pins
                    pins_data = page.evaluate("""
                        () => {
                            const results = [];
                            const imgs = document.querySelectorAll('img');
                            for (const img of imgs) {
                                const src = img.src || '';
                                if (!src.includes('pinimg.com')) continue;
                                const alt = img.alt || '';
                                
                                // Upgrade to 736x HD
                                let hdUrl = src;
                                if (src.includes('/236x/')) {
                                    hdUrl = src.replace('/236x/', '/736x/');
                                } else if (src.includes('/474x/')) {
                                    hdUrl = src.replace('/474x/', '/736x/');
                                }
                                
                                const link = img.closest('a');
                                const href = link ? link.href : '';
                                results.push({
                                    src: hdUrl,
                                    alt: alt,
                                    href: href
                                });
                            }
                            return results;
                        }
                    """)

                    print(f"    Extracted {len(pins_data)} candidate pin URLs.")

                    downloaded_for_query = 0
                    for item in pins_data:
                        if downloaded_for_query >= max_per_query:
                            break

                        img_url = item["src"]
                        if img_url in seen_urls:
                            continue

                        # Fetch in browser context as base64 to bypass CDN socket reset
                        b64_data = page.evaluate("""
                            async (url) => {
                                try {
                                    const resp = await fetch(url);
                                    if (!resp.ok) return null;
                                    const blob = await resp.blob();
                                    return new Promise((resolve, reject) => {
                                        const reader = new FileReader();
                                        reader.onloadend = () => resolve(reader.result);
                                        reader.onerror = reject;
                                        reader.readAsDataURL(blob);
                                    });
                                } catch (e) {
                                    return null;
                                }
                            }
                        """, img_url)

                        if not b64_data or not b64_data.startswith("data:image"):
                            continue

                        header, encoded = b64_data.split(",", 1)
                        img_bytes = base64.b64decode(encoded)

                        try:
                            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                                w, h = pil_img.size
                                # Filter out tiny avatars / icons
                                if w < 400 or h < 500:
                                    continue

                                cand_id = f"COS_{cat}_{int(time.time()*10)%10000000}_{downloaded_for_query+1}"
                                out_filename = f"{cand_id}.jpg"
                                out_filepath = cat_dir / out_filename

                                pil_img.convert("RGB").save(out_filepath, "JPEG", quality=94)

                                rec = {
                                    "id": cand_id,
                                    "category": cat,
                                    "category_title": group["title"],
                                    "query": query,
                                    "file": str(out_filepath.relative_to(ROOT)).replace("\\", "/"),
                                    "width": w,
                                    "height": h,
                                    "url": img_url,
                                    "pin_href": item["href"],
                                    "alt": item["alt"]
                                }
                                records.append(rec)
                                seen_urls.add(img_url)
                                downloaded_for_query += 1
                                print(f"    [OK] Downloaded: {out_filename} ({w}x{h}) - {item['alt'][:30]}")
                        except Exception as img_err:
                            print(f"    [Error] Processing image: {img_err}")

                except Exception as page_err:
                    print(f"    [Error] Query {query} failed: {page_err}")

        browser.close()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nAll Done! Saved {len(records)} Cosplay references into {OUT_DIR}")

if __name__ == "__main__":
    run_cosplay_collector(max_per_query=6)
