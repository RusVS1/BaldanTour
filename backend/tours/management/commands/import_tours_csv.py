import csv
import re
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.utils.text import slugify

from tours.models import Amenity, Tour


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_date_yyyymmdd(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        y = int(value[0:4])
        m = int(value[4:6])
        d = int(value[6:8])
        return date(y, m, d)
    except Exception:
        return None


_PRICE_RE = re.compile(r"\d+")
_STARS_RE = re.compile(r"(?<!\d)([1-5])\s*(?:\\*|★)(?!\d)")


def _parse_price(value: str | None) -> tuple[int | None, str]:
    text = (value or "").strip()
    digits = _PRICE_RE.findall(text)
    if not digits:
        return None, text
    try:
        return int("".join(digits)), text
    except ValueError:
        return None, text


def _parse_hotel_category(*values: str | None) -> int | None:
    haystack = " ".join([v for v in values if v])
    if not haystack:
        return None
    m = _STARS_RE.search(haystack)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _split_amenities(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(";") if p.strip()]
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        slug = slugify(part)[:64] or slugify(part, allow_unicode=True)[:64]
        if not slug:
            continue
        if slug in seen:
            continue
        seen.add(slug)
        result.append(slug)
    return result


class Command(BaseCommand):
    help = "Import tours from CSV files in 'Распаршенные страны' folder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-dir",
            default=None,
            help="Path to folder with CSVs (default: ./Распаршенные страны).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after importing N rows total (for smoke tests).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Bulk insert batch size.",
        )

    def handle(self, *args, **options):
        if options["csv_dir"]:
            base_dir = Path(options["csv_dir"])
        else:
            cwd = Path.cwd()
            if (cwd / "parsed_country").exists():
                base_dir = cwd / "parsed_country"
            else:
                base_dir = cwd / "Распаршенные страны"
        limit = options["limit"]
        batch_size = options["batch_size"]

        if not base_dir.exists():
            raise SystemExit(f"CSV dir not found: {base_dir}")

        csv_files = sorted(base_dir.glob("anextour_available_tours_*.csv"))
        if not csv_files:
            raise SystemExit(f"No CSV files found in: {base_dir}")

        total = 0
        for csv_path in csv_files:
            self.stdout.write(f"Importing: {csv_path.name}")
            total = self._import_one(csv_path, batch_size=batch_size, total=total, limit=limit)
            if limit is not None and total >= limit:
                break

        self.stdout.write(self.style.SUCCESS(f"Done. Imported (or skipped duplicates) up to {total} rows."))

    def _import_one(self, csv_path: Path, *, batch_size: int, total: int, limit: int | None) -> int:
        to_create: list[Tour] = []
        pending_amenities: list[list[str]] = []

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                price_value, price_text = _parse_price(row.get("price"))

                tour = Tour(
                    country_slug=(row.get("country_slug") or "").strip(),
                    base_link=(row.get("base_link") or "").strip() or None,
                    request_url=(row.get("request_url") or "").strip(),
                    townfrom=(row.get("townfrom") or "").strip(),
                    adult=_parse_int(row.get("adult")) or 0,
                    child=_parse_int(row.get("child")) or 0,
                    night_min=_parse_int(row.get("night_min")),
                    night_max=_parse_int(row.get("night_max")),
                    checkin_beg=_parse_date_yyyymmdd(row.get("checkin_beg")),
                    checkin_end=_parse_date_yyyymmdd(row.get("checkin_end")),
                    description=(row.get("description") or "").strip(),
                    trip_dates=(row.get("trip_dates") or "").strip(),
                    nights=_parse_int(row.get("nights")),
                    room=(row.get("room") or "").strip(),
                    meal=(row.get("meal") or "").strip(),
                    placement=(row.get("placement") or "").strip(),
                    hotel_category=_parse_hotel_category(
                        row.get("raw_text"),
                        row.get("placement"),
                        row.get("room"),
                        row.get("description"),
                    ),
                    price_text=price_text,
                    price_value=price_value,
                    booking_link=(row.get("booking_link") or "").strip() or None,
                    raw_text=(row.get("raw_text") or "").strip(),
                )
                to_create.append(tour)
                pending_amenities.append(_split_amenities(row.get("functions")))

                if len(to_create) >= batch_size:
                    total = self._flush_batch(to_create, pending_amenities, total, limit)
                    to_create.clear()
                    pending_amenities.clear()
                    if limit is not None and total >= limit:
                        return total

        if to_create:
            total = self._flush_batch(to_create, pending_amenities, total, limit)
        return total

    def _flush_batch(
        self,
        tours: list[Tour],
        pending_amenities: list[list[str]],
        total: int,
        limit: int | None,
    ) -> int:
        request_urls = [t.request_url for t in tours if t.request_url]
        if not request_urls:
            return total

        # 1) ensure amenities exist
        amenity_slugs: set[str] = set()
        for slugs in pending_amenities:
            amenity_slugs.update(slugs)

        existing = set(
            Amenity.objects.filter(slug__in=amenity_slugs).values_list("slug", flat=True)
        )
        missing = amenity_slugs - existing
        if missing:
            Amenity.objects.bulk_create(
                [Amenity(slug=s, name=s.replace("-", " ")) for s in sorted(missing)],
                ignore_conflicts=True,
            )

        slug_to_id = dict(Amenity.objects.filter(slug__in=amenity_slugs).values_list("slug", "id"))

        # 2) insert tours (skip duplicates by request_url)
        with transaction.atomic():
            Tour.objects.bulk_create(tours, ignore_conflicts=True)

            created = {
                t.request_url: t.id
                for t in Tour.objects.filter(request_url__in=request_urls).only("id", "request_url")
            }

            # 2b) backfill hotel_category for existing rows (bulk_create ignore_conflicts won't update)
            url_to_category = {
                t.request_url: t.hotel_category
                for t in tours
                if t.request_url and t.hotel_category is not None
            }
            if url_to_category:
                whens = [
                    When(request_url=url, then=Value(category))
                    for url, category in url_to_category.items()
                ]
                Tour.objects.filter(
                    request_url__in=list(url_to_category.keys()),
                    hotel_category__isnull=True,
                ).update(
                    hotel_category=Case(
                        *whens,
                        output_field=IntegerField(),
                    )
                )

            through = Tour.amenities.through
            rels = []
            for tour, slugs in zip(tours, pending_amenities, strict=False):
                tour_id = created.get(tour.request_url)
                if not tour_id:
                    continue
                for slug in slugs:
                    amenity_id = slug_to_id.get(slug)
                    if amenity_id:
                        rels.append(through(tour_id=tour_id, amenity_id=amenity_id))

            if rels:
                through.objects.bulk_create(rels, ignore_conflicts=True)

        total += len(tours)
        if limit is not None:
            total = min(total, limit)
        return total
