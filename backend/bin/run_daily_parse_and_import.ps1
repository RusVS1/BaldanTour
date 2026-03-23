# Daily pipeline:
# 1) Run Playwright parser (host) -> write CSV/JSON into /app/parsed_country/<date>/...
# 2) Import that CSV into PostgreSQL via Django management command inside the backend container.
#
# Requirements (once):
# - Install python deps for the parser environment (playwright, etc.)
# - Install Playwright browser: `python -m playwright install chromium`
# - Start Docker Desktop (for Postgres + backend import step)

[CmdletBinding()]
param(
  [string]$ParserScript = "D:\asoiu\anextour_available_tours_example.py",
  [string]$ProjectRoot = "D:\asoiu\проект",
  [string]$InputsRoot = "D:\asoiu\проект\data\inputs",
  [string]$StopFlag = "D:\asoiu\проект\STOP_PARSING.flag",
  [string]$TownFrom = "moskva",
  [string]$CountrySlug = "",
  [string]$CountrySlugs = "",
  [int]$AdultMax = 10,
  [int]$ChildMax = 10,
  [switch]$Headless = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-Python {
  param([string]$ProjectRoot)
  $venvPy = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) { return $venvPy }

  $fallback = "C:\Users\bairb\AppData\Local\Programs\Python\Python312\python.exe"
  if (Test-Path $fallback) { return $fallback }

  throw "Python not found. Expected $venvPy or $fallback"
}

function Ensure-Inputs {
  param([string]$InputsRoot, [string]$FallbackRoot)

  New-Item -ItemType Directory -Force -Path $InputsRoot | Out-Null

  $need = @(
    "anextour_tours_dynamic.csv",
    "anextour_tours_dynamics.csv",
    "anextour_city_names.txt"
  )

  foreach ($name in $need) {
    $dst = Join-Path $InputsRoot $name
    if (Test-Path $dst) { continue }

    $src = Join-Path $FallbackRoot $name
    if (Test-Path $src) {
      Copy-Item -Force $src $dst
      continue
    }
  }
}

if (!(Test-Path $ParserScript)) { throw "Parser script not found: $ParserScript" }
if (!(Test-Path $ProjectRoot)) { throw "Project root not found: $ProjectRoot" }

# Don’t start a scheduled run in a pre-stopped state.
if (Test-Path $StopFlag) { Remove-Item -Force $StopFlag }

Ensure-Inputs -InputsRoot $InputsRoot -FallbackRoot "D:\asoiu"

$python = Resolve-Python -ProjectRoot $ProjectRoot

$today = Get-Date -Format "yyyy-MM-dd"
$outDir = Join-Path $ProjectRoot ("parsed_country\" + $today)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$outCsv = Join-Path $outDir ("anextour_available_tours_" + $today + ".csv")
$outJson = Join-Path $outDir ("anextour_available_tours_" + $today + ".json")
$logDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir ("daily_" + $today + ".log")

Start-Transcript -Path $logPath -Append | Out-Null
try {
  Write-Host ("[1/2] Parser -> " + $outCsv)

  $args = @(
    $ParserScript,
    "--root", $InputsRoot,
    "--out-csv", $outCsv,
    "--out-json", $outJson,
    "--flush-interval-sec", "120",
    "--stop-flag", $StopFlag,
    "--adult-max", "$AdultMax",
    "--child-max", "$ChildMax",
    "--townfrom", $TownFrom,
    "--reset-output"
  )
  if ($Headless) { $args += "--headless" }
  if ($CountrySlug) { $args += @("--country-slug", $CountrySlug) }
  if ($CountrySlugs) { $args += @("--country-slugs", $CountrySlugs) }

  & $python @args
  if ($LASTEXITCODE -ne 0) { throw "Parser failed with exit code $LASTEXITCODE" }

  Write-Host "[2/2] Import into PostgreSQL (docker compose backend)"

  Push-Location $ProjectRoot
  try {
    docker compose -p touragg up -d db backend | Out-Null
    # Import only today's folder. It’s mounted into the container as /app/parsed_country/<date>
    docker compose -p touragg exec -T backend python manage.py import_tours_csv --csv-dir ("/app/parsed_country/" + $today)
  } finally {
    Pop-Location
  }

  Write-Host "OK"
} finally {
  Stop-Transcript | Out-Null
}

