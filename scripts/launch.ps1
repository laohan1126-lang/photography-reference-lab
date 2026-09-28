$Host.UI.RawUI.WindowTitle = "摄影参考库 · 本地控制台"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$port = 18765
$url = "http://127.0.0.1:$port"
$wslDir = "/home/dell/projects/photography-reference-lab-regression"
$dataDir = "$wslDir/.local/regression-real-fixed"
$serverScript = "$wslDir/run_server.sh"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "               摄影参考库 · 私人本地控制台 (v0.3)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查服务是否已在运行
$alreadyRunning = $false
try {
    $resp = Invoke-RestMethod -Uri "$url/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
    if ($resp.status -eq "ok") {
        $alreadyRunning = $true
        Write-Host "[*] 检测到参考库服务已在后台运行中。" -ForegroundColor Green
    }
} catch {
    $alreadyRunning = $false
}

# 2. 如果未运行，启动 WSL 后端服务
if (-not $alreadyRunning) {
    Write-Host "[*] 正在启动后台服务，请稍候..." -ForegroundColor Yellow
    Start-Process -FilePath "wsl.exe" -ArgumentList "-e", $serverScript -WindowStyle Hidden
    
    # 轮询健康检查
    $attempts = 0
    $ready = $false
    while ($attempts -lt 20) {
        $attempts++
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-RestMethod -Uri "$url/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
            if ($resp.status -eq "ok") {
                $ready = $true
                break
            }
        } catch {
            # 继续重试
        }
    }
    
    if (-not $ready) {
        Write-Host "[!] 服务启动超时，请检查 WSL 状态或端口占用情况。" -ForegroundColor Red
        Write-Host "按任意键退出..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }
    Write-Host "[OK] 服务启动成功！" -ForegroundColor Green
}

# 3. 读取访问口令
$token = ""
try {
    $tokenOutput = (wsl.exe -e cat "$dataDir/access-token" 2>$null)
    if ($tokenOutput) {
        $token = $tokenOutput.Trim()
        Set-Clipboard -Value $token
    }
} catch {
    # 忽略读取异常
}

# 4. 打开浏览器
Start-Process $url

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  本地服务地址 : $url" -ForegroundColor White
if ($token) {
    Write-Host "  系统访问口令 : $token" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  [提示] 口令已自动复制到剪贴板！" -ForegroundColor Green
    Write-Host "         浏览器打开后，在输入框直接按 Ctrl + V 粘贴即可进入。" -ForegroundColor Green
} else {
    Write-Host "  [提示] 未获取到口令，请手动检查 $dataDir/access-token。" -ForegroundColor Yellow
}
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "如需停止后台服务，可随时双击运行 [停止参考库.bat] 或 [stop.bat]。" -ForegroundColor Gray
Write-Host ""
Write-Host "窗口可直接关闭，或按任意键退出控制台..." -ForegroundColor Gray
if ([Environment]::UserInteractive) {
    try {
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
        # Non-interactive shell fallback
    }
}
