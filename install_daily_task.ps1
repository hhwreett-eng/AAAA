param(
    [string]$TaskName = "TechInfluencerDailyMonitor",
    [string]$Time = "08:30",
    [string]$PythonExe = "C:\Users\0\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    [string]$ProjectDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe. Edit -PythonExe or install Python."
}

$script = Join-Path $ProjectDir "monitor.py"
$config = Join-Path $ProjectDir "config.toml"
$logDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$logFile = Join-Path $logDir "daily-task.log"
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$ProjectDir'; & '$PythonExe' '$script' --config '$config' *> '$logFile'`""

schtasks /Create /SC DAILY /TN $TaskName /TR $action /ST $Time /F
Write-Host "Installed daily task '$TaskName' at $Time."
Write-Host "Log file: $logFile"

