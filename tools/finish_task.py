#!/usr/bin/env python3
"""Opt-in task closeout. Stage only declared paths, never force-push or publish main."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def check_path(value: str) -> str:
    path = Path(value)
    resolved = (ROOT / path).resolve()
    if path.is_absolute() or not resolved.is_relative_to(ROOT):
        raise ValueError(f"Path must remain inside the repository: {value}")
    parts = resolved.relative_to(ROOT).parts
    if not parts or any(p in {'.git', '.local', '.venv', 'edge_profile', 'edge_xhs_profile', '.bsk'} for p in parts):
        raise ValueError(f"Refusing private/runtime path: {value}")
    if any(p.startswith('.env') and p != '.env.example' for p in parts) or path.suffix in {'.sqlite3', '.log'}:
        raise ValueError(f"Refusing possible secret/runtime file: {value}")
    return resolved.relative_to(ROOT).as_posix()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, help='Versioned docs/tasks entry')
    parser.add_argument('--paths', nargs='+', required=True, help='Explicit files/directories belonging to this task')
    parser.add_argument('--message', required=True)
    parser.add_argument('--browser', action='store_true', help='Include complete HTTP/browser/offline regression')
    parser.add_argument('--push', action='store_true', help='Explicitly authorize push to origin task branch')
    parser.add_argument('--sync-notion', action='store_true')
    args = parser.parse_args(argv)
    receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'tests': [], 'commit': None,
               'remote_verified': False, 'notion': 'not_requested'}
    try:
        task = check_path(args.task)
        if not task.startswith('docs/tasks/') or not (ROOT / task).is_file():
            raise ValueError('Task must be an existing docs/tasks file with intent and acceptance criteria')
        paths = sorted(set([task] + [check_path(path) for path in args.paths]))
        branch = run('git', 'branch', '--show-current')
        if not branch or branch in {'main', 'master'}:
            raise ValueError('Closeout requires an explicit task branch, not main/master/detached HEAD')
        if run('git', 'diff', '--cached', '--name-only'):
            raise ValueError('Index is not empty; review existing staged work before automated closeout')
        commands = [
            [sys.executable, '-m', 'pytest', '-q', 'tests/test_library.py', 'tests/test_imports_jobs.py', 'tests/test_workers.py', 'tests/test_operations.py'],
            ['node', '--check', 'web/app.js'],
        ]
        if args.browser:
            commands += [[sys.executable, '-m', 'pytest', '-q', 'tests/test_ui_components.py', 'tests/test_browser.py']]
        for command in commands:
            output = run(*command)
            receipt['tests'].append({'command': command, 'result': 'passed', 'output': output[-12000:]})
        run('git', 'add', '--', *paths)
        staged = run('git', 'diff', '--cached', '--name-only').splitlines()
        for path in staged: check_path(path)
        if not staged:
            raise ValueError('No changes to commit; no empty completion commit created')
        run('git', 'diff', '--cached', '--check')
        run('git', 'commit', '-m', args.message)
        receipt.update(branch=branch, commit=run('git', 'rev-parse', 'HEAD'))
        if args.push:
            run('git', 'push', '-u', 'origin', f'HEAD:refs/heads/{branch}')
            remote = run('git', 'ls-remote', '--heads', 'origin', f'refs/heads/{branch}')
            if not remote or remote.split()[0] != receipt['commit']:
                raise RuntimeError('Push returned, but remote SHA was not verified')
            receipt['remote_verified'] = True
        if args.sync_notion:
            try:
                result = run(sys.executable, '-m', 'ref_lab', 'sync-notion', '--task', task, '--commit', receipt['commit'])
                receipt['notion'] = json.loads(result)
            except (RuntimeError, ValueError) as exc:
                receipt['notion'] = {'status': 'pending', 'reason': str(exc)[-2000:]}
        receipt['status'] = 'saved' if not args.push else 'pushed_and_verified'
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        receipt.update(status='failed', error=str(exc))
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        folder = ROOT / '.local/closeout'
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (folder / f'{stamp}.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
