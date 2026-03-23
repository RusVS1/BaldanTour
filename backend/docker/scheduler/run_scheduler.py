from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


@dataclass(frozen=True)
class Schedule:
    mode: str  # "daily" | "interval"
    tz: str
    daily_at: str  # "HH:MM"
    interval_minutes: int
    run_on_start: bool


def load_schedule() -> Schedule:
    mode = (os.getenv("SCHEDULE_MODE", "daily") or "daily").strip().lower()
    tz = (os.getenv("SCHEDULE_TZ", "Europe/Moscow") or "Europe/Moscow").strip()
    daily_at = (os.getenv("SCHEDULE_DAILY_AT", "03:30") or "03:30").strip()
    interval_minutes = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "1440") or "1440")
    run_on_start = (os.getenv("RUN_ON_START", "1") or "1").strip() in ("1", "true", "yes", "y", "on")
    if mode not in ("daily", "interval"):
        mode = "daily"
    if interval_minutes < 1:
        interval_minutes = 1
    return Schedule(mode=mode, tz=tz, daily_at=daily_at, interval_minutes=interval_minutes, run_on_start=run_on_start)


def now_in_tz(tz: str) -> datetime:
    if ZoneInfo is None:
        return datetime.now()
    try:
        return datetime.now(ZoneInfo(tz))
    except Exception:
        return datetime.now()


def compute_next_run(s: Schedule, after: datetime) -> datetime:
    if s.mode == "interval":
        return after + timedelta(minutes=s.interval_minutes)

    # daily
    try:
        hh, mm = s.daily_at.split(":", 1)
        hour = int(hh)
        minute = int(mm)
    except Exception:
        hour = 3
        minute = 30

    candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= after:
        candidate = candidate + timedelta(days=1)
    return candidate


def build_manage_command() -> list[str]:
    """
    All args are configurable via env vars so docker-compose can tune behavior.
    """
    cmd = [sys.executable, "manage.py", "parse_anextour"]

    def add(flag: str, env: str) -> None:
        v = (os.getenv(env, "") or "").strip()
        if v:
            cmd.extend([flag, v])

    def add_int(flag: str, env: str) -> None:
        v = (os.getenv(env, "") or "").strip()
        if v:
            cmd.extend([flag, str(int(v))])

    # Required: where inputs live inside container
    add("--root", "ANEXTOUR_PARSER_ROOT")
    add("--parser-path", "ANEXTOUR_PARSER_PATH")

    # Optional tuning
    if (os.getenv("ANEXTOUR_HEADLESS", "1") or "1").strip() in ("1", "true", "yes", "y", "on"):
        cmd.append("--headless")

    add_int("--timeout-ms", "ANEXTOUR_TIMEOUT_MS")
    add("--start-checkin-beg", "ANEXTOUR_START_CHECKIN_BEG")
    add("--max-checkin-beg", "ANEXTOUR_MAX_CHECKIN_BEG")
    add_int("--max-date-probe-days", "ANEXTOUR_MAX_DATE_PROBE_DAYS")
    add_int("--max-hotels", "ANEXTOUR_MAX_HOTELS")
    add_int("--max-towns", "ANEXTOUR_MAX_TOWNS")
    add("--townfrom", "ANEXTOUR_TOWNFROM")
    add("--base-link", "ANEXTOUR_BASE_LINK")
    add_int("--max-countries", "ANEXTOUR_MAX_COUNTRIES")
    add("--country-slug", "ANEXTOUR_COUNTRY_SLUG")
    add("--country-slugs", "ANEXTOUR_COUNTRY_SLUGS")
    add_int("--adult-max", "ANEXTOUR_ADULT_MAX")
    add_int("--child-max", "ANEXTOUR_CHILD_MAX")
    add("--stop-flag", "ANEXTOUR_STOP_FLAG")
    add_int("--commit-every", "ANEXTOUR_COMMIT_EVERY")

    return cmd


_stop = False


def _handle_sigterm(signum, frame) -> None:  # pragma: no cover
    global _stop
    _stop = True


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    schedule = load_schedule()
    print(f"[scheduler] schedule={schedule}", flush=True)

    # Simple lock to prevent overlapping runs if a parse takes longer than schedule interval.
    lock_path = Path(os.getenv("SCHEDULER_LOCK", "/tmp/anextour_scheduler.lock"))

    def can_run() -> bool:
        try:
            if lock_path.exists():
                # stale lock older than 12h -> ignore
                age = time.time() - lock_path.stat().st_mtime
                if age < 12 * 3600:
                    return False
                lock_path.unlink(missing_ok=True)
            lock_path.write_text(str(os.getpid()), encoding="utf-8")
            return True
        except Exception:
            return True

    def release_lock() -> None:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    next_run = now_in_tz(schedule.tz)
    if not schedule.run_on_start:
        next_run = compute_next_run(schedule, next_run)

    while not _stop:
        now = now_in_tz(schedule.tz)
        if now >= next_run:
            if not can_run():
                print("[scheduler] skip (another run is still in progress)", flush=True)
            else:
                try:
                    cmd = build_manage_command()
                    print("[scheduler] run: " + " ".join(cmd), flush=True)
                    p = subprocess.run(cmd, check=False)
                    print(f"[scheduler] exit_code={p.returncode}", flush=True)
                finally:
                    release_lock()

            next_run = compute_next_run(schedule, now_in_tz(schedule.tz))
            print(f"[scheduler] next_run={next_run.isoformat()}", flush=True)

        time.sleep(1.0)

    print("[scheduler] stopping", flush=True)


if __name__ == "__main__":
    main()

