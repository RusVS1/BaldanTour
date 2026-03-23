[CmdletBinding()]
param(
  [string]$StopFlag = "D:\asoiu\проект\STOP_PARSING.flag"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

New-Item -ItemType File -Force -Path $StopFlag | Out-Null
Write-Host ("Created stop flag: " + $StopFlag)

