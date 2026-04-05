#!/usr/bin/env bash
set -euo pipefail

DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-tour_aggregator}"
POSTGRES_USER="${POSTGRES_USER:-tour_aggregator}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-tour_aggregator}"

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
    except Exception as e:
        last_error = e
        time.sleep(1)

raise SystemExit(f"DB is not ready after {timeout}s: {last_error}")
PY

python manage.py migrate --noinput

(python - <<'PY'
import os

provider = (os.environ.get("EMBEDDINGS_PROVIDER") or "").strip().lower()
should_warm = (os.environ.get("PRELOAD_EMBEDDING_MODEL") or "1").strip().lower() not in {"0", "false", "no"}

if not should_warm:
    print("Embedding preload skipped by PRELOAD_EMBEDDING_MODEL.")
    raise SystemExit(0)

if provider == "dummy":
    print("Embedding preload skipped for dummy provider.")
    raise SystemExit(0)

try:
    from tours.embeddings import get_embedder

    embedder = get_embedder()
    if embedder.provider in {"st", "sentence_transformers", "sentence-transformers"}:
        embedder.embed_texts(["query: warmup"])
        print(f"Embedding model preloaded: provider={embedder.provider} dim={embedder.dim}")
    else:
        print(f"Embedding preload skipped for provider={embedder.provider}")
except Exception as exc:
    print(f"WARNING: embedding preload failed: {exc}")
PY
) &

exec python manage.py runserver 0.0.0.0:8000
