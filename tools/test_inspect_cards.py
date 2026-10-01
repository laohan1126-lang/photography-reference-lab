import subprocess
import json
import os
import sys

sys.path.insert(0, 'tools')
from collect_adapter import select_browserskill

bsk_bin, browser_id = select_browserskill()
env = {**os.environ, 'BSK_AUTO_START': '0'}
start_p = subprocess.run([bsk_bin, 'session', 'start', '--browser', browser_id, '--json'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
session_id = json.loads(start_p.stdout).get('session_id')

inspect_js = """(() => {
    const list = [];
    const items = document.querySelectorAll('section, div.note-item, div.search-card, a[href*="/explore/"], a[href*="xsec_token"]');
    for (const it of Array.from(items).slice(0, 5)) {
        const img = it.querySelector('img') || (it.tagName === 'IMG' ? it : null);
        list.push({
            tag: it.tagName,
            cls: it.className,
            text: it.innerText ? it.innerText.slice(0, 60) : '',
            imgSrc: img ? (img.currentSrc || img.src) : null,
            imgW: img ? img.naturalWidth : 0
        });
    }
    return { url: location.href, count: items.length, sample: list };
})()"""

eval_p = subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', inspect_js], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print('inspect:', eval_p.stdout)

subprocess.run([bsk_bin, 'session', 'stop', session_id], capture_output=True, env=env)
