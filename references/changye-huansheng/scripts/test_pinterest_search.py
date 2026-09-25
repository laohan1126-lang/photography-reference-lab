from playwright.sync_api import sync_playwright
import time
import requests
from pathlib import Path
from PIL import Image
import io

test_dir = Path("staging/pinterest_test")
test_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    print("Opening Pinterest search in Edge...")
    page.goto("https://www.pinterest.com/search/pins/?q=staff%20pose%20cosplay%20reference", timeout=30000)
    page.wait_for_timeout(4000)

    # find images
    imgs = page.eval_on_selector_all('img[src*="pinimg.com"]', """
        elements => elements.map(el => ({
            src: el.src,
            alt: el.alt,
            width: el.naturalWidth,
            height: el.naturalHeight
        }))
    """)

    print(f"Found {len(imgs)} pin images on page")
    headers = {"User-Agent": "Mozilla/5.0"}
    downloaded = 0
    for idx, item in enumerate(imgs[:6]):
        src = item["src"]
        alt = item["alt"]
        orig_url = src.replace("/236x/", "/originals/").replace("/474x/", "/originals/").replace("/736x/", "/originals/")
        print(f"Trying pin {idx+1}: {alt[:30]} | {orig_url}")
        try:
            r = requests.get(orig_url, headers=headers, timeout=10)
            if r.status_code == 200:
                im = Image.open(io.BytesIO(r.content))
                fn = test_dir / f"test_pin_{idx+1:02d}.jpg"
                im.save(fn)
                print(f"-> SUCCESS (Originals): Saved {fn} with size {im.size}")
                downloaded += 1
            else:
                f_url = src.replace("/236x/", "/736x/").replace("/474x/", "/736x/")
                r2 = requests.get(f_url, headers=headers, timeout=10)
                if r2.status_code == 200:
                    im = Image.open(io.BytesIO(r2.content))
                    fn = test_dir / f"test_pin_{idx+1:02d}.jpg"
                    im.save(fn)
                    print(f"-> SUCCESS (736x): Saved {fn} with size {im.size}")
                    downloaded += 1
        except Exception as e:
            print(f"-> Failed: {e}")

    browser.close()
    print(f"Total downloaded: {downloaded}")
