# Creates/updates Windows Task Scheduler job to run daily.
# Run in an elevated PowerShell if your Task Scheduler policy requires it.

[CmdletBinding()]
param(
  [string]$TaskName = "AnexTourDailyParse",
  [string]$ProjectRoot = "D:\asoiu\проект",
  [string]$At = "03:30"  # local time (Asia/Irkutsk)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script = Join-Path $ProjectRoot "bin\run_daily_parse_and_import.ps1"
if (!(Test-Path $script)) { throw "Not found: $script" }

$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""

# Recreate idempotently
schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
schtasks /Create /TN $TaskName /SC DAILY /ST $At /RL HIGHEST /F /TR $action | Out-Null

Write-Host ("Installed scheduled task: " + $TaskName)
Write-Host ("Runs daily at: " + $At)

