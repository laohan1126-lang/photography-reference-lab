$ErrorActionPreference = "Stop"

$script:RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$script:LocalStateDir = Join-Path $script:RepoRoot ".local"
$script:RuntimeDir = Join-Path $script:LocalStateDir "runtime"
$script:WindowsRuntimeConfigPath = Join-Path $script:LocalStateDir "windows-runtime.json"

function Resolve-ReferenceLabPath {
    param([Parameter(Mandatory = $true)][string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $script:RepoRoot $PathValue))
}

function Get-ReferenceLabRuntimeConfig {
    param([switch]$RequireLibrary)

    $port = 18765
    $dataDirValue = $env:LAB_DATA_DIR

    if (Test-Path $script:WindowsRuntimeConfigPath) {
        $stored = Get-Content -LiteralPath $script:WindowsRuntimeConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not ($stored -is [pscustomobject]) -or -not ($stored.data_dir -is [string]) -or -not $stored.data_dir.Trim()) {
            throw "Windows runtime configuration requires a non-empty data_dir."
        }
        if (-not $dataDirValue) {
            $dataDirValue = $stored.data_dir
        }
        if (-not $env:LAB_PORT -and $stored.port) {
            $port = [int]$stored.port
        }
    }

    if ($env:LAB_PORT) {
        $parsedPort = 0
        if (-not [int]::TryParse($env:LAB_PORT, [ref]$parsedPort)) {
            throw "LAB_PORT must be an integer between 1 and 65535."
        }
        $port = $parsedPort
    }

    if ($port -lt 1 -or $port -gt 65535) {
        throw "Configured port must be between 1 and 65535."
    }

    if (-not $dataDirValue) {
        $repoLocalDb = Join-Path $script:LocalStateDir "library.sqlite3"
        if (Test-Path $repoLocalDb) {
            $dataDirValue = $script:LocalStateDir
        }
    }

    if (-not $dataDirValue) {
        throw @"
Windows runtime data is not configured.
This launcher intentionally refuses to create a new empty library silently.

After restoring the existing library to a Windows directory, run:
  powershell -ExecutionPolicy Bypass -File scripts\configure-windows-runtime.ps1 -DataDir "D:\path\to\reference-lab-data"

For a deliberate brand-new empty library, add -InitializeEmpty.
"@
    }

    $dataDir = Resolve-ReferenceLabPath $dataDirValue
    if (-not (Test-Path $dataDir)) {
        throw "Configured LAB_DATA_DIR does not exist: $dataDir"
    }

    $database = Join-Path $dataDir "library.sqlite3"
    if ($RequireLibrary -and -not (Test-Path $database)) {
        throw "Configured LAB_DATA_DIR has no library.sqlite3: $dataDir. Restore the library first or explicitly initialize it with configure-windows-runtime.ps1 -InitializeEmpty."
    }

    return [pscustomobject]@{
        RepoRoot = $script:RepoRoot
        DataDir = $dataDir
        Port = $port
        Url = "http://127.0.0.1:$port"
        RuntimeDir = $script:RuntimeDir
        ConfigPath = $script:WindowsRuntimeConfigPath
    }
}

function Get-ReferenceLabPython {
    $python = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "Windows virtual environment is missing: $python. Run .\install.ps1 first."
    }
    return [System.IO.Path]::GetFullPath($python)
}

function Assert-ReferenceLabPythonMatchesRepo {
    param([Parameter(Mandatory = $true)][string]$Python)

    $loaded = (& $Python -c "import pathlib, ref_lab; print(pathlib.Path(ref_lab.__file__).resolve())" 2>$null | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0 -or -not $loaded) {
        throw "The Windows virtual environment cannot import ref_lab. Run .\install.ps1 again."
    }

    $loadedPath = [System.IO.Path]::GetFullPath($loaded.Trim())
    $repoPrefix = $script:RepoRoot.TrimEnd("\") + "\"
    if (-not $loadedPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Split-brain runtime refused: Windows Python imports ref_lab from '$loadedPath' instead of this checkout '$script:RepoRoot'. Reinstall the editable environment with .\install.ps1."
    }
}

function Get-ReferenceLabPidFile {
    New-Item -ItemType Directory -Path $script:RuntimeDir -Force | Out-Null
    return (Join-Path $script:RuntimeDir "server.json")
}

function Get-ReferenceLabManagedProcess {
    param($Record, $Config)

    if (-not $Record.pid -or
        [System.IO.Path]::GetFullPath([string]$Record.repo_root) -ne $Config.RepoRoot -or
        [System.IO.Path]::GetFullPath([string]$Record.data_dir) -ne $Config.DataDir -or
        [int]$Record.port -ne $Config.Port) {
        throw "Runtime PID record belongs to a different checkout/data configuration. Refusing to manage it."
    }
    $process = Get-Process -Id ([int]$Record.pid) -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    if (-not $Record.process_start_ticks -or -not $Record.process_path -or -not $process.Path -or
        [string]$process.StartTime.ToUniversalTime().Ticks -ne [string]$Record.process_start_ticks -or
        [System.IO.Path]::GetFullPath($process.Path) -ne [System.IO.Path]::GetFullPath([string]$Record.process_path)) {
        throw "Unverified or reused PID $($Record.pid). Refusing to manage it; inspect the runtime record."
    }
    return $process
}

function Get-ReferenceLabRuntimeInfo {
    param($Config, [string]$Origin = $Config.Url)

    $token = $env:LAB_ACCESS_TOKEN
    $tokenFile = Join-Path $Config.DataDir "access-token"
    if (-not $token -and (Test-Path $tokenFile)) {
        $token = (Get-Content -LiteralPath $tokenFile -Raw -Encoding UTF8).Trim()
    }
    $headers = @{}
    if ($token) { $headers.Authorization = "Bearer $token" }
    try {
        return (Invoke-RestMethod -Uri "$Origin/api/runtime" -Headers $headers -TimeoutSec 2 -ErrorAction Stop)
    } catch {
        return $null
    }
}

function Assert-ReferenceLabRuntimeIdentity {
    param($Runtime, $Config, [int]$ExpectedPid)

    if (-not $Runtime -or [int]$Runtime.pid -ne $ExpectedPid -or
        [System.IO.Path]::GetFullPath([string]$Runtime.source) -ne (Join-Path $Config.RepoRoot "ref_lab\api.py") -or
        [System.IO.Path]::GetFullPath([string]$Runtime.data_dir) -ne $Config.DataDir -or
        [System.IO.Path]::GetFullPath([string]$Runtime.database) -ne (Join-Path $Config.DataDir "library.sqlite3")) {
        throw "Running server identity does not match this process, checkout and library. Refusing to reuse it."
    }
}

function Get-ReferenceLabRevision {
    param([string]$RepoRoot)

    $revision = & git -C $RepoRoot rev-parse --verify HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $revision) { throw "Cannot identify this checkout's Git revision." }
    return $revision.Trim()
}
