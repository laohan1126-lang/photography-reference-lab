
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
    $pid = [int]$record.pid
} catch {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    throw "Runtime PID record was invalid and has been removed."
}

$process = Get-Process -Id $pid -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "[*] Stopping Windows reference-lab process tree (PID $pid)..." -ForegroundColor Yellow
    & taskkill.exe /PID $pid /T /F *> $null
    Start-Sleep -Milliseconds 500
    if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
        throw "Windows reference-lab process $pid is still running."
    }
    Write-Host "[OK] Windows reference-lab service stopped." -ForegroundColor Green
} else {
    Write-Host "[*] PID $pid was already gone; removing stale runtime record." -ForegroundColor Yellow
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

if (-not $NoWait -and [Environment]::UserInteractive) {
    Start-Sleep -Seconds 1
}
