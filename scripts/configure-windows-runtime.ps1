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
if (-not (Test-Path $db)) {
    if (-not $InitializeEmpty) {
        throw "No library.sqlite3 found in $resolved. Refusing to configure an accidental empty library."
    }

    $python = Get-ReferenceLabPython
    Assert-ReferenceLabPythonMatchesRepo -Python $python
    $oldDataDir = $env:LAB_DATA_DIR
    try {
        $env:LAB_DATA_DIR = $resolved
        & $python -m ref_lab doctor | Out-Host
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $db)) {
            throw "Intentional empty-library initialization did not create a healthy database."
        }
    } finally {
        if ($null -eq $oldDataDir) {
            Remove-Item Env:LAB_DATA_DIR -ErrorAction SilentlyContinue
        } else {
            $env:LAB_DATA_DIR = $oldDataDir
        }
    }
}

New-Item -ItemType Directory -Path $script:LocalStateDir -Force | Out-Null
$config = [ordered]@{
    data_dir = $resolved
    port = $Port
}
if (Test-Path $script:WindowsRuntimeConfigPath) {
    $previous = Get-Content -LiteralPath $script:WindowsRuntimeConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($key in @('history_roots', 'auto_classify', 'search_timeout_seconds')) {
        if ($null -ne $previous.$key) { $config[$key] = $previous.$key }
    }
}
$config | ConvertTo-Json | Set-Content -LiteralPath $script:WindowsRuntimeConfigPath -Encoding UTF8

Write-Host "[OK] Windows runtime configured." -ForegroundColor Green
Write-Host "  Repo      : $script:RepoRoot"
Write-Host "  Data dir  : $resolved"
Write-Host "  Port      : $Port"
Write-Host "  Config    : $script:WindowsRuntimeConfigPath"
if ($InitializeEmpty) {
    Write-Host "  Mode      : intentional empty library initialized now" -ForegroundColor Yellow
}
Write-Host "  Database  : library.sqlite3 present" -ForegroundColor Green
Write-Host ""
Write-Host "Next: .\start.bat"
