$Host.UI.RawUI.WindowTitle = "停止摄影参考库"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[*] 正在停止后台服务..." -ForegroundColor Yellow
try {
    wsl.exe -e bash -c "pkill -f 'ref_lab serve'" 2>$null
    Start-Sleep -Seconds 1
    Write-Host "[OK] 摄影参考库服务已安全停止。" -ForegroundColor Green
} catch {
    Write-Host "[!] 停止过程中出现异常: $_" -ForegroundColor Red
}

Start-Sleep -Seconds 2
