
param(
    [switch]$NoOpen,
    [switch]$NoWait,
    [switch]$SkipExternalServices
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "摄影参考库 · Windows 本地控制台"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. (Join-Path $PSScriptRoot "runtime-common.ps1")

$config = Get-ReferenceLabRuntimeConfig -RequireLibrary
$python = Get-ReferenceLabPython
Assert-ReferenceLabPythonMatchesRepo -Python $python

$revision = Get-ReferenceLabRevision -RepoRoot $config.RepoRoot

$adapter = Join-Path $config.RepoRoot "tools\collect_adapter.py"
if (-not (Test-Path $adapter)) {
    throw "Collection adapter is missing from this checkout: $adapter"
}

New-Item -ItemType Directory -Path $config.RuntimeDir -Force | Out-Null
$pidFile = Get-ReferenceLabPidFile
$stdoutLog = Join-Path $config.RuntimeDir "server.stdout.log"
$stderrLog = Join-Path $config.RuntimeDir "server.stderr.log"
$url = $config.Url

function Test-ReferenceLabHealth {
    try {
        $resp = Invoke-RestMethod -Uri "$url/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        return ($resp.status -eq "ok")
    } catch {
        return $false
    }
}

function Get-ManagedServerRecord {
    if (-not (Test-Path $pidFile)) {
        return $null
    }
    try {
        return (Get-Content -LiteralPath $pidFile -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        throw "Runtime PID record is invalid. Refusing to replace it; inspect $pidFile."
    }
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "          摄影参考库 · Windows 主运行环境 (v0.3)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Repo     : $($config.RepoRoot)"
Write-Host "  Data     : $($config.DataDir)"
Write-Host "  URL      : $url"
Write-Host ""

$record = Get-ManagedServerRecord
$managedProcess = $null
if ($record) {
    $managedProcess = Get-ReferenceLabManagedProcess -Record $record -Config $config
    if (-not $managedProcess) {
        Remove-Item -LiteralPath $pidFile -Force
        $record = $null
    }
}

$alreadyHealthy = Test-ReferenceLabHealth
if ($alreadyHealthy) {
    if (-not $record -or -not $managedProcess) {
        throw "An unmanaged server already answers at $url. Stop it through its owner; this launcher will not adopt or kill it."
    }
    if ($record.code_revision -ne $revision) {
        throw "The managed server was started at another Git revision. Stop it with stop.bat, then start this revision."
    }
    Assert-ReferenceLabRuntimeIdentity -Runtime (Get-ReferenceLabRuntimeInfo -Config $config) -Config $config -ExpectedPid $managedProcess.Id
    Write-Host "[*] Windows reference-lab service is already running (PID $($record.pid))." -ForegroundColor Green
} else {
    if ($managedProcess) {
        throw "Managed Windows process PID $($record.pid) exists but health check failed. Run stop.bat, inspect $stderrLog, then start again."
    }

    $env:LAB_DATA_DIR = $config.DataDir
    $env:LAB_PUBLIC_ORIGIN = $url
    $env:LAB_COLLECTION_COMMAND = (@(
        $python,
        $adapter,
        "{task_file}",
        "{result_file}"
    ) | ConvertTo-Json -Compress)
    if (-not $env:HTTP_PROXY -and -not $env:http_proxy) {
        $env:HTTP_PROXY = "http://127.0.0.1:12000"
        $env:HTTPS_PROXY = "http://127.0.0.1:12000"
        $env:ALL_PROXY = "http://127.0.0.1:12000"
    }

    Write-Host "[*] Starting repo-local Windows backend..." -ForegroundColor Yellow
    # Avoid an inherited console/pipe: the stdlib owns only OS process creation.
    $spawnCode = @"
import subprocess, sys
with open(sys.argv[3], 'ab') as out, open(sys.argv[4], 'ab') as err:
    proc = subprocess.Popen(
        [sys.executable, '-m', 'ref_lab', 'serve', '--host', '127.0.0.1', '--port', sys.argv[2]],
        cwd=sys.argv[1], stdin=subprocess.DEVNULL, stdout=out, stderr=err,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
    )
    print(proc.pid)
"@
    $spawnedId = & $python -B -c $spawnCode $config.RepoRoot $config.Port $stdoutLog $stderrLog
    if ($LASTEXITCODE -ne 0 -or -not $spawnedId) { throw "Windows backend process creation failed; inspect runtime logs." }
    $process = Get-Process -Id ([int]$spawnedId) -ErrorAction Stop

    $record = [ordered]@{
        pid = $process.Id
        repo_root = $config.RepoRoot
        data_dir = $config.DataDir
        port = $config.Port
        python = $python
        adapter = $adapter
        code_revision = $revision
        started_at = $process.StartTime.ToUniversalTime().ToString("o")
        process_start_ticks = [string]$process.StartTime.ToUniversalTime().Ticks
        process_path = $process.Path
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8

    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            break
        }
        $runtime = Get-ReferenceLabRuntimeInfo -Config $config
        if ($runtime) {
            try {
                $serverProcess = Get-Process -Id ([int]$runtime.pid) -ErrorAction Stop
                # Windows venv python.exe wraps the real interpreter in one child process.
                if ($serverProcess.Id -ne $process.Id) {
                    $serverParent = (Get-CimInstance Win32_Process -Filter "ProcessId = $($serverProcess.Id)" -ErrorAction Stop).ParentProcessId
                    if ($serverParent -ne $process.Id) { throw "Endpoint belongs to a process we did not start." }
                }
                Assert-ReferenceLabRuntimeIdentity -Runtime $runtime -Config $config -ExpectedPid $serverProcess.Id
                $record.pid = $serverProcess.Id
                $record.started_at = $serverProcess.StartTime.ToUniversalTime().ToString("o")
                $record.process_start_ticks = [string]$serverProcess.StartTime.ToUniversalTime().Ticks
                $record.process_path = $serverProcess.Path
                $record | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
                $ready = $true
            } catch {
                Write-Host "[!] Backend identity verification failed: $_" -ForegroundColor Yellow
            }
            break
        }
    }

    if (-not $ready) {
        if (-not $process.HasExited) {
            $ownedProcess = Get-ReferenceLabManagedProcess -Record $record -Config $config
            if ($ownedProcess) { & taskkill.exe /PID $ownedProcess.Id /T /F *> $null }
        }
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        throw "Windows backend did not become healthy. Inspect $stderrLog and $stdoutLog."
    }

    Write-Host "[OK] Windows backend started (PID $($record.pid))." -ForegroundColor Green
}

$tunnelReady = $false
$browserReady = $false
if (-not $SkipExternalServices) {
    . (Join-Path $PSScriptRoot "ensure-external-services.ps1")
    $tunnelReady = Ensure-CloudflareTunnel -Config $config -ExpectedPid $record.pid
    $browserReady = Ensure-BrowserSkillDaemon
}

if (-not $NoOpen) { Start-Process $url }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  电脑访问 : $url" -ForegroundColor White
if ($tunnelReady) {
    Write-Host "  手机访问 : https://ref.koshikorato.top" -ForegroundColor Green
} else {
    Write-Host "  手机访问 : 未验证连到本资料库，请查看隧道检查结果。" -ForegroundColor Yellow
}
if ($browserReady) {
    Write-Host "  采集浏览器 : Edge 已连接；平台登录仍需正常有效。" -ForegroundColor Green
} else {
    Write-Host "  采集浏览器 : 未就绪；请打开 Edge 并检查 BrowserSkill 扩展。" -ForegroundColor Yellow
}
$session = Invoke-RestMethod -Uri "$url/api/session" -TimeoutSec 2 -ErrorAction Stop
if ($session.no_auth) {
    Write-Host "  模式     : 当前资料库免密访问。" -ForegroundColor Cyan
} else {
    Write-Host "  口令     : run .venv\Scripts\python.exe -m ref_lab token locally" -ForegroundColor Gray
}
Write-Host "  Stop     : double-click stop.bat" -ForegroundColor Gray
Write-Host "================================================================" -ForegroundColor Cyan

if (-not $NoWait -and [Environment]::UserInteractive) {
    Write-Host ""
    Write-Host "Close this window or press any key; the backend remains managed by stop.bat." -ForegroundColor Gray
    try {
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
    }
}
