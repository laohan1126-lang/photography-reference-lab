
param([switch]$NoWait)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "停止摄影参考库"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

. (Join-Path $PSScriptRoot "runtime-common.ps1")

$pidFile = Get-ReferenceLabPidFile
$serverPid = $null
$stopped = $false

if (Test-Path $pidFile) {
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
        if ($process.Path -and ([System.IO.Path]::GetFullPath($process.Path) -ne $expectedPython) -and -not ($process.ProcessName -match "python")) {
            throw "PID $serverPid is now owned by a different executable. Refusing to kill it; remove the stale runtime record only after inspection."
        }

        Write-Host "[*] Stopping Windows reference-lab process tree (PID $serverPid)..." -ForegroundColor Yellow
        & taskkill.exe /PID $serverPid /T /F *> $null
        Start-Sleep -Milliseconds 500
        if (Get-Process -Id $serverPid -ErrorAction SilentlyContinue) {
            throw "Windows reference-lab process $serverPid is still running."
        }
        Write-Host "[OK] Windows reference-lab service stopped." -ForegroundColor Green
        $stopped = $true
    } else {
        Write-Host "[*] PID $serverPid was already gone; removing stale runtime record." -ForegroundColor Yellow
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$runtimePort = 18765
try {
    $runtimeConfig = Get-ReferenceLabRuntimeConfig
    if ($runtimeConfig -and $runtimeConfig.Port) {
        $runtimePort = [int]$runtimeConfig.Port
    }
} catch {
}

$conn = Get-NetTCPConnection -LocalPort $runtimePort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn -and $conn.OwningProcess) {
    $orphanPid = [int]$conn.OwningProcess
    $orphanProc = Get-Process -Id $orphanPid -ErrorAction SilentlyContinue
    if ($orphanProc -and ($orphanProc.ProcessName -match "python")) {
        Write-Host "[*] Found unmanaged reference-lab Python process on port $runtimePort (PID $orphanPid). Stopping it..." -ForegroundColor Yellow
        & taskkill.exe /PID $orphanPid /T /F *> $null
        Start-Sleep -Milliseconds 500
        if (-not (Get-Process -Id $orphanPid -ErrorAction SilentlyContinue)) {
            Write-Host "[OK] Unmanaged process $orphanPid stopped." -ForegroundColor Green
            $stopped = $true
        } else {
            throw "Failed to stop unmanaged process $orphanPid on port $runtimePort."
        }
    }
}

if (-not $stopped) {
    Write-Host "[*] No active reference-lab process was found on Windows." -ForegroundColor Yellow
    Write-Host "    If an older WSL service is still running, stop it explicitly before migration." -ForegroundColor Yellow
}

if (-not $NoWait -and [Environment]::UserInteractive) {
    Start-Sleep -Seconds 1
}

