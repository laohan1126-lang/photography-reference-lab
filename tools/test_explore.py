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

nav_p = subprocess.run([bsk_bin, 'navigate', 'https://www.xiaohongshu.com/explore', '--session', session_id, '--json', '--wait-until', 'domcontentloaded'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print('nav:', nav_p.stdout)

eval_p = subprocess.run([bsk_bin, 'evaluate', '--session', session_id, '--json', '(() => ({ url: location.href, title: document.title, sections: document.querySelectorAll("section").length }))()'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print('eval:', eval_p.stdout)

subprocess.run([bsk_bin, 'session', 'stop', session_id], capture_output=True, env=env)
