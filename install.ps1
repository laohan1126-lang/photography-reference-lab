param([switch]$WithBrowser)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { throw "Install Python 3.11 or newer, then run this script again." }
& $Python.Source -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw "Unsupported Python version." }
if (-not (Test-Path .venv\Scripts\python.exe)) {
    & $Python.Source -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
& .venv\Scripts\python.exe -m pip install -e ".[test]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
if ($WithBrowser) {
    & .venv\Scripts\python.exe -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Browser installation failed." }
}
Write-Host "Installed. Next: .venv\Scripts\python.exe -m ref_lab migrate-legacy"
Write-Host "Then: .venv\Scripts\python.exe -m ref_lab serve"
Write-Host "In another terminal: .venv\Scripts\python.exe -m ref_lab token"
