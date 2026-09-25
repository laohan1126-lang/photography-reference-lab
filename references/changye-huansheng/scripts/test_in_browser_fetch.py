from playwright.sync_api import sync_playwright
import base64
from pathlib import Path
from PIL import Image
import io

out_file = Path("staging/pinterest_test/browser_fetch_test.jpg")
out_file.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    print("Navigating to Pinterest search in Edge...")
    page.goto("https://www.pinterest.com/search/pins/?q=staff%20pose%20cosplay%20reference", timeout=30000)
    page.wait_for_timeout(4000)

    # Let browser fetch image as base64 in its own network context
    js_code = """
    async () => {
        const imgs = Array.from(document.querySelectorAll('img[src*="pinimg.com"]'));
        const results = [];
        for (const img of imgs.slice(0, 6)) {
            try {
                // Try to upgrade to 736x or originals
                let targetUrl = img.src.replace('/236x/', '/736x/').replace('/474x/', '/736x/');
                const res = await fetch(targetUrl);
                if (!res.ok) {
                    // fallback
                    const res2 = await fetch(img.src);
                    const blob = await res2.blob();
                    const b64 = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                    results.push({ url: img.src, data: b64, alt: img.alt });
                    continue;
                }
                const blob = await res.blob();
                const b64 = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.readAsDataURL(blob);
                });
                results.push({ url: targetUrl, data: b64, alt: img.alt });
            } catch(e) {
                console.error(e);
            }
        }
        return results;
    }
    """
    results = page.evaluate(js_code)
    print(f"Browser evaluated and fetched {len(results)} images in-context!")

    for idx, r in enumerate(results):
        b64 = r["data"]
        header, encoded = b64.split(",", 1)
        data = base64.b64decode(encoded)
        im = Image.open(io.BytesIO(data))
        fn = Path(f"staging/pinterest_test/pin_in_browser_{idx+1:02d}.jpg")
        fn.write_bytes(data)
        print(f"Saved {fn.name}: {im.size} | {r['alt'][:30]} | {r['url']}")

    browser.close()
