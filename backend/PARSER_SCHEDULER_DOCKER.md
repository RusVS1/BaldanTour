# Docker Scheduler (In-Container, Configurable)

This project includes a `scheduler` service that runs the AnexTour Playwright parser **inside a Docker container** on a schedule and writes results directly into PostgreSQL (via Django ORM).

## Start

```powershell
Set-Location "D:\asoiu\проект"
docker compose -p touragg up -d db scheduler
```

View logs:

```powershell
docker compose -p touragg logs -f scheduler
```

## Schedule Settings (Env Vars)

These are read by the scheduler container (`docker/scheduler/run_scheduler.py`).

Scheduling:
- `SCHEDULE_MODE` = `daily` | `interval` (default: `daily`)
- `SCHEDULE_TZ` (default: `Europe/Moscow`)
- `SCHEDULE_DAILY_AT` = `HH:MM` (default: `03:30`)
- `SCHEDULE_INTERVAL_MINUTES` (default: `1440`)
- `RUN_ON_START` = `1` | `0` (default: `1`)

Parser settings:
- `ANEXTOUR_PARSER_ROOT` (default: `/app/data/inputs`)
- `ANEXTOUR_PARSER_PATH` (default: `/app/anextour_available_tours_example.py`)
- `ANEXTOUR_HEADLESS` (default: `1`)
- `ANEXTOUR_TOWNFROM` (default: `moskva`)
- `ANEXTOUR_COUNTRY_SLUG` (default: empty)
- `ANEXTOUR_COUNTRY_SLUGS` (default: empty, e.g. `spain,belarus,china`)
- `ANEXTOUR_ADULT_MAX` (default: `10`)
- `ANEXTOUR_CHILD_MAX` (default: `10`)
- `ANEXTOUR_STOP_FLAG` (default: `/app/STOP_PARSING.flag`)
- `ANEXTOUR_COMMIT_EVERY` (default: `50`)

You can set them in `.env` next to `docker-compose.yml`, or pass via PowerShell:

```powershell
$env:SCHEDULE_MODE="interval"
$env:SCHEDULE_INTERVAL_MINUTES="60"
$env:ANEXTOUR_COUNTRY_SLUGS="spain,belarus"
docker compose -p touragg up -d scheduler
```

## Safe Stop

Create stop flag (mounted into the container as `/app/STOP_PARSING.flag`):

```powershell
Set-Content -Path "D:\asoiu\проект\STOP_PARSING.flag" -Value "" -Encoding ascii
```

The running parse will stop on the next stop-flag check.

