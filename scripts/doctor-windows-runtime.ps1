param([switch]$RepairDerived)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "runtime-common.ps1")

$config = Get-ReferenceLabRuntimeConfig -RequireLibrary
$python = Get-ReferenceLabPython
Assert-ReferenceLabPythonMatchesRepo -Python $python

$oldDataDir = $env:LAB_DATA_DIR
try {
    $env:LAB_DATA_DIR = $config.DataDir
    $args = @("-m", "ref_lab", "doctor")
    if ($RepairDerived) {
        $args += "--repair-derived"
    }
    & $python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Reference-lab doctor reported a failure for $($config.DataDir)."
    }
} finally {
    if ($null -eq $oldDataDir) {
        Remove-Item Env:LAB_DATA_DIR -ErrorAction SilentlyContinue
    } else {
        $env:LAB_DATA_DIR = $oldDataDir
    }
}
