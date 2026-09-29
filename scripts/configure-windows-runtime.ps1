param(
    [Parameter(Mandatory = $true)][string]$DataDir,
    [ValidateRange(1, 65535)][int]$Port = 18765,
    [switch]$InitializeEmpty
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "runtime-common.ps1")

$resolved = Resolve-ReferenceLabPath $DataDir

if (-not (Test-Path $resolved)) {
    if ($InitializeEmpty) {
        New-Item -ItemType Directory -Path $resolved -Force | Out-Null
    } else {
        throw "Data directory does not exist: $resolved. Restore the existing library first, or use -InitializeEmpty only for an intentional new library."
    }
}

$db = Join-Path $resolved "library.sqlite3"
if (-not (Test-Path $db) -and -not $InitializeEmpty) {
    throw "No library.sqlite3 found in $resolved. Refusing to configure an accidental empty library."
}

New-Item -ItemType Directory -Path $script:LocalStateDir -Force | Out-Null
$config = [ordered]@{
    data_dir = $resolved
    port = $Port
    allow_empty = [bool]$InitializeEmpty
}
$config | ConvertTo-Json | Set-Content -LiteralPath $script:WindowsRuntimeConfigPath -Encoding UTF8

Write-Host "[OK] Windows runtime configured." -ForegroundColor Green
Write-Host "  Repo      : $script:RepoRoot"
Write-Host "  Data dir  : $resolved"
Write-Host "  Port      : $Port"
Write-Host "  Config    : $script:WindowsRuntimeConfigPath"
if ($InitializeEmpty) {
    Write-Host "  Mode      : intentional empty library initialization" -ForegroundColor Yellow
} else {
    Write-Host "  Database  : existing library.sqlite3 required and found" -ForegroundColor Green
}
Write-Host ""
Write-Host "Next: .\start.bat"
