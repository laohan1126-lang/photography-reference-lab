param([switch]$WithBrowser)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { throw "Install Python 3.11 or newer, then run this script again." }
& $Python.Source -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw "Unsupported Python version." }
if ((Test-Path .venv) -and -not (Test-Path .venv\Scripts\python.exe)) {
    throw ".venv exists but is not a Windows virtual environment. Refusing to overwrite a possible WSL/Linux venv; rename/remove it explicitly, then rerun install.ps1."
}
if (-not (Test-Path .venv\Scripts\python.exe)) {
    & $Python.Source -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install -e ".[test]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
. (Join-Path $PSScriptRoot "scripts\runtime-common.ps1")
Assert-ReferenceLabPythonMatchesRepo -Python (Get-ReferenceLabPython)
if ($WithBrowser) {
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Browser installation failed." }
}
Write-Host "Installed Windows runtime for this checkout." -ForegroundColor Green
Write-Host "Existing library: restore it to a Windows directory, then configure:"
Write-Host '  powershell -ExecutionPolicy Bypass -File scripts\configure-windows-runtime.ps1 -DataDir "D:\path\to\reference-lab-data"'
Write-Host "Intentional new empty library:"
Write-Host '  powershell -ExecutionPolicy Bypass -File scripts\configure-windows-runtime.ps1 -DataDir ".local" -InitializeEmpty'
Write-Host "Then run: .\start.bat"
