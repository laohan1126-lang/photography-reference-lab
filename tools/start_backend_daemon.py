"""Compatibility entry point; the Windows launcher owns configuration and processes."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(REPO_ROOT / "scripts" / "launch.ps1"), "-NoOpen", "-NoWait"],
        cwd=REPO_ROOT,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
