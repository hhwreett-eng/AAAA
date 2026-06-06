param(
    [string]$Config = "$PSScriptRoot\config.toml",
    [switch]$InitSeen,
    [string]$PythonExe = "C:\Users\0\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$argsList = @("$PSScriptRoot\monitor.py", "--config", $Config)
if ($InitSeen) {
    $argsList += "--init-seen"
}

& $PythonExe @argsList

