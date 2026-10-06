# scripts/ensure-external-services.ps1
# Ensures Cloudflare Tunnel (for mobile phone access) and BrowserSkill Daemon (for reference collection) are active.

$ErrorActionPreference = "Stop"

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

function Test-ReferenceLabPublicRuntime {
    param($Config, [int]$ExpectedPid)

    try {
        $runtime = Get-ReferenceLabRuntimeInfo -Config $Config -Origin "https://ref.koshikorato.top"
        Assert-ReferenceLabRuntimeIdentity -Runtime $runtime -Config $Config -ExpectedPid $ExpectedPid
        return $true
    } catch {
        return $false
    }
}

function Ensure-CloudflareTunnel {
    param($Config, [int]$ExpectedPid)

    if (Test-ReferenceLabPublicRuntime -Config $Config -ExpectedPid $ExpectedPid) {
        Write-Host "[OK] Cloudflare 已连到当前资料库。" -ForegroundColor Green
        return $true
    }

    # 2. Check if cloudflared process is already running
    $cfProcesses = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
    if ($cfProcesses) {
        for ($i = 0; $i -lt 5; $i++) {
            Start-Sleep -Seconds 1
            if (Test-ReferenceLabPublicRuntime -Config $Config -ExpectedPid $ExpectedPid) {
                Write-Host "[OK] Cloudflare 已连到当前资料库。" -ForegroundColor Green
                return $true
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
            ArgumentList = @("tunnel", "--no-autoupdate", "--no-prechecks", "--protocol", "http2", "--config", $cfConfig, "run")
            WindowStyle = "Hidden"
            PassThru = $true
        }
        $null = Start-Process @startArgs
    } catch {
        Write-Host "[!] Cloudflare 进程启动失败，手机访问未就绪。" -ForegroundColor Yellow
        return $false
    } finally {
        $env:HTTP_PROXY = $prevHttp
        $env:HTTPS_PROXY = $prevHttps
    }

    # Wait up to 10s for tunnel to connect
    $ready = $false
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        if (Test-ReferenceLabPublicRuntime -Config $Config -ExpectedPid $ExpectedPid) {
            $ready = $true
            break
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
            ArgumentList = @("daemon", "start", "--foreground", "--daemon-idle", "24h")
            WindowStyle = "Hidden"
            PassThru = $true
        }
        try {
            $null = Start-Process @startArgs
            Start-Sleep -Seconds 1
        } catch {
            Write-Host "[!] BrowserSkill 进程启动失败，采集未就绪。" -ForegroundColor Yellow
            return $false
        }
    }

    $env:BSK_AUTO_START = "0"
    try {
        $output = & $bskExe status --json 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            $statusObj = $output | ConvertFrom-Json -ErrorAction SilentlyContinue
            $edgeBrowser = $statusObj.browsers | Where-Object { $_.browser_name -eq "edge" -and $_.instance_id } | Select-Object -First 1
            if ($edgeBrowser) {
                Write-Host "[OK] BrowserSkill 采集守护已就绪 (已绑定 Edge 浏览器: $($edgeBrowser.instance_id))。" -ForegroundColor Green
                return $true
            }
            Write-Host "[!] BrowserSkill 守护已运行，但没有连接 Edge；采集尚不可用。" -ForegroundColor Yellow
            return $false
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
    . (Join-Path $PSScriptRoot "runtime-common.ps1")
    $config = Get-ReferenceLabRuntimeConfig -RequireLibrary
    $record = Get-Content -LiteralPath (Get-ReferenceLabPidFile) -Raw -Encoding UTF8 | ConvertFrom-Json
    $managedProcess = Get-ReferenceLabManagedProcess -Record $record -Config $config
    if (-not $managedProcess) { throw "Start the managed backend before checking external services." }
    $tunnelReady = Ensure-CloudflareTunnel -Config $config -ExpectedPid $managedProcess.Id
    $browserReady = Ensure-BrowserSkillDaemon
    if (-not ($tunnelReady -and $browserReady)) { exit 1 }
}
