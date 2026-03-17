#!/bin/sh
set -eu

echo "[entrypoint] migrate"
python manage.py migrate

echo "[entrypoint] ensure test user"
python manage.py ensure_test_user

echo "[entrypoint] preload parsed tours if empty"
python - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.parsed_tours.models import ParsedAvailableTour

count = ParsedAvailableTour.objects.count()
print(f"[entrypoint] parsed tours in db: {count}")
reset = os.getenv("RESET_PARSED_TOURS", "false").lower() == "true"
if reset or count == 0:
    import subprocess
    parsed_dir = os.getenv("PARSED_COUNTRIES_DIR", "/data/parsed")
    sample_fixture = os.getenv("SAMPLE_FIXTURE_PATH", "/app/seed/sample_parsed_tours.json")

    # Prefer importing from CSVs if mount exists, otherwise fall back to a small fixture shipped with the repo.
    if os.path.isdir(parsed_dir) and any(n.endswith(".csv") for n in os.listdir(parsed_dir)):
        print(f"[entrypoint] importing from: {parsed_dir}")
        cmd = ["python", "manage.py", "import_parsed_countries", "--dir", parsed_dir, "--chunk-size", "2000"]
        if reset:
            cmd.append("--reset")
        subprocess.check_call(cmd)
        subprocess.check_call(["python", "manage.py", "fill_missing_descriptions"])
    elif os.path.isfile(sample_fixture):
        print(f"[entrypoint] loading sample fixture: {sample_fixture}")
        subprocess.check_call(["python", "manage.py", "loaddata", sample_fixture])
    else:
        print("[entrypoint] no CSV mount and no sample fixture; leaving parsed tours empty")
PY

if [ "${RUN_GPU_EMBEDDINGS:-false}" = "true" ]; then
  echo "[entrypoint] GPU embeddings enabled"
  python manage.py embed_parsed_tours_gpu --batch-size 256 --only-missing
else
  echo "[entrypoint] GPU embeddings disabled (set RUN_GPU_EMBEDDINGS=true to enable)"
fi

if [ "${EXPORT_EMBEDDINGS_CACHE:-false}" = "true" ]; then
  echo "[entrypoint] export embeddings cache enabled"
  python manage.py export_embeddings_cache
else
  echo "[entrypoint] export embeddings cache disabled (set EXPORT_EMBEDDINGS_CACHE=true to enable)"
fi

echo "[entrypoint] start gunicorn"
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --timeout 180
