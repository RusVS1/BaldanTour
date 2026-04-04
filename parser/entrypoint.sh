#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os
import time

import psycopg

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
db = os.environ.get("POSTGRES_DB", "tour_aggregator")
user = os.environ.get("POSTGRES_USER", "tour_aggregator")
password = os.environ.get("POSTGRES_PASSWORD", "tour_aggregator")
timeout = int(os.environ.get("DB_WAIT_SECONDS", "60"))

deadline = time.time() + timeout
last_error = None
while time.time() < deadline:
    try:
        with psycopg.connect(host=host, port=port, dbname=db, user=user, password=password, connect_timeout=3):
            print("DB is ready.")
            raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(1)

raise SystemExit(f"DB is not ready after {timeout}s: {last_error}")
PY

exec python -u -m parser.main \
  --headless \
  --root /app \
  --country-workers "${PARSER_COUNTRY_WORKERS:-20}" \
  --db-batch-size "${PARSER_DB_BATCH_SIZE:-200}" \
  ${PARSER_EXTRA_ARGS:-}
