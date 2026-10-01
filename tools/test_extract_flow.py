import subprocess
import json
import os
import sys
import time

sys.path.insert(0, 'tools')
from collect_adapter import select_browserskill

bsk_bin, browser_id = select_browserskill()
env = {**os.environ, 'BSK_AUTO_START': '0'}
start_p = subprocess.run([bsk_bin, 'session', 'start', '--browser', browser_id, '--json'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
session_id = json.loads(start_p.stdout).get('session_id')

nav_p = subprocess.run([bsk_bin, 'navigate', 'https://www.xiaohongshu.com/explore', '--session', session_id, '--json', '--wait-until', 'domcontentloaded'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
time.sleep(2.5)

search_js = """(() => {
    const input = document.querySelector('input.search-input') || document.querySelector('#search-input') || document.querySelector('input');
    if (!input) return false;
    input.focus();
    input.value = 'JK 拍照姿势';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    const searchBtn = document.querySelector('.search-icon') || document.querySelector('.input-button') || document.querySelector('button[type="submit"]');
    if (searchBtn) searchBtn.click();
    return true;
})()"""
subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', search_js], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
time.sleep(4.0)

extract_test_js = """(() => {
    const cards = [];
    const items = document.querySelectorAll('section, div.note-item, div.search-card');
    for (const item of items) {
        const img = item.querySelector('img');
        const titleEl = item.querySelector('.title, .desc, a.title span, span.title') || item.querySelector('a:not(.user) span');
        const authorEl = item.querySelector('.author, .name, .user-name, a.user span');
        if (img && (img.currentSrc || img.src)) {
            const src = img.currentSrc || img.src;
            if (src.includes('xhscdn.com') && !src.includes('avatar') && img.naturalWidth >= 120) {
                cards.push({
                    title: titleEl ? titleEl.innerText.trim() : (img.alt ? img.alt.trim() : ''),
                    author: authorEl ? authorEl.innerText.trim() : '',
                    img_src: src.slice(0, 80),
                    w: img.naturalWidth,
                    h: img.naturalHeight
                });
            }
        }
    }
    return { url: location.href, count: cards.length, sample: cards.slice(0, 5) };
})()"""

eval_res = subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', extract_test_js], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print('extract result:', eval_res.stdout)

subprocess.run([bsk_bin, 'session', 'stop', session_id], capture_output=True, env=env)
