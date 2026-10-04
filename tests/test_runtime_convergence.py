from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import site
import venv

import httpx
import subprocess
from types import SimpleNamespace

import pytest
from ref_lab import config

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
TOKEN = "synthetic-runtime-test-token-123456789"


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    repo = tmp_path / "checkout"
    repo.mkdir()
    monkeypatch.setattr(config, "ROOT", repo)
    for name in ("LAB_DATA_DIR", "LAB_NO_AUTH", "LAB_PUBLIC_ORIGIN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LAB_ACCESS_TOKEN", TOKEN)
    return repo


def test_bom_runtime_config_selects_configured_library(isolated_config):
    repo = isolated_config
    target = repo.parent / "selected-library"
    state = repo / ".local"
    state.mkdir()
    (state / "windows-runtime.json").write_text(json.dumps({"data_dir": str(target)}), encoding="utf-8-sig")
    (repo / "data").mkdir()
    assert config.Settings.from_env().data_dir == target.resolve()
    assert not (repo / "data" / "access-token").exists()


@pytest.mark.parametrize("raw", ["broken-json", "[]", '{}', '{"data_dir": 42}'])
def test_invalid_runtime_configuration_refuses_fallback(isolated_config, raw):
    repo = isolated_config
    (repo / ".local").mkdir()
    (repo / "data").mkdir()
    (repo / ".local" / "windows-runtime.json").write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="runtime configuration"):
        config.Settings.from_env()
    assert not (repo / ".local" / "access-token").exists()


def test_implicit_default_does_not_choose_unconfigured_data_folder(isolated_config):
    (isolated_config / "data").mkdir()
    assert config.Settings.from_env().data_dir == (isolated_config / ".local").resolve()


def test_relative_config_path_is_relative_to_checkout(isolated_config, monkeypatch):
    (isolated_config / ".local").mkdir()
    (isolated_config / ".local" / "windows-runtime.json").write_text('{"data_dir":"selected-library"}', encoding="utf-8")
    monkeypatch.chdir(isolated_config.parent)
    assert config.Settings.from_env().data_dir == isolated_config / "selected-library"


def test_no_auth_is_scoped_to_selected_library(isolated_config, monkeypatch):
    repo = isolated_config
    for directory in (repo / "data", repo / ".local"):
        directory.mkdir()
        (directory / "no-auth").touch()
    selected = repo.parent / "protected-library"
    monkeypatch.setenv("LAB_DATA_DIR", str(selected))
    assert config.Settings.from_env().no_auth is False
    (selected / "no-auth").touch()
    assert config.Settings.from_env().no_auth is True
    monkeypatch.setenv("LAB_NO_AUTH", "0")
    assert config.Settings.from_env().no_auth is False


@pytest.mark.parametrize("value", ["false", "no", "0", "true", "yes", "1", "invalid"])
def test_no_auth_environment_is_explicit(isolated_config, monkeypatch, value):
    monkeypatch.setenv("LAB_NO_AUTH", value)
    if value == "invalid":
        with pytest.raises(ValueError, match="LAB_NO_AUTH"):
            config.Settings.from_env()
    else:
        assert config.Settings.from_env().no_auth is (value in {"1", "true", "yes"})


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def powershell(code, *, env=None, shell=None):
    if os.name != "nt" or not POWERSHELL:
        pytest.skip("Native Windows PowerShell runtime regressions")
    encoded = base64.b64encode(code.encode("utf-16-le")).decode("ascii")
    completed = subprocess.run([shell or POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                               env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout


def common_code():
    return "$ErrorActionPreference='Stop'; . " + ps_quote(ROOT / "scripts/runtime-common.ps1") + "; "


@pytest.mark.parametrize("change", ["reused_pid", "foreign_python", "legacy_record", "wrong_data", "wrong_repo"])
def test_managed_process_requires_full_launch_identity(change, tmp_path):
    code = common_code() + """
$fakeStart = [datetime]'2026-01-01T00:00:00Z'
$config = [pscustomobject]@{RepoRoot=$script:RepoRoot; DataDir='D:/isolated-library'; Port=18765}
$record = [pscustomobject]@{pid=12345; repo_root=$config.RepoRoot; data_dir=$config.DataDir; port=18765; process_path='D:/venv/python.exe'; process_start_ticks=[string]$fakeStart.ToUniversalTime().Ticks}
$fakeProcess = [pscustomobject]@{Id=12345; Path=$record.process_path; StartTime=$fakeStart; ProcessName='python'}
function Get-Process { param($Id,$ErrorAction) return $fakeProcess }
"""
    changes = {
        "reused_pid": "$fakeProcess.StartTime=$fakeStart.AddSeconds(1)",
        "foreign_python": "$fakeProcess.Path='D:/foreign/python.exe'",
        "legacy_record": "$record.process_start_ticks=$null",
        "wrong_data": "$record.data_dir='D:/other-library'",
        "wrong_repo": "$record.repo_root='D:/other-checkout'",
    }
    code += changes[change] + "; $refused=$false; try { Get-ReferenceLabManagedProcess -Record $record -Config $config | Out-Null } catch { $refused=$true }; if (-not $refused) { throw 'Unsafe process identity was accepted' }"
    # A missing helper is a failure, not a false-positive rejection.
    code += "; if (-not (Get-Command Get-ReferenceLabManagedProcess -ErrorAction SilentlyContinue)) { throw 'Managed identity helper missing' }"
    powershell(code)


@pytest.mark.parametrize("change", ["wrong_pid", "wrong_source", "wrong_data", "wrong_database"])
def test_runtime_report_must_identify_selected_process_and_library(change):
    code = common_code() + """
$config = [pscustomobject]@{RepoRoot=$script:RepoRoot; DataDir='D:/isolated-library'; Port=18765}
$runtime = [pscustomobject]@{pid=12345; source=(Join-Path $config.RepoRoot 'ref_lab/api.py'); data_dir=$config.DataDir; database=(Join-Path $config.DataDir 'library.sqlite3')}
"""
    changes = {"wrong_pid": "$runtime.pid=99999", "wrong_source": "$runtime.source='D:/other/ref_lab/api.py'",
               "wrong_data": "$runtime.data_dir='D:/other-library'", "wrong_database": "$runtime.database='D:/other-library/library.sqlite3'"}
    code += changes[change] + "; $refused=$false; try { Assert-ReferenceLabRuntimeIdentity -Runtime $runtime -Config $config -ExpectedPid 12345 } catch { $refused=$true }; if (-not $refused) { throw 'Mismatched running library was accepted' }; if (-not (Get-Command Assert-ReferenceLabRuntimeIdentity -ErrorAction SilentlyContinue)) { throw 'Runtime identity helper missing' }"
    powershell(code)


def test_stop_does_not_kill_unmanaged_python_on_configured_port(tmp_path):
    code = common_code() + "$script:RuntimeDir=" + ps_quote(tmp_path / "runtime") + "; " + """
$script:killed=$false
function taskkill.exe { $script:killed=$true }
function Get-NetTCPConnection { return [pscustomobject]@{OwningProcess=12345} }
function Get-Process { return [pscustomobject]@{Id=12345; ProcessName='python'} }
function Get-ReferenceLabRuntimeConfig { return [pscustomobject]@{Port=18765} }
"""
    code += "$text=Get-Content -Raw -Encoding UTF8 " + ps_quote(ROOT / "scripts/terminate.ps1") + "; $text=$text.Replace(" + ps_quote('. (Join-Path $PSScriptRoot "runtime-common.ps1")') + ", ''); & ([scriptblock]::Create($text)) -NoWait; if ($script:killed) { throw 'Killed an unmanaged process' }"
    powershell(code)


@pytest.mark.parametrize("browsers,expected", [([], False), ([{"browser_name": "edge", "instance_id": "synthetic-browser"}], True)])
def test_daemon_presence_is_not_browser_availability(browsers, expected):
    status = json.dumps({"pid": 12345, "browsers": browsers})
    code = "$ErrorActionPreference='Stop'; . " + ps_quote(ROOT / "scripts/ensure-external-services.ps1") + "; "
    code += "function Find-BskExe { return 'Invoke-SyntheticBsk' }; function Invoke-SyntheticBsk { $global:LASTEXITCODE=0; return " + ps_quote(status) + " }; "
    code += "$actual=Ensure-BrowserSkillDaemon; if ($actual -ne $" + str(expected).lower() + ") { throw 'Incorrect browser availability' }"
    powershell(code)


def test_detached_entrypoint_delegates_without_replacing_configuration(monkeypatch):
    spec = importlib.util.spec_from_file_location("runtime_delegate", ROOT / "tools/start_backend_daemon.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "urllib"):
        monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("No live endpoints in this test")))
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda argv, **kwargs: calls.append((argv, kwargs)) or SimpleNamespace(returncode=7))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **kw: pytest.fail("Duplicate backend process creation"))
    monkeypatch.setenv("LAB_DATA_DIR", "synthetic-selected-library")
    assert module.main() == 7
    argv, kwargs = calls[0]
    assert str(ROOT / "scripts/launch.ps1") in argv
    assert "-NoOpen" in argv and "-NoWait" in argv
    assert "env" not in kwargs


@pytest.mark.skipif(os.name != "nt", reason="Native Windows process lifecycle")
@pytest.mark.parametrize("shell", [shutil.which("pwsh"), shutil.which("powershell")])
def test_windows_launcher_checks_actual_runtime_and_stops_its_instance(tmp_path, shell):
    if not shell:
        pytest.skip("Requested PowerShell is not installed")
    # A self-contained temporary checkout, never the normal service/data directory.
    repo = tmp_path / "runtime-checkout"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    for name in ("runtime-common.ps1", "launch.ps1", "terminate.ps1", "ensure-external-services.ps1"):
        shutil.copyfile(ROOT / "scripts" / name, scripts / name)
    shutil.copytree(ROOT / "ref_lab", repo / "ref_lab", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "web", repo / "web")
    (repo / "tools").mkdir()
    shutil.copyfile(ROOT / "tools/collect_adapter.py", repo / "tools/collect_adapter.py")
    git = ["git", "-C", str(repo)]
    subprocess.run(git + ["init", "-q"], check=True, capture_output=True)
    subprocess.run(git + ["add", "scripts", "ref_lab", "web", "tools"], check=True, capture_output=True)
    commit = git + ["-c", "user.name=Runtime Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "--no-verify"]
    subprocess.run(commit + ["-m", "Synthetic runtime fixture"], check=True, capture_output=True)
    venv.EnvBuilder(with_pip=False).create(repo / ".venv")
    from ref_lab.service import Library
    data = tmp_path / "library"
    Library(config.Settings(data, TOKEN))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(repo), *site.getsitepackages())),
           "PYTHONDONTWRITEBYTECODE": "1", "LAB_DATA_DIR": str(data), "LAB_PORT": str(port),
           "LAB_ACCESS_TOKEN": TOKEN, "LAB_NO_AUTH": "0"}
    base = f"http://127.0.0.1:{port}"
    record_file = repo / ".local/runtime/server.json"
    record = None
    launch = "Set-Location " + ps_quote(repo) + "; & " + ps_quote(scripts / "launch.ps1") + " -NoOpen -NoWait -SkipExternalServices"
    try:
        powershell(launch, env=env, shell=shell)
        record = json.loads(record_file.read_text(encoding="utf-8-sig"))
        with httpx.Client(trust_env=False, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
            runtime = client.get(base + "/api/runtime").json()
            assert runtime["pid"] == record["pid"]
            assert Path(runtime["source"]) == repo / "ref_lab/api.py"
            assert Path(runtime["database"]) == data / "library.sqlite3"
            assert record["process_start_ticks"]
            # The same recorded instance is reused; a second checkout/library is refused.
            powershell(launch, env=env, shell=shell)
            different = {**env, "LAB_DATA_DIR": str(data.parent / "different-library")}
            Path(different["LAB_DATA_DIR"]).mkdir()
            (Path(different["LAB_DATA_DIR"]) / "library.sqlite3").touch()
            refused = "$refused=$false; try { " + launch + " } catch { $refused=$true }; if (-not $refused) { throw 'Wrong library was reused' }"
            powershell(refused, env=different, shell=shell)
            assert client.get(base + "/api/runtime").json()["pid"] == record["pid"]
            # A stale PID creation time must not stop even this test's own server.
            changed = {**record, "process_start_ticks": str(int(record["process_start_ticks"]) + 1)}
            record_file.write_text(json.dumps(changed), encoding="utf-8")
            stop = "& " + ps_quote(scripts / "terminate.ps1") + " -NoWait"
            refused = "$refused=$false; try { " + stop + " } catch { $refused=$true }; if (-not $refused) { throw 'Reused PID was killed' }"
            powershell(refused, env=env, shell=shell)
            assert client.get(base + "/api/runtime").json()["pid"] == record["pid"]
            record_file.write_text(json.dumps(record), encoding="utf-8")
            subprocess.run(commit + ["--allow-empty", "-m", "Another revision"], check=True, capture_output=True)
            refused = "$refused=$false; try { " + launch + " } catch { $refused=$true }; if (-not $refused) { throw 'Older revision was reused' }"
            powershell(refused, env=env, shell=shell)
            assert client.get(base + "/api/runtime").json()["pid"] == record["pid"]
    finally:
        if record is not None:
            record_file.write_text(json.dumps(record), encoding="utf-8")
        powershell("& " + ps_quote(scripts / "terminate.ps1") + " -NoWait", env=env, shell=shell)
    with httpx.Client(trust_env=False) as client:
        with pytest.raises(httpx.ConnectError):
            client.get(base + "/health")
    assert not record_file.exists()


@pytest.mark.parametrize("connected", [False, True])
def test_default_launcher_checks_connected_browser_and_keeps_failure_status(tmp_path, connected):
    status = json.dumps({"pid": 12345, "browsers": [{"browser_name": "edge", "instance_id": "synthetic"}] if connected else []})
    code = common_code() + ". " + ps_quote(ROOT / "scripts/ensure-external-services.ps1") + "; "
    code += "$script:RuntimeDir=" + ps_quote(tmp_path / "runtime") + "; "
    code += "$script:FakeConfig=[pscustomobject]@{RepoRoot=$script:RepoRoot; DataDir=" + ps_quote(tmp_path) + "; Port=18765; Url='http://127.0.0.1:18765'; RuntimeDir=$script:RuntimeDir}; "
    code += r"""
$fakeStart=[datetime]'2026-01-01T00:00:00Z'
$fakeProcess=[pscustomobject]@{Id=12345; Path='D:/synthetic/python.exe'; StartTime=$fakeStart}
$fakeRuntime=[pscustomobject]@{pid=12345; source=(Join-Path $script:RepoRoot 'ref_lab/api.py'); data_dir=$script:FakeConfig.DataDir; database=(Join-Path $script:FakeConfig.DataDir 'library.sqlite3')}
$fakeRecord=[pscustomobject]@{pid=12345; repo_root=$script:RepoRoot; data_dir=$script:FakeConfig.DataDir; port=18765; process_path=$fakeProcess.Path; process_start_ticks=[string]$fakeStart.ToUniversalTime().Ticks; code_revision=(Get-ReferenceLabRevision -RepoRoot $script:RepoRoot)}
$fakeRecord | ConvertTo-Json | Set-Content -LiteralPath (Get-ReferenceLabPidFile) -Encoding UTF8
function Get-ReferenceLabRuntimeConfig { return $script:FakeConfig }
function Get-ReferenceLabPython { return 'D:/synthetic/python.exe' }
function Assert-ReferenceLabPythonMatchesRepo { }
function Get-Process { param($Id,$Name,$ErrorAction) if (-not $Name) { return $fakeProcess } }
function Get-ReferenceLabRuntimeInfo { param($Config,$Origin) if ($Origin) { return [pscustomobject]@{pid=99999} }; return $fakeRuntime }
function Invoke-RestMethod { param($Uri,$TimeoutSec,$Method,$ErrorAction) if ($Uri.EndsWith('/health')) { return [pscustomobject]@{status='ok'} }; return [pscustomobject]@{no_auth=$true} }
function Find-CloudflaredExe { return $null }
function Find-BskExe { return 'Invoke-SyntheticBsk' }
$script:browserCalls=0
"""
    code += "function Invoke-SyntheticBsk { $script:browserCalls++; $global:LASTEXITCODE=0; return " + ps_quote(status) + " }; "
    code += "$text=Get-Content -Raw -Encoding UTF8 " + ps_quote(ROOT / "scripts/launch.ps1") + "; "
    for name in ("runtime-common.ps1", "ensure-external-services.ps1"):
        code += "$text=$text.Replace(" + ps_quote('. (Join-Path $PSScriptRoot "' + name + '")') + ", ''); "
    code += ". ([scriptblock]::Create($text)) -NoOpen -NoWait; if ($script:browserCalls -lt 1) { throw 'Default startup did not probe BrowserSkill' }; "
    code += "if ($browserReady -ne $" + str(connected).lower() + " -or $tunnelReady) { throw 'Readiness results were ignored' }"
    powershell(code)
