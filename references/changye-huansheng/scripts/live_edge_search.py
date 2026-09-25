#!/usr/bin/env python3
"""Live Edge Search Collector via Playwright for Pinterest & Web Reference Discovery.

Controls real visible Microsoft Edge browser, navigates to Pinterest with English and Japanese
keywords, extracts high-definition pin images in-browser, and saves them into staging/live_downloads/.
"""

import base64
import io
import json
import time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "staging/live_downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_PATH = ROOT / "staging/live_manifest.json"

SEARCH_PLAN = [
    {
        "direction": "E_PROP",
        "queries": [
            "staff pose cosplay reference",
            "scepter pose reference portrait female",
            "杖 ポーズ 写真 コスプレ",
            "和傘 ポーズ 撮影 女性"
        ]
    },
    {
        "direction": "A_STANDING",
        "queries": [
            "flowing dress pose photoshoot female",
            "angelic maiden pose reference portrait",
            "立ちポーズ 撮影 ドレス 女性",
            "漢服 ポーズ 立ち姿"
        ]
    },
    {
        "direction": "B_TURN_BACK",
        "queries": [
            "looking back over shoulder pose photoshoot female",
            "back view flowing dress photography",
            "振り返り ポーズ 撮影 女性",
            "見返り美人 ポーズ コスプレ"
        ]
    },
    {
        "direction": "C_HANDS_FACE",
        "queries": [
            "veil gesture photoshoot female",
            "hand on face pose reference portrait female",
            "祈り ポーズ コスプレ 女性",
            "ベール ポーズ 撮影"
        ]
    },
    {
        "direction": "D_LOW_STOOL",
        "queries": [
            "stool seated pose reference female portrait",
            "chair pose photoshoot elegant gown",
            "スツール 座りポーズ 撮影 女性",
            "椅子 座りポーズ 撮影 女性"
        ]
    },
    {
        "direction": "F_LOW_ANGLE",
        "queries": [
            "low angle full body portrait photography female",
            "low angle dress photoshoot female",
            "ローアングル 撮影 ポーズ 女性",
            "煽り構图 コスプレ 写真"
        ]
    },
    {
        "direction": "G_DYNAMIC",
        "queries": [
            "floating dress pose reference photography",
            "subtle motion dress photoshoot female",
            "ドレス 動き ポーズ 撮影",
            "浮遊感 ポーズ コスプレ"
        ]
    }
]

JS_FETCH_PINS = """
async () => {
    // Scroll a bit to trigger lazy loading
    window.scrollBy(0, 1000);
    await new Promise(r => setTimeout(r, 1500));
    window.scrollBy(0, 1000);
    await new Promise(r => setTimeout(r, 1500));

    const imgs = Array.from(document.querySelectorAll('img[src*="pinimg.com"]'));
    const items = [];
    const seenUrls = new Set();

    for (const img of imgs) {
        if (!img.src || seenUrls.has(img.src)) continue;
        seenUrls.add(img.src);

        // Attempt upgrade to 736x or originals
        let targetUrl = img.src.replace('/236x/', '/736x/').replace('/474x/', '/736x/');
        try {
            let res = await fetch(targetUrl);
            if (!res.ok) {
                targetUrl = img.src;
                res = await fetch(targetUrl);
            }
            if (!res.ok) continue;

            const blob = await res.blob();
            const b64 = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });

            // Find closest pin link if available
            const pinCard = img.closest('[data-test-id="pin"]') || img.closest('a');
            const pinHref = pinCard && pinCard.href ? pinCard.href : window.location.href;

            items.push({
                url: targetUrl,
                data: b64,
                alt: img.alt || "Pinterest Pose Reference",
                pin_href: pinHref
            });

            if (items.length >= 8) break; // Collect 8 high quality pins per query
        } catch(e) {
            console.error('Fetch error:', e);
        }
    }
    return items;
}
"""

def run_live_search():
    manifest = []
    if METADATA_PATH.exists():
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = []

    existing_urls = {item["url"] for item in manifest}
    total_saved = 0

    print("==================================================================")
    print("STARTING LIVE EDGE BROWSER AUTOMATION")
    print("Target: High-definition Single-shot Poses via Pinterest (EN/JA)")
    print("==================================================================")

    with sync_playwright() as p:
        # Launch visible Edge browser
        browser = p.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 920})
        page = context.new_page()

        for group in SEARCH_PLAN:
            direction = group["direction"]
            dir_folder = OUT_DIR / direction
            dir_folder.mkdir(parents=True, exist_ok=True)
            print(f"\n>>> Searching for Direction: {direction}")

            for q in group["queries"]:
                search_url = f"https://www.pinterest.com/search/pins/?q={requests_quote(q)}"
                print(f"  [Edge] Navigating: '{q}' -> {search_url}")
                try:
                    page.goto(search_url, timeout=35000)
                    page.wait_for_timeout(3000)

                    pins = page.evaluate(JS_FETCH_PINS)
                    print(f"  [Edge] Evaluated {len(pins)} candidates on page")

                    saved_this_query = 0
                    for p_data in pins:
                        img_url = p_data["url"]
                        if img_url in existing_urls:
                            continue

                        b64 = p_data["data"]
                        if "," not in b64:
                            continue
                        header, encoded = b64.split(",", 1)
                        raw_bytes = base64.b64decode(encoded)

                        try:
                            im = Image.open(io.BytesIO(raw_bytes))
                            w, h = im.size
                            # Reject low-res or tiny icons
                            if w < 400 or h < 600:
                                continue

                            ext = "jpg" if im.format == "JPEG" else "webp"
                            file_id = f"LIVE_{direction}_{int(time.time()*1000)%10000000}_{saved_this_query+1}"
                            fn = f"{file_id}.{ext}"
                            fp = dir_folder / fn
                            im.save(fp, quality=92)

                            record = {
                                "id": file_id,
                                "direction": direction,
                                "query": q,
                                "file": str(fp.relative_to(ROOT)).replace("\\", "/"),
                                "width": w,
                                "height": h,
                                "url": img_url,
                                "pin_href": p_data["pin_href"],
                                "alt": p_data["alt"]
                            }
                            manifest.append(record)
                            existing_urls.add(img_url)
                            saved_this_query += 1
                            total_saved += 1
                            print(f"    + Downloaded: {fn} ({w}x{h}) | {p_data['alt'][:28]}")
                        except Exception as e:
                            print(f"    x Save failed: {e}")

                except Exception as e:
                    print(f"  [Edge] Query '{q}' encountered error: {e}")

        browser.close()

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n==================================================================")
    print(f"LIVE SEARCH COMPLETED: {total_saved} new high-res photos downloaded!")
    print(f"Manifest updated at: {METADATA_PATH}")
    print(f"==================================================================")

def requests_quote(s):
    import urllib.parse
    return urllib.parse.quote(s)

if __name__ == "__main__":
    run_live_search()
