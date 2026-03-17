import csv
import hashlib
import math
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from apps.parsed_tours.models import ParsedAvailableTour, ParsedCountry


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def parse_yyyymmdd(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_int(value: str):
    value = (value or "").strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_decimal(value: str):
    value = (value or "").strip()
    if value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def build_source_hash(row: dict) -> str:
    parts = [
        row.get("country_slug", ""),
        row.get("request_url", ""),
        row.get("townfrom", ""),
        row.get("checkin_beg", ""),
        row.get("checkin_end", ""),
        row.get("nights", ""),
        row.get("room", ""),
        row.get("meal", ""),
        row.get("placement", ""),
        row.get("price", ""),
        row.get("booking_link", ""),
    ]
    payload = "|".join(str(p).strip() for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_embedding(text: str, dim: int = 64) -> list[float]:
    # Deterministic hashing embedding (no external models / API).
    # Suitable for basic similarity search later; can be re-embedded with a real model.
    vec = [0.0] * dim
    for token in TOKEN_RE.findall((text or "").lower()):
        h = hashlib.md5(token.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        sign = -1.0 if (h[4] & 1) else 1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class Command(BaseCommand):
    help = "Import parsed available tours from CSVs into DB (with deterministic embeddings)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            dest="dir",
            default=os.getenv("PARSED_COUNTRIES_DIR", "/data/parsed"),
            help="Directory with anextour_available_tours_*.csv",
        )
        parser.add_argument("--pattern", dest="pattern", default="anextour_available_tours_*.csv")
        parser.add_argument("--chunk-size", dest="chunk_size", type=int, default=1000)
        parser.add_argument("--no-embeddings", dest="no_embeddings", action="store_true")
        parser.add_argument("--limit", dest="limit", type=int, default=0)
        parser.add_argument(
            "--reset",
            dest="reset",
            action="store_true",
            help="TRUNCATE parsed tours/countries tables before import (keeps auth/users/history).",
        )

    def handle(self, *args, **options):
        base_dir = Path(options["dir"]).expanduser().resolve()
        pattern = options["pattern"]
        chunk_size = int(options["chunk_size"])
        no_embeddings = bool(options["no_embeddings"])
        limit = int(options["limit"]) if int(options["limit"]) > 0 else None
        reset = bool(options["reset"])

        if not base_dir.exists():
            raise SystemExit(f"Directory not found: {base_dir}")

        files = sorted(base_dir.glob(pattern))
        if not files:
            self.stdout.write(self.style.WARNING(f"No files matched {pattern} in {base_dir}"))
            return

        embedding_version = "" if no_embeddings else "hash-v1-64"

        countries_cache: dict[str, ParsedCountry] = {}

        if reset:
            # Use TRUNCATE for speed and to reset IDs. Does not touch auth tables.
            self.stdout.write(self.style.WARNING("[reset] TRUNCATE parsed_tours tables"))
            with connection.cursor() as cur, transaction.atomic():
                cur.execute(
                    "TRUNCATE TABLE parsed_tours_parsedavailabletour, parsed_tours_parsedcountry RESTART IDENTITY CASCADE;"
                )

        for csv_path in files:
            self.stdout.write(f"[import] {csv_path.name}")
            created_countries = 0
            rows_seen = 0
            count_before = ParsedAvailableTour.objects.count()

            # Use utf-8-sig to strip BOM if present.
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                buffer: list[ParsedAvailableTour] = []

                for row in reader:
                    rows_seen += 1
                    if limit is not None and rows_seen > limit:
                        break

                    country_slug = (row.get("country_slug") or "").strip()
                    if not country_slug:
                        continue

                    source_hash = build_source_hash(row)
                    country = countries_cache.get(country_slug)
                    if country is None:
                        country, created = ParsedCountry.objects.get_or_create(slug=country_slug)
                        countries_cache[country_slug] = country
                        if created:
                            created_countries += 1

                    text_for_embedding = " ".join(
                        [
                            row.get("description", "") or "",
                            row.get("raw_text", "") or "",
                            row.get("booking_link", "") or "",
                        ]
                    ).strip()

                    embedding = None if no_embeddings else hash_embedding(text_for_embedding, dim=64)

                    buffer.append(
                        ParsedAvailableTour(
                            country=country,
                            source_hash=source_hash,
                            base_link=(row.get("base_link") or "").strip(),
                            request_url=(row.get("request_url") or "").strip(),
                            townfrom=(row.get("townfrom") or "").strip(),
                            adult=parse_int(row.get("adult", "")),
                            child=parse_int(row.get("child", "")),
                            night_min=parse_int(row.get("night_min", "")),
                            night_max=parse_int(row.get("night_max", "")),
                            checkin_beg=parse_yyyymmdd(row.get("checkin_beg", "")),
                            checkin_end=parse_yyyymmdd(row.get("checkin_end", "")),
                            description=(row.get("description") or "").strip(),
                            functions=(row.get("functions") or "").strip(),
                            trip_dates=(row.get("trip_dates") or "").strip(),
                            nights=(row.get("nights") or "").strip(),
                            room=(row.get("room") or "").strip(),
                            meal=(row.get("meal") or "").strip(),
                            placement=(row.get("placement") or "").strip(),
                            price=parse_decimal(row.get("price", "")),
                            booking_link=(row.get("booking_link") or "").strip(),
                            raw_text=(row.get("raw_text") or "").strip(),
                            embedding=embedding,
                            embedding_version=embedding_version,
                        )
                    )

                    if len(buffer) >= chunk_size:
                        self._flush(buffer)
                        buffer.clear()

                if buffer:
                    self._flush(buffer)

            count_after = ParsedAvailableTour.objects.count()
            created_tours = count_after - count_before

            self.stdout.write(
                self.style.SUCCESS(
                    f"[done] rows_seen={rows_seen} countries_created={created_countries} tours_created={created_tours}"
                )
            )

    def _flush(self, buffer: list[ParsedAvailableTour]) -> int:
        with transaction.atomic():
            ParsedAvailableTour.objects.bulk_create(buffer, batch_size=len(buffer), ignore_conflicts=True)
        return 0
