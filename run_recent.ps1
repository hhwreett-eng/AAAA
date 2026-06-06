param(
    [string]$Config = "$PSScriptRoot\config.toml",
    [int]$Days = 5,
    [int]$Limit = 200,
    [string]$PythonExe = "C:\Users\0\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

& $PythonExe "$PSScriptRoot\recent_digest.py" --config $Config --days $Days --limit $Limit

