
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
    $recordMatches = (
        ([System.IO.Path]::GetFullPath([string]$record.repo_root) -eq $config.RepoRoot) -and
        ([System.IO.Path]::GetFullPath([string]$record.data_dir) -eq $config.DataDir) -and
        ([int]$record.port -eq $config.Port)
    )
    if (-not $recordMatches) {
        throw "Runtime PID record belongs to a different checkout/data configuration. Refusing to reuse it; inspect $pidFile."
    }

    $managedProcess = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
    if (-not $managedProcess) {
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        $record = $null
    } elseif ($managedProcess.ProcessName -notmatch "python") {
        throw "PID $($record.pid) was reused by a different executable ($($managedProcess.ProcessName)). Refusing to treat it as the reference-lab server."
    }
}

$alreadyHealthy = Test-ReferenceLabHealth
if ($alreadyHealthy) {
    if (-not $record -or -not $managedProcess) {
        $orphanConn = Get-NetTCPConnection -LocalPort $config.Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        $canAttach = $false
        if ($orphanConn -and $orphanConn.OwningProcess) {
            $orphanProc = Get-Process -Id $orphanConn.OwningProcess -ErrorAction SilentlyContinue
            if ($orphanProc -and ($orphanProc.ProcessName -match "python")) {
                $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($orphanConn.OwningProcess)" -ErrorAction SilentlyContinue).CommandLine
                $isSameRepo = ($cmdLine -like "*$($config.RepoRoot)*" -or $cmdLine -like "*ref_lab*")
                if ($isSameRepo) {
                    $record = [ordered]@{
                        pid = $orphanConn.OwningProcess
                        repo_root = $config.RepoRoot
                        data_dir = $config.DataDir
                        port = $config.Port
                        python = $python
                        adapter = $adapter
                        started_at = (Get-Date).ToString("o")
                    }
                    $record | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
                    $managedProcess = $orphanProc
                    $canAttach = $true
                    Write-Host "[*] 已检测到本地参考库服务正在运行 (PID $($record.pid)，可与手机端/外部隧道同时使用)。" -ForegroundColor Green
                }
            }
        }

        if (-not $canAttach) {
            $extraHint = "Stop the old WSL service first, then run start.bat again."
            if ($orphanConn -and $orphanConn.OwningProcess) {
                $orphanProc = Get-Process -Id $orphanConn.OwningProcess -ErrorAction SilentlyContinue
                if ($orphanProc) {
                    $extraHint = "An unmanaged Windows process (PID $($orphanConn.OwningProcess), $($orphanProc.ProcessName)) is occupying port $($config.Port). Run stop.bat to stop it, then run start.bat again."
                }
            }
            $msg = "A healthy reference-lab service already answers at $url, but it was not started by this Windows launcher.`n" +
                   "Refusing to attach to an unmanaged process because that would make the running code version ambiguous.`n`n" +
                   "$extraHint"
            throw $msg
        }
    } else {
        Write-Host "[*] Windows reference-lab service is already running (PID $($record.pid))." -ForegroundColor Green
    }
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

$servicesHelper = Join-Path $PSScriptRoot "ensure-external-services.ps1"
if (Test-Path $servicesHelper) {
    try {
        . $servicesHelper
        Ensure-CloudflareTunnel | Out-Null
        Ensure-BrowserSkillDaemon | Out-Null
    } catch {
        Write-Host "[!] 外部访问与采集服务检查异常: $_" -ForegroundColor Yellow
    }
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
Write-Host "  Runtime  : Windows Python + Windows BrowserSkill/Edge" -ForegroundColor White
Write-Host "  电脑访问 : $url" -ForegroundColor White
Write-Host "  手机访问 : https://ref.koshikorato.top" -ForegroundColor Green
if ($token) {
    Write-Host "  手机免密 : https://ref.koshikorato.top/?token=$token" -ForegroundColor Cyan
    Write-Host "  Token    : $token (已复制到剪贴板)" -ForegroundColor Green
} else {
    Write-Host "  Token    : run .venv\Scripts\python.exe -m ref_lab token" -ForegroundColor Yellow
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
