from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Callable

from .models import Amenity, Favorite, Tour, TourImage, TourText


RU_MONTHS = {
    "янв": 1,
    "январ": 1,
    "фев": 2,
    "феврал": 2,
    "мар": 3,
    "март": 3,
    "апр": 4,
    "апрел": 4,
    "май": 5,
    "мая": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "август": 8,
    "сен": 9,
    "сент": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _to_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_yyyymmdd(value) -> date | None:
    value = str(value or "").strip()
    if not re.fullmatch(r"\d{8}", value):
        return None
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def _ru_month_number(value: str) -> int | None:
    normalized = (value or "").strip().lower().replace("ё", "е").rstrip(".")
    for prefix, number in RU_MONTHS.items():
        if normalized.startswith(prefix):
            return number
    return None


def _parse_trip_dates_range(value: str, reference_yyyymmdd: str | None = None) -> tuple[str, str, str]:
    text = re.sub(r"\s+", " ", value or "").strip()
    if not text:
        return "", "", ""
    reference = _parse_yyyymmdd(reference_yyyymmdd)
    reference_year = reference.year if reference else date.today().year

    numeric = re.search(
        r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s*[-–]\s*(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\b",
        text,
    )
    if numeric:
        d1, m1, y1, d2, m2, y2 = numeric.groups()
        start = date(int(y1 or reference_year), int(m1), int(d1))
        end = date(int(y2 or start.year), int(m2), int(d2))
        if end < start:
            end = date(end.year + 1, end.month, end.day)
        return f"{start:%d.%m.%Y} - {end:%d.%m.%Y}", start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    word_month = re.search(
        r"\b(\d{1,2})\s+([а-яё]+)\.?\s*[-–]\s*(\d{1,2})\s+([а-яё]+)\.?(?:\s+(\d{4}))?\b",
        text,
        flags=re.IGNORECASE,
    )
    if word_month:
        d1, m1_text, d2, m2_text, year_text = word_month.groups()
        m1 = _ru_month_number(m1_text)
        m2 = _ru_month_number(m2_text)
        if not m1 or not m2:
            return text, "", ""
        start = date(int(year_text or reference_year), m1, int(d1))
        end = date(start.year, m2, int(d2))
        if end < start:
            end = date(end.year + 1, end.month, end.day)
        return f"{start:%d.%m.%Y} - {end:%d.%m.%Y}", start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    return text, "", ""


def _is_placeholder_image_url(url: str) -> bool:
    s = (url or "").strip().lower()
    if not s:
        return True
    return (
        "logo-anex" in s
        or "/logo/" in s
        or s.endswith(".svg")
        or "user-files/elfinder/com/logo" in s
        or "/sliders/" in s
        or "/pop-up/" in s
    )


@dataclass
class TourRowImporter:
    batch_size: int = 1000
    log: Callable[[str], None] | None = None

    def truncate_all(self) -> None:
        Favorite.objects.all().delete()
        Tour.objects.all().delete()
        Amenity.objects.all().delete()
        TourImage.objects.all().delete()
        TourText.objects.all().delete()

    def purge_stale_tours(self) -> int:
        deleted, _ = Tour.objects.filter(checkin_beg__lt=date.today()).delete()
        return deleted

    def add_row(self, row: dict) -> None:
        request_url = (row.get("request_url") or "").strip()
        booking_link = (row.get("booking_link") or "").strip() or None
        if not request_url and not booking_link:
            return

        trip_dates, trip_checkin_beg, trip_checkin_end = _parse_trip_dates_range(
            (row.get("trip_dates") or "").strip(),
            row.get("checkin_beg"),
        )

        defaults = {
            "country_slug": (row.get("country_slug") or "").strip(),
            "country_ru": (row.get("country_ru") or "").strip(),
            "base_link": (row.get("base_link") or "").strip() or None,
            "request_url": request_url,
            "townfrom": (row.get("townfrom") or "").strip(),
            "townfrom_ru": (row.get("townfrom_ru") or "").strip(),
            "adult": _to_int(row.get("adult")) or 1,
            "child": _to_int(row.get("child")) or 0,
            "night_min": _to_int(row.get("night_min")),
            "night_max": _to_int(row.get("night_max")),
            "checkin_beg": _parse_yyyymmdd(trip_checkin_beg or row.get("checkin_beg")),
            "checkin_end": _parse_yyyymmdd(trip_checkin_end or row.get("checkin_end")),
            "hotel_name": (row.get("hotel_name") or "").strip(),
            "hotel_rating": (row.get("hotel_rating") or "").strip(),
            "trip_dates": trip_dates or (row.get("trip_dates") or "").strip(),
            "nights": _to_int(row.get("nights")),
            "room": (row.get("room") or "").strip(),
            "meal": (row.get("meal") or "").strip(),
            "placement": (row.get("placement") or "").strip(),
            "rest_type": (row.get("rest_type") or "").strip(),
            "hotel_type": (row.get("hotel_type") or "").strip(),
            "hotel_category": _to_int(row.get("hotel_category") or row.get("hotel_stars")),
            "price_text": (row.get("price_text") or row.get("price") or "").strip(),
            "price_value": _to_int(row.get("price_value")),
            "booking_link": booking_link,
            "raw_text": (row.get("raw_text") or "").strip(),
        }

        image_url = (row.get("main_image_url") or "").strip()
        if _is_placeholder_image_url(image_url):
            image_url = ""
        if image_url:
            defaults["main_image"], _ = TourImage.objects.get_or_create(
                sha256=_hash_text(image_url),
                defaults={"url": image_url},
            )

        for field_name, row_key in (
            ("common_description", "common_description"),
            ("target_description", "target_description"),
            ("answer_description", "answer_description"),
        ):
            text = (row.get(row_key) or "").strip()
            if text:
                defaults[field_name], _ = TourText.objects.get_or_create(
                    sha256=_hash_text(text),
                    defaults={"content": text},
                )

        lookup = {"booking_link": booking_link} if booking_link else {"request_url": request_url}
        tour, _ = Tour.objects.update_or_create(defaults=defaults, **lookup)

        amenities = (row.get("amenities") or row.get("functions") or "").split(",")
        for raw_slug in amenities:
            slug = raw_slug.strip().lower()
            if not slug:
                continue
            amenity, _ = Amenity.objects.get_or_create(slug=slug, defaults={"name": slug})
            tour.amenities.add(amenity)

    def finalize(self) -> None:
        return None
