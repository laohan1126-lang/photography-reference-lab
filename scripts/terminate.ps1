
param([switch]$NoWait)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "停止摄影参考库"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. (Join-Path $PSScriptRoot "runtime-common.ps1")

$pidFile = Get-ReferenceLabPidFile
if (Test-Path $pidFile) {
    try {
        $record = Get-Content -LiteralPath $pidFile -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw "Runtime PID record is invalid. Refusing to replace it or kill an unknown process."
    }
    $config = Get-ReferenceLabRuntimeConfig
    $process = Get-ReferenceLabManagedProcess -Record $record -Config $config
    $serverPid = [int]$record.pid
    if ($process) {
        Write-Host "[*] Stopping managed Windows reference-lab process tree (PID $serverPid)..." -ForegroundColor Yellow
        & taskkill.exe /PID $serverPid /T /F *> $null
        Start-Sleep -Milliseconds 500
        if (Get-Process -Id $serverPid -ErrorAction SilentlyContinue) {
            throw "Windows reference-lab process $serverPid is still running."
        }
        Write-Host "[OK] Windows reference-lab service stopped." -ForegroundColor Green
    } else {
        Write-Host "[*] Recorded process was already gone; removing stale record." -ForegroundColor Yellow
    }
    Remove-Item -LiteralPath $pidFile -Force
} else {
    Write-Host "[*] No managed Windows reference-lab process record was found." -ForegroundColor Yellow
}

if (-not $NoWait -and [Environment]::UserInteractive) {
    Start-Sleep -Seconds 1
}

