#!/usr/bin/env bash
set -euo pipefail

python docker/wait_for_db.py
python manage.py migrate --noinput

exec python docker/scheduler/run_scheduler.py

