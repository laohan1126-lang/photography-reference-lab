# scripts/ensure-external-services.ps1
# Ensures Cloudflare Tunnel (for mobile phone access) and BrowserSkill Daemon (for reference collection) are active.

$ErrorActionPreference = "Continue"

function Find-CloudflaredExe {
    $candidates = @(
        "C:\Program Files (x86)\cloudflared\cloudflared.exe",
        "C:\Program Files\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\cloudflared\cloudflared.exe",
        (Get-Command cloudflared.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Get-Command cloudflared -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) {
            return [System.IO.Path]::GetFullPath($c)
        }
    }
    return $null
}

function Find-CloudflaredConfig {
    $candidates = @(
        (Join-Path $env:USERPROFILE ".cloudflared\cloudflared-lab.yml"),
        (Join-Path $env:USERPROFILE "notebooklm-service\cloudflared-nblm.yml"),
        (Join-Path $env:USERPROFILE ".cloudflared\config.yml")
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) {
            $content = Get-Content -LiteralPath $c -Raw -ErrorAction SilentlyContinue
            if ($content -and $content -match "ref\.koshikorato\.top") {
                return [System.IO.Path]::GetFullPath($c)
            }
        }
    }
    return $null
}

function Ensure-CloudflareTunnel {
    # 1. Test if public endpoint is already healthy
    try {
        $resp = Invoke-RestMethod -Uri "https://ref.koshikorato.top/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($resp.status -eq "ok") {
            Write-Host "[OK] Cloudflare 隧道正常运行中 (https://ref.koshikorato.top)。" -ForegroundColor Green
            return $true
        }
    } catch {
    }

    # 2. Check if cloudflared process is already running
    $cfProcesses = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
    if ($cfProcesses) {
        for ($i = 0; $i -lt 5; $i++) {
            Start-Sleep -Seconds 1
            try {
                $resp = Invoke-RestMethod -Uri "https://ref.koshikorato.top/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
                if ($resp.status -eq "ok") {
                    Write-Host "[OK] Cloudflare 隧道已就绪 (https://ref.koshikorato.top)。" -ForegroundColor Green
                    return $true
                }
            } catch {
            }
        }
    }

    # 3. Start cloudflared
    $cfExe = Find-CloudflaredExe
    if (-not $cfExe) {
        Write-Host "[!] 未找到 cloudflared.exe，手机远程访问暂不可用。" -ForegroundColor Yellow
        return $false
    }
    $cfConfig = Find-CloudflaredConfig
    if (-not $cfConfig) {
        Write-Host "[!] 未找到包含 ref.koshikorato.top 的 cloudflared 配置文件。" -ForegroundColor Yellow
        return $false
    }

    Write-Host "[*] 正在启动 Cloudflare 隧道服务..." -ForegroundColor Yellow
    $prevHttp = $env:HTTP_PROXY
    $prevHttps = $env:HTTPS_PROXY
    try {
        $env:HTTP_PROXY = ""
        $env:HTTPS_PROXY = ""
        $startArgs = @{
            FilePath = $cfExe
            ArgumentList = @("tunnel", "--no-autoupdate", "--protocol", "http2", "--config", $cfConfig, "run")
            WindowStyle = "Hidden"
            PassThru = $true
        }
        $null = Start-Process @startArgs
    } finally {
        $env:HTTP_PROXY = $prevHttp
        $env:HTTPS_PROXY = $prevHttps
    }

    # Wait up to 10s for tunnel to connect
    $ready = $false
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-RestMethod -Uri "https://ref.koshikorato.top/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
            if ($resp.status -eq "ok") {
                $ready = $true
                break
            }
        } catch {
        }
    }

    if ($ready) {
        Write-Host "[OK] Cloudflare 隧道已成功启动 (https://ref.koshikorato.top)。" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[!] Cloudflare 隧道已拉起但未能连接，请检查网络。" -ForegroundColor Yellow
        return $false
    }
}

function Find-BskExe {
    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\bsk.exe"),
        (Get-Command bsk.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Get-Command bsk -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) {
            return [System.IO.Path]::GetFullPath($c)
        }
    }
    return $null
}

function Ensure-BrowserSkillDaemon {
    $bskExe = Find-BskExe
    if (-not $bskExe) {
        Write-Host "[!] 未找到 bsk.exe，无法自动启动 BrowserSkill。" -ForegroundColor Yellow
        return $false
    }

    $prevAuto = $env:BSK_AUTO_START
    $env:BSK_AUTO_START = "0"
    $isRunning = $false
    try {
        $output = & $bskExe status --json 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            $statusObj = $output | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($statusObj -and $statusObj.pid) {
                $isRunning = $true
            }
        }
    } catch {
    } finally {
        $env:BSK_AUTO_START = $prevAuto
    }

    if (-not $isRunning) {
        Write-Host "[*] 正在启动 BrowserSkill 后台守护服务..." -ForegroundColor Yellow
        $startArgs = @{
            FilePath = $bskExe
            ArgumentList = @("daemon", "start", "--foreground")
            WindowStyle = "Hidden"
            PassThru = $true
        }
        $null = Start-Process @startArgs
        Start-Sleep -Seconds 1
    }

    $env:BSK_AUTO_START = "0"
    try {
        $output = & $bskExe status --json 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            $statusObj = $output | ConvertFrom-Json -ErrorAction SilentlyContinue
            $edgeBrowser = $statusObj.browsers | Where-Object { $_.browser_name -eq "edge" } | Select-Object -First 1
            if ($edgeBrowser) {
                Write-Host "[OK] BrowserSkill 采集守护已就绪 (已绑定 Edge 浏览器: $($edgeBrowser.instance_id))。" -ForegroundColor Green
            } else {
                Write-Host "[*] BrowserSkill 采集守护已就绪 (PID $($statusObj.pid))。" -ForegroundColor Green
            }
            return $true
        }
    } catch {
    } finally {
        $env:BSK_AUTO_START = $prevAuto
    }

    Write-Host "[!] BrowserSkill 守护启动可能失败。" -ForegroundColor Yellow
    return $false
}

$isDotSourced = ($MyInvocation.InvocationName -eq '.') -or ($MyInvocation.Line -match '^\s*\.\s+')
if (-not $isDotSourced) {
    Ensure-CloudflareTunnel | Out-Null
    Ensure-BrowserSkillDaemon | Out-Null
}
