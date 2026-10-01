import subprocess
import json
import os
import sys

sys.path.insert(0, 'tools')
from collect_adapter import select_browserskill

bsk_bin, browser_id = select_browserskill()
env = {**os.environ, 'BSK_AUTO_START': '0'}
start_p = subprocess.run([bsk_bin, 'session', 'start', '--browser', browser_id, '--json'], capture_output=True, text=True, env=env)
session_id = json.loads(start_p.stdout).get('session_id')
print('session_id:', session_id)

nav_p = subprocess.run([bsk_bin, 'navigate', 'https://www.xiaohongshu.com/search_result?keyword=JK', '--session', session_id, '--json', '--wait-until', 'domcontentloaded'], capture_output=True, text=True, env=env)
print('nav:', nav_p.stdout)

eval_p = subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', '(() => ({ title: document.title, url: location.href, sections: document.querySelectorAll("section").length, imgs: document.querySelectorAll("img").length, bodyText: document.body.innerText.slice(0, 300) }))()'], capture_output=True, text=True, env=env)
print('eval:', eval_p.stdout)

subprocess.run([bsk_bin, 'session', 'stop', session_id], capture_output=True, env=env)
