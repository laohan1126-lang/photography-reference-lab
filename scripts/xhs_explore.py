import subprocess
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BSK_EXE = r"C:\Users\Dell\.local\bin\bsk.exe"

def get_session():
    cmd = [BSK_EXE, "session", "list", "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env={"BSK_AUTO_START": "0"})
    if res.returncode == 0 and res.stdout.strip():
        try:
            data = json.loads(res.stdout)
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get("session_id")
        except Exception:
            pass
    # Auto-start session
    start_cmd = [BSK_EXE, "session", "start", "--browser", "9d3f232a", "--json"]
    s_res = subprocess.run(start_cmd, capture_output=True, text=True, encoding="utf-8", env={"BSK_AUTO_START": "0"})
    if s_res.returncode == 0 and s_res.stdout.strip():
        try:
            data = json.loads(s_res.stdout)
            return data.get("session_id", "auto")
        except Exception:
            pass
    return "auto"

SESSION = get_session()

def eval_js(code: str) -> str:
    global SESSION
    SESSION = get_session()
    cmd = [BSK_EXE, "evaluate", "--session", SESSION, code]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env={"BSK_AUTO_START": "0"})
    if res.returncode != 0:
        raise RuntimeError(f"bsk error: {res.stderr.strip() or res.stdout.strip()}")
    return res.stdout.strip()

def navigate(url: str):
    escaped_url = json.dumps(url, ensure_ascii=True)
    eval_js(f"window.location.href = {escaped_url}")
    time.sleep(3)
    return "navigated"

def press_key(key: str):
    sess = get_session()
    cmd = [BSK_EXE, "press", "--session", sess, key]
    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env={"BSK_AUTO_START": "0"})

def close_modal():
    code = """(() => {
        const btn = document.querySelector('.close-circle, .close, .close-box');
        if (btn) { btn.click(); return 'clicked_close_btn'; }
        const mask = document.querySelector('.mask');
        if (mask) { mask.click(); return 'clicked_mask'; }
        return 'none';
    })()"""
    eval_js(code)
    press_key("Escape")
    time.sleep(1)

def list_cards():
    code = """(() => {
        const cards = Array.from(document.querySelectorAll('section.note-item, div.note-item'));
        return JSON.stringify(cards.slice(0, 20).map((c, i) => {
            const title = c.querySelector('.title, .footer .title, a.title')?.innerText || '';
            const author = c.querySelector('.author, .name')?.innerText || '';
            const link = c.querySelector('a[href*="/explore/"]')?.href || '';
            const img = c.querySelector('img')?.src || '';
            return { index: i, title: title.trim(), author: author.trim(), link, img };
        }));
    })()"""
    out = eval_js(code)
    try:
        # If output is wrapped in quotes or raw json
        if out.startswith('"') and out.endswith('"'):
            out = json.loads(out)
        return json.loads(out)
    except Exception as e:
        print("Raw output:", out)
        raise e

def search_url(kw: str):
    import urllib.parse
    url = f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(kw)}&source=web_search_result_notes"
    navigate(url)
    time.sleep(3)
    return url

def open_card(index: int):
    code = f"""(() => {{
        const cards = Array.from(document.querySelectorAll('section.note-item, div.note-item'));
        if (cards[{index}]) {{
            const cover = cards[{index}].querySelector('.cover, .image-wrapper, img');
            if (cover) {{
                cover.click();
                return 'clicked_cover';
            }}
            cards[{index}].click();
            return 'clicked_card';
        }}
        return 'not_found';
    }})()"""
    res = eval_js(code)
    time.sleep(2)
    return res

def inspect_modal():
    code = """(() => {
        const title = document.querySelector('.note-container .title, #detail-title, .title')?.innerText || '';
        const author = document.querySelector('.author-container .name, .username, .name')?.innerText || '';
        const desc = document.querySelector('.note-container .desc, #detail-desc, .desc')?.innerText || '';
        const imgs = Array.from(document.querySelectorAll('.media-container img, .swiper-slide img, .note-slider img, .carousel img, .note-scroller img'))
            .map(i => i.src)
            .filter(src => src && src.includes('xhscdn.com') && !src.includes('avatar'));
        return JSON.stringify({
            url: window.location.href,
            title: title.trim(),
            author: author.trim(),
            desc: desc.trim().slice(0, 200),
            imgs: Array.from(new Set(imgs))
        });
    })()"""
    out = eval_js(code)
    try:
        if out.startswith('"') and out.endswith('"'):
            out = json.loads(out)
        return json.loads(out)
    except Exception as e:
        print("Raw output:", out)
        raise e

if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "list":
            cards = list_cards()
            for c in cards:
                print(f"[{c['index']}] {c['title']} | {c['author']} | {c['link']}")
        elif action == "search" and len(sys.argv) > 2:
            res = search_url(sys.argv[2])
            print(f"Search URL loaded: {res}")
            cards = list_cards()
            for c in cards:
                print(f"[{c['index']}] {c['title']} | {c['author']} | {c['link']}")
        elif action == "open" and len(sys.argv) > 2:
            res = open_card(int(sys.argv[2]))
            print(f"Clicked card: {res}")
            data = inspect_modal()
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif action == "inspect":
            data = inspect_modal()
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif action == "close":
            close_modal()
            print("Closed modal")
        elif action == "nav" and len(sys.argv) > 2:
            navigate(sys.argv[2])
            print("Navigated")
