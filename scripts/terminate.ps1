
param([switch]$NoWait)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "停止摄影参考库"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. (Join-Path $PSScriptRoot "runtime-common.ps1")

$pidFile = Get-ReferenceLabPidFile

if (-not (Test-Path $pidFile)) {
    Write-Host "[*] No Windows-managed reference-lab PID record was found." -ForegroundColor Yellow
    Write-Host "    If an older WSL service is still running, stop it explicitly before migration." -ForegroundColor Yellow
    exit 0
}

try {
    $record = Get-Content -LiteralPath $pidFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $serverPid = [int]$record.pid
} catch {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    throw "Runtime PID record was invalid and has been removed."
}

$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($process) {
    $expectedRepo = [System.IO.Path]::GetFullPath([string]$record.repo_root)
    $expectedPython = [System.IO.Path]::GetFullPath([string]$record.python)
    if ($expectedRepo -ne $script:RepoRoot) {
        throw "PID record belongs to another checkout ($expectedRepo). Refusing to kill PID $serverPid."
    }
    if ($process.Path -and ([System.IO.Path]::GetFullPath($process.Path) -ne $expectedPython)) {
        throw "PID $serverPid is now owned by a different executable. Refusing to kill it; remove the stale runtime record only after inspection."
    }

    Write-Host "[*] Stopping Windows reference-lab process tree (PID $serverPid)..." -ForegroundColor Yellow
    & taskkill.exe /PID $serverPid /T /F *> $null
    Start-Sleep -Milliseconds 500
    if (Get-Process -Id $serverPid -ErrorAction SilentlyContinue) {
        throw "Windows reference-lab process $serverPid is still running."
    }
    Write-Host "[OK] Windows reference-lab service stopped." -ForegroundColor Green
} else {
    Write-Host "[*] PID $serverPid was already gone; removing stale runtime record." -ForegroundColor Yellow
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

if (-not $NoWait -and [Environment]::UserInteractive) {
    Start-Sleep -Seconds 1
}
