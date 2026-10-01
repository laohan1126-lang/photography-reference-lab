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
time.sleep(2)

# Check search input
search_js = """(() => {
    const input = document.querySelector('input.search-input') || document.querySelector('#search-input') || document.querySelector('input[type="search"]') || document.querySelector('input');
    if (!input) return { ok: false, error: 'no input' };
    input.focus();
    input.value = 'JK 拍照姿势';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    
    const searchBtn = document.querySelector('.search-icon') || document.querySelector('.input-button') || document.querySelector('button[type="submit"]');
    if (searchBtn) searchBtn.click();
    return { ok: true, val: input.value, btn: !!searchBtn };
})()"""

eval_p = subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', search_js], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print('search action:', eval_p.stdout)
time.sleep(3)

check_js = """(() => ({
    url: location.href,
    title: document.title,
    sections: document.querySelectorAll('section').length,
    cards: document.querySelectorAll('.note-item, section, .search-card').length,
    body: document.body.innerText.slice(0, 150)
}))()"""
eval_check = subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', check_js], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print('after search:', eval_check.stdout)

subprocess.run([bsk_bin, 'session', 'stop', session_id], capture_output=True, env=env)
