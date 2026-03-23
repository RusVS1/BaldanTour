import argparse
import hashlib
import os
import sys
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from tours.models import Amenity, Tour, TourImage, TourText

try:
    # Reuse the exact import/normalization logic already used for CSV imports.
    from tours.management.commands.import_tours_csv import (  # type: ignore
        _COUNTRY_SLUG_TO_RU,
        _TOWNFROM_SLUG_TO_RU,
        _parse_rest_type as _import_parse_rest_type,
        _split_amenities as _import_split_amenities,
        _to_ru_label,
    )
except Exception:  # pragma: no cover
    _COUNTRY_SLUG_TO_RU = {}
    _TOWNFROM_SLUG_TO_RU = {}
    _import_parse_rest_type = None
    _import_split_amenities = None
    _to_ru_label = None


def _sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _parse_date_yyyymmdd(value: str | None) -> date | None:
    v = (value or "").strip()
    if not v:
        return None
    try:
        y = int(v[0:4])
        m = int(v[4:6])
        d = int(v[6:8])
        return date(y, m, d)
    except Exception:
        return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _parse_price(value: str | None) -> tuple[int | None, str]:
    text = (value or "").strip()
    digits = []
    cur = []
    for ch in text:
        if ch.isdigit():
            cur.append(ch)
        else:
            if cur:
                digits.append("".join(cur))
                cur = []
    if cur:
        digits.append("".join(cur))
    if not digits:
        return None, text
    try:
        return int("".join(digits)), text
    except ValueError:
        return None, text


def _split_amenities(value: str | None) -> list[str]:
    """
    Parser emits icons/features as semicolon-separated (or may be empty).
    Keep it simple and stable: normalize + dedup.
    """
    if not value:
        return []
    parts = [p.strip() for p in value.split(";") if p.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        slug = p.lower()
        slug = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in slug)
        slug = "-".join([x for x in slug.split("-") if x])[:64]
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
    return out


def _extract_answer_description(target_desc: str) -> str:
    """
    Keep the logic close to what you already import into DB:
    - answer_description = first part of target_description (before "Инфраструктура" / rules)
    """
    t = (target_desc or "").strip()
    if not t:
        return ""
    # crude but effective
    idx = t.lower().find("инфраструктура")
    if idx != -1:
        t = t[:idx].strip()
    return t


class Command(BaseCommand):
    help = "Run anextour Playwright parser and write results directly into PostgreSQL via Django ORM (no CSV)."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--parser-path",
            default=os.getenv("ANEXTOUR_PARSER_PATH", r"/app/anextour_available_tours_example.py"),
        )
        parser.add_argument("--root", default=os.getenv("ANEXTOUR_PARSER_ROOT", r"/app/data/inputs"))
        parser.add_argument("--headless", action="store_true")
        parser.add_argument("--timeout-ms", type=int, default=30000)
        parser.add_argument("--start-checkin-beg", default="20260313")
        parser.add_argument("--max-checkin-beg", default="20260320")
        parser.add_argument("--max-date-probe-days", type=int, default=40)
        parser.add_argument("--max-hotels", type=int, default=1)
        parser.add_argument("--max-towns", type=int, default=0)
        parser.add_argument("--townfrom", default="")
        parser.add_argument("--base-link", default="")
        parser.add_argument("--max-countries", type=int, default=0)
        parser.add_argument("--country-slug", default="")
        parser.add_argument("--country-slugs", default="")
        parser.add_argument("--adult-max", type=int, default=10)
        parser.add_argument("--child-max", type=int, default=10)
        parser.add_argument("--stop-flag", default=r"D:\asoiu\проект\STOP_PARSING.flag")
        parser.add_argument("--commit-every", type=int, default=50, help="Commit every N parsed rows.")

    def handle(self, *args, **opts):
        parser_path = Path(opts["parser_path"])
        if not parser_path.exists():
            raise SystemExit(f"Parser not found: {parser_path}")

        # Import parser module by path (so we reuse the exact parsing logic you debugged).
        sys.path.insert(0, str(parser_path.parent))
        mod_name = parser_path.stem
        parser = __import__(mod_name)

        # Build a lightweight Namespace compatible with parser.run_core().
        ns = argparse.Namespace(
            root=opts["root"],
            headless=bool(opts["headless"]),
            timeout_ms=int(opts["timeout_ms"]),
            start_checkin_beg=opts["start_checkin_beg"],
            max_checkin_beg=opts["max_checkin_beg"],
            max_date_probe_days=int(opts["max_date_probe_days"]),
            max_hotels=int(opts["max_hotels"]),
            max_towns=int(opts["max_towns"]),
            townfrom=opts["townfrom"],
            base_link=opts["base_link"],
            max_countries=int(opts["max_countries"]),
            country_slug=opts["country_slug"],
            country_slugs=opts["country_slugs"],
            adult_max=int(opts["adult_max"]),
            child_max=int(opts["child_max"]),
        )

        stop_flag = Path(opts["stop_flag"])
        stop_flag.parent.mkdir(parents=True, exist_ok=True)

        commit_every = max(1, int(opts["commit_every"]))

        # Caches to reduce DB chatter.
        text_cache: dict[str, int] = {}
        image_cache: dict[str, int] = {}
        amenity_cache: dict[str, int] = {}

        def get_text_id(content: str) -> int | None:
            content = (content or "").strip()
            if not content:
                return None
            h = _sha256_text(content)
            if h in text_cache:
                return text_cache[h]
            obj, _ = TourText.objects.get_or_create(sha256=h, defaults={"content": content})
            text_cache[h] = obj.id
            return obj.id

        def get_image_id(url: str) -> int | None:
            url = (url or "").strip()
            if not url:
                return None
            h = _sha256_text(url)
            if h in image_cache:
                return image_cache[h]
            obj, _ = TourImage.objects.get_or_create(sha256=h, defaults={"url": url})
            image_cache[h] = obj.id
            return obj.id

        def get_amenity_ids(functions: str) -> list[int]:
            if _import_split_amenities is not None:
                slugs = _import_split_amenities(functions)
            else:
                slugs = _split_amenities(functions)
            ids: list[int] = []
            for slug in slugs:
                if slug in amenity_cache:
                    ids.append(amenity_cache[slug])
                    continue
                obj, _ = Amenity.objects.get_or_create(slug=slug, defaults={"name": slug})
                amenity_cache[slug] = obj.id
                ids.append(obj.id)
            return ids

        parsed_count = 0
        stopped = False

        def upsert_row(row: dict) -> None:
            nonlocal parsed_count
            parsed_count += 1

            common_desc = (row.get("common_description") or "").strip()
            target_desc = (row.get("target_description") or "").strip()
            answer_desc = _extract_answer_description(target_desc)

            common_id = get_text_id(common_desc)
            target_id = get_text_id(target_desc)
            answer_id = get_text_id(answer_desc)
            image_id = get_image_id(row.get("main_image_url") or "")

            price_value, price_text = _parse_price(row.get("price"))

            booking_link = (row.get("booking_link") or "").strip() or None
            request_url = (row.get("request_url") or "").strip()

            country_slug = (row.get("country_slug") or "").strip()
            townfrom = (row.get("townfrom") or "").strip()
            if _to_ru_label is not None:
                country_ru = _to_ru_label(country_slug, _COUNTRY_SLUG_TO_RU)
                townfrom_ru = _to_ru_label(townfrom, _TOWNFROM_SLUG_TO_RU)
            else:
                country_ru = ""
                townfrom_ru = ""

            if _import_parse_rest_type is not None:
                rest_type = _import_parse_rest_type(common_desc, target_desc)
            else:
                rest_type = ""

            defaults = dict(
                country_slug=country_slug,
                country_ru=country_ru,
                base_link=(row.get("base_link") or "").strip() or None,
                request_url=request_url,
                townfrom=townfrom,
                townfrom_ru=townfrom_ru,
                adult=int(row.get("adult") or 1),
                child=int(row.get("child") or 0),
                night_min=_parse_int(row.get("night_min")),
                night_max=_parse_int(row.get("night_max")),
                checkin_beg=_parse_date_yyyymmdd(row.get("checkin_beg")),
                checkin_end=_parse_date_yyyymmdd(row.get("checkin_end")),
                hotel_name=(row.get("hotel_name") or "").strip(),
                hotel_rating=(row.get("hotel_rating") or "").strip(),
                hotel_stars=_parse_int(row.get("hotel_stars")),
                hotel_type=(row.get("hotel_type") or "").strip(),
                rest_type=rest_type,
                trip_dates=(row.get("trip_dates") or "").strip(),
                nights=_parse_int(row.get("nights")),
                room=(row.get("room") or "").strip()[:255],
                meal=(row.get("meal") or "").strip()[:128],
                placement=(row.get("placement") or "").strip()[:255],
                price_text=price_text[:64],
                price_value=price_value,
                booking_link=booking_link,
                raw_text=(row.get("raw_text") or "").strip(),
                common_description_id=common_id,
                target_description_id=target_id,
                answer_description_id=answer_id,
                main_image_id=image_id,
                hotel_category=_parse_int(row.get("hotel_stars")),
            )

            # Upsert by booking_link when possible (unique). Otherwise fallback to request_url.
            if booking_link:
                tour, _created = Tour.objects.update_or_create(
                    booking_link=booking_link,
                    defaults=defaults,
                )
            else:
                tour = Tour.objects.filter(request_url=request_url).order_by("id").first()
                if tour is None:
                    tour = Tour.objects.create(**defaults)
                else:
                    for k, v in defaults.items():
                        setattr(tour, k, v)
                    tour.save(update_fields=list(defaults.keys()) + ["updated_at"])

            amenity_ids = get_amenity_ids(row.get("functions") or "")
            if amenity_ids:
                tour.amenities.set(amenity_ids)
            else:
                tour.amenities.clear()

        async def _run_async() -> None:
            nonlocal stopped
            # Code-only mode: countries/towns are embedded in the parser module.
            rows: list[dict[str, str]] = []
            towns = parser.select_towns(ns.townfrom, ns.max_towns)
            countries = parser.select_countries(ns.country_slug, ns.country_slugs, ns.max_countries)
            # Force discovery inside run_core by providing empty base_links per country.
            links_by_country = {c: [] for c in countries}
            city_names = set(getattr(parser, "DEFAULT_TOWNS", towns))

            self.stdout.write(f"[info] countries={len(countries)} towns={len(towns)}")

            buffer: list[dict] = []

            def emit_row(row_dict: dict) -> None:
                buffer.append(row_dict)
                if len(buffer) >= commit_every:
                    with transaction.atomic():
                        for r in buffer:
                            upsert_row(r)
                    buffer.clear()

            stopped = await parser.run_core(
                ns,
                rows=rows,
                city_names=city_names,
                links_by_country=links_by_country,
                countries=countries,
                towns=towns,
                stop_flag=stop_flag,
                emit_row=emit_row,
            )

            if buffer:
                with transaction.atomic():
                    for r in buffer:
                        upsert_row(r)
                buffer.clear()

        # Ensure Playwright async is driven properly
        import asyncio

        asyncio.run(_run_async())

        status = "stopped_by_flag" if stopped else "completed"
        self.stdout.write(self.style.SUCCESS(f"Done: {status}, rows_upserted={parsed_count}"))
