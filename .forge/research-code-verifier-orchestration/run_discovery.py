"""Fresh native Codex routing trials; output stays in the gitignored .local folder."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import winreg

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / '.agents/skills/research-code-verifier-orchestration/SKILL.md'
OUT = ROOT / '.local/orchestration-validation/discovery'
PREFIX = ('本次仅进行只读任务规划，允许用shell或工具读取相关说明与源码。'
          '禁止修改文件、调度其他代理或后台工作、研究网页、调用Publisher、读取私人数据或凭据。'
          '后续实施沿用现有用户授权，仅限目标必需步骤。'
          '请按当前可用技能和项目规则决定如何处理以下用户目标，完成规划后停止。\n\n')


def _normalized_lines(value):
    return value.replace('\r\n', '\n').replace('\r', '\n').strip('\n')


def _complete_skill_in(value, skill_text):
    if isinstance(value, str):
        body = _normalized_lines(skill_text)
        return bool(body) and body in _normalized_lines(value)
    if isinstance(value, dict):
        return any(_complete_skill_in(v, skill_text) for v in value.values())
    if isinstance(value, list):
        return any(_complete_skill_in(v, skill_text) for v in value)
    return False


def _target_skill_read(command, skill_text):
    cmd = command.get('command', '')
    output = command.get('aggregated_output', '')
    targets_skill = ('research-code-verifier-orchestration' in cmd and 'SKILL.md' in cmd)
    if not targets_skill:
        return False
    # A later compound command can fail after the complete source was returned.
    # A title, path or partial body is insufficient even when exit_code is zero.
    return (_complete_skill_in(output, skill_text)
            and (command.get('exit_code') == 0 or 'Get-Content' in cmd))


def _target_skill_mcp_read(item, skill_text):
    arguments = json.dumps(item.get('arguments', {}))
    return ('research-code-verifier-orchestration' in arguments
            and 'SKILL.md' in arguments
            and _complete_skill_in(item.get('result', {}), skill_text))


def run(case):
    attempt = sys.argv[1] if len(sys.argv) > 1 else 'initial'
    directory = OUT / (case['id'] + '-' + attempt)
    if directory.exists():
        raise RuntimeError('Preserve existing runs; choose an explicit new attempt label')
    directory.mkdir(parents=True, exist_ok=True)
    args = [shutil.which('codex'), 'exec', '--ephemeral', '--json', '--color', 'never',
            '--sandbox', 'danger-full-access', '-C', str(directory), '-o', str(directory/'final.txt'),
            PREFIX + case['prompt']]
    meta = {'id': case['id'], 'prompt': case['prompt'], 'cwd': str(directory),
            'command': args[:-1] + ['<readonly-planning-prompt>'],
            'started_at': datetime.now(timezone.utc).isoformat(),
            'skill_sha256': hashlib.sha256(SKILL.read_bytes()).hexdigest(),
            'execution_boundary': 'Prompt-constrained read-only planning in the same authorized host policy; native Windows sandbox provisioning failed in the preserved prior attempt'}
    with (directory/'events.jsonl').open('w', encoding='utf-8') as stdout, \
         (directory/'stderr.txt').open('w', encoding='utf-8') as stderr:
        env = os.environ.copy()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            if winreg.QueryValueEx(key, 'ProxyEnable')[0]:
                proxy = winreg.QueryValueEx(key, 'ProxyServer')[0]
                if not proxy.startswith('127.0.0.1:'):
                    raise RuntimeError('Only the inspected existing local proxy is supported')
                env['HTTP_PROXY'] = env['HTTPS_PROXY'] = 'http://' + proxy
                env['NO_PROXY'] = 'localhost,127.0.0.1'
                meta['existing_windows_proxy_child_only'] = True
        process = subprocess.Popen(args, cwd=directory, env=env, stdout=stdout, stderr=stderr,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        meta['pid'] = process.pid
        (directory/'started.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'id': case['id'], 'pid': process.pid}), flush=True)
        try:
            process.wait(timeout=360)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            meta['timeout'] = True
    meta.update(exit_code=process.returncode, ended_at=datetime.now(timezone.utc).isoformat())
    events = []
    for line in (directory/'events.jsonl').read_text(encoding='utf-8').splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    commands = [e['item'] for e in events if e.get('type') == 'item.completed'
                and e.get('item', {}).get('type') == 'command_execution']
    skill_text = SKILL.read_text(encoding='utf-8')
    reads = [c for c in commands if _target_skill_read(c, skill_text)]
    mcp_reads = [e['item'] for e in events if e.get('type') == 'item.completed'
                 and e.get('item', {}).get('type') == 'mcp_tool_call'
                 and _target_skill_mcp_read(e['item'], skill_text)]
    meta['target_read_commands'] = reads
    meta['target_read_mcp_events'] = mcp_reads
    meta['thread_ids'] = [e.get('thread_id') for e in events if e.get('type') == 'thread.started']
    meta['terminal'] = [e for e in events if e.get('type') in ('turn.completed', 'turn.failed', 'error')]
    meta['final'] = (directory/'final.txt').read_text(encoding='utf-8') if (directory/'final.txt').exists() else ''
    meta['skill_unchanged'] = hashlib.sha256(SKILL.read_bytes()).hexdigest() == meta['skill_sha256']
    meta['observed_trigger'] = bool(reads or mcp_reads)
    meta['matches_expected'] = meta['exit_code'] == 0 and meta['observed_trigger'] == case['should_trigger']
    (directory/'result.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:meta[k] for k in ('id','pid','exit_code','observed_trigger','matches_expected')}), flush=True)
    return meta


if __name__ == '__main__':
    pack = json.loads(Path(__file__).with_name('evals.json').read_text(encoding='utf-8'))
    cases = [c for c in pack['cases'] if c['id'] in ('explicit', 'implicit', 'negative-color')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, cases))
    (OUT/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
