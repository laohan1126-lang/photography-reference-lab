from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def test_windows_launcher_is_repo_local_and_not_wsl_bound():
    launch = read("scripts/launch.ps1")
    assert "wsl.exe" not in launch.lower()
    assert "photography-reference-lab-regression" not in launch
    assert "run_server.sh" not in launch
    assert "Get-ReferenceLabPython" in launch
    assert "Assert-ReferenceLabPythonMatchesRepo" in launch
    assert "tools\\collect_adapter.py" in launch
    assert "LAB_COLLECTION_COMMAND" in launch
    assert "Split-brain" in read("scripts/runtime-common.ps1")


def test_windows_installer_refuses_to_overwrite_a_foreign_venv():
    install = read("install.ps1")
    assert "not a Windows virtual environment" in install
    assert "Assert-ReferenceLabPythonMatchesRepo" in install
    assert "runtime-common.ps1" in install


def test_windows_doctor_uses_the_same_configured_data_dir():
    doctor = read("scripts/doctor-windows-runtime.ps1")
    assert "Get-ReferenceLabRuntimeConfig -RequireLibrary" in doctor
    assert "$env:LAB_DATA_DIR = $config.DataDir" in doctor
    assert "Assert-ReferenceLabPythonMatchesRepo" in doctor


def test_windows_runtime_requires_explicit_data_configuration():
    common = read("scripts/runtime-common.ps1")
    configure = read("scripts/configure-windows-runtime.ps1")
    assert "refuses to create a new empty library silently" in common
    assert "library.sqlite3" in common
    assert "windows-runtime.json" in common
    assert "InitializeEmpty" in configure
    assert "No library.sqlite3 found" in configure


def test_windows_stop_is_pid_scoped_not_global_python_or_wsl_kill():
    terminate = read("scripts/terminate.ps1").lower()
    assert "pkill" not in terminate
    assert "wsl.exe" not in terminate
    assert "taskkill.exe /pid $serverpid /t /f" in terminate
    assert "get-process -id $serverpid" in terminate


def test_browserskill_discovery_has_no_owner_specific_path():
    source = read("tools/collect_adapter.py")
    assert "Users/Dell" not in source
    assert r"C:\Users\Dell" not in source
    assert 'Path.home()' in source
    assert 'Path("/mnt/c/Users")' in source
    assert 'glob("*/.local/bin/bsk.exe")' in source


def test_docs_name_windows_as_primary_and_wsl_as_compatibility():
    readme = read("README.md")
    compatibility = read("docs/COMPATIBILITY.md")
    assert "Windows：日常主运行环境" in readme
    assert "WSL / Linux：兼容与开发路径" in readme
    assert "Windows 是当前日常主运行环境" in compatibility
    assert "禁止 Windows 与 WSL 轮流打开同一个活动 SQLite" in read("docs/DEPLOYMENT.md")


def test_windows_launcher_ensures_external_services():
    launch = read("scripts/launch.ps1")
    assert "ensure-external-services.ps1" in launch
    assert "Ensure-CloudflareTunnel" in launch
    assert "Ensure-BrowserSkillDaemon" in launch
    helper = read("scripts/ensure-external-services.ps1")
    assert "ref.koshikorato.top" in helper
    assert "bsk" in helper
