import os
import time

import psycopg


def main() -> None:
    dbname = os.getenv("POSTGRES_DB", "tour_aggregator")
    user = os.getenv("POSTGRES_USER", "tour_aggregator")
    password = os.getenv("POSTGRES_PASSWORD", "tour_aggregator")
    host = os.getenv("POSTGRES_HOST", "db")
    port = int(os.getenv("POSTGRES_PORT", "5432"))

    deadline = time.time() + int(os.getenv("DB_WAIT_SECONDS", "60"))
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with psycopg.connect(
                dbname=dbname, user=user, password=password, host=host, port=port
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
            print("DB is ready.")
            return
        except Exception as e:  # noqa: BLE001
            last_error = e
            time.sleep(1)

    raise SystemExit(f"DB not ready after timeout. Last error: {last_error!r}")


if __name__ == "__main__":
    main()

