"""Start Reference Lab backend as a fully detached background Windows process.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

def ensure_external_services():
    helper = REPO_ROOT / "scripts" / "ensure-external-services.ps1"
    if helper.is_file():
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper)],
                capture_output=True,
                timeout=15
            )
        except Exception:
            pass

def main():
    runtime_dir = REPO_ROOT / ".local" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = runtime_dir / "server.stdout.log"
    stderr_log = runtime_dir / "server.stderr.log"

    env = dict(os.environ)
    env["LAB_DATA_DIR"] = str(REPO_ROOT / "data")
    env["LAB_PUBLIC_ORIGIN"] = "https://ref.koshikorato.top"
    adapter_path = REPO_ROOT / "tools" / "collect_adapter.py"
    if adapter_path.is_file():
        env["LAB_COLLECTION_COMMAND"] = json.dumps([PYTHON, str(adapter_path), "{task_file}", "{result_file}"])

    # Check if already running
    try:
        req = urllib.request.Request("http://127.0.0.1:18765/health")
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                print("Server is already running and healthy.")
                ensure_external_services()
                return 0
    except Exception:
        pass

    out_file = open(stdout_log, "a", encoding="utf-8")
    err_file = open(stderr_log, "a", encoding="utf-8")

    cmd = [PYTHON, "-m", "ref_lab", "serve", "--host", "127.0.0.1", "--port", "18765"]
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=out_file,
        stderr=err_file,
        creationflags=flags,
        close_fds=True
    )
    print(f"Spawned detached server PID {proc.pid}")

    # Wait up to 10 seconds for health check
    for _ in range(20):
        time.sleep(0.5)
        try:
            req = urllib.request.Request("http://127.0.0.1:18765/health")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    print("Server is up and healthy!")
                    ensure_external_services()
                    return 0
        except Exception:
            pass

    print("Warning: server started but health check timed out. Check .local/runtime/server.stderr.log")
    return 1


if __name__ == "__main__":
    sys.exit(main())
