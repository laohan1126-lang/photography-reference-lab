
param(
    [switch]$NoOpen,
    [switch]$NoWait
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "摄影参考库 · Windows 本地控制台"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. (Join-Path $PSScriptRoot "runtime-common.ps1")

$config = Get-ReferenceLabRuntimeConfig -RequireLibrary
$python = Get-ReferenceLabPython
Assert-ReferenceLabPythonMatchesRepo -Python $python

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
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        return $null
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
if ($record -and $record.pid) {
    $managedProcess = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
    if (-not $managedProcess) {
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        $record = $null
    }
}

$alreadyHealthy = Test-ReferenceLabHealth
if ($alreadyHealthy) {
    if (-not $record -or -not $managedProcess) {
        throw @"
A healthy reference-lab service already answers at $url, but it was not started by this Windows launcher.
Refusing to attach to an unmanaged/legacy WSL process because that would make the running code version ambiguous.

Stop the old WSL service first, then run start.bat again.
"@
    }
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

    Write-Host "[*] Starting repo-local Windows backend..." -ForegroundColor Yellow
    $startArgs = @{
        FilePath = $python
        ArgumentList = @("-m", "ref_lab", "serve", "--host", "127.0.0.1", "--port", "$($config.Port)")
        WorkingDirectory = $config.RepoRoot
        WindowStyle = "Hidden"
        RedirectStandardOutput = $stdoutLog
        RedirectStandardError = $stderrLog
        PassThru = $true
    }
    $process = Start-Process @startArgs

    $record = [ordered]@{
        pid = $process.Id
        repo_root = $config.RepoRoot
        data_dir = $config.DataDir
        port = $config.Port
        python = $python
        adapter = $adapter
        started_at = (Get-Date).ToString("o")
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8

    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            break
        }
        if (Test-ReferenceLabHealth) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        if (-not $process.HasExited) {
            & taskkill.exe /PID $process.Id /T /F *> $null
        }
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        throw "Windows backend did not become healthy. Inspect $stderrLog and $stdoutLog."
    }

    Write-Host "[OK] Windows backend started (PID $($process.Id))." -ForegroundColor Green
}

$token = ""
$tokenFile = Join-Path $config.DataDir "access-token"
if (Test-Path $tokenFile) {
    try {
        $token = (Get-Content -LiteralPath $tokenFile -Raw -Encoding UTF8).Trim()
        if ($token) {
            Set-Clipboard -Value $token
        }
    } catch {
        Write-Host "[!] Could not copy the access token to clipboard." -ForegroundColor Yellow
    }
}

if (-not $NoOpen) {
    Start-Process $url
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Runtime : Windows Python + Windows BrowserSkill/Edge" -ForegroundColor White
Write-Host "  URL     : $url" -ForegroundColor White
if ($token) {
    Write-Host "  Token   : copied to clipboard" -ForegroundColor Green
} else {
    Write-Host "  Token   : run .venv\Scripts\python.exe -m ref_lab token" -ForegroundColor Yellow
}
Write-Host "  Stop    : double-click stop.bat" -ForegroundColor Gray
Write-Host "================================================================" -ForegroundColor Cyan

if (-not $NoWait -and [Environment]::UserInteractive) {
    Write-Host ""
    Write-Host "Close this window or press any key; the backend remains managed by stop.bat." -ForegroundColor Gray
    try {
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
    }
}
