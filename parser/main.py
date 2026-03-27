#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import calendar
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from asgiref.sync import sync_to_async
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright


NIGHT_RANGES = [(1, 8), (9, 16), (17, 24), (25, 28)]


def _default_checkin_window() -> tuple[str, str]:
    start_date = date.today() + timedelta(days=4)
    month_index = start_date.month - 1 + 7
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    end_date = date(year, month, day)
    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")


DEFAULT_CHECKIN_BEG, DEFAULT_MAX_CHECKIN_BEG = _default_checkin_window()

# Defaults embedded in code (so container runs do not depend on external CSV/text files).
DEFAULT_TOWNS = [
    "moskva",
    "sankt-peterburg",
    "kaliningrad",
    "barnaul",
    "chelyabinsk",
    "ekaterinburg",
    "kazan",
    "krasnodar",
    "n-novgorod",
    "novosibirsk",
    "omsk",
    "perm",
    "rostov-na-donu",
    "samara",
    "tyumen",
    "vladivostok",
    "volgograd",
]

DEFAULT_COUNTRY_SLUGS = [
    "abkhazia",
    "andorra",
    "argentina",
    "armenia",
    "aruba",
    "austria",
    "azerbaijan",
    "bahrain",
    "belarus",
    "belgium",
    "brazil",
    "bulgaria",
    "cambodia",
    "cape-verde",
    "chile",
    "china",
    "china-hong-kong-sar",
    "china-macau-sar",
    "costa-rica",
    "croatia",
    "cuba",
    "cyprus",
    "czech-republic",
    "dominican-republic",
    "egypt",
    "fiji",
    "france",
    "georgia",
    "germany",
    "greece",
    "hungary",
    "india",
    "indonesia",
    "israel",
    "italy",
    "jamaica",
    "japan",
    "jordan",
    "kazakhstan",
    "kenya",
    "kyrgyzstan",
    "lebanon",
    "madagascar",
    "malaysia",
    "maldives",
    "malta",
    "mauritius",
    "mexico",
    "mongolia",
    "montenegro",
    "morocco",
    "namibia",
    "nepal",
    "netherlands",
    "oman",
    "panama",
    "peru",
    "philippines",
    "portugal",
    "qatar",
    "russia",
    "saudi-arabia",
    "serbia",
    "seychelles",
    "singapore",
    "slovenia",
    "south-korea",
    "spain",
    "sri-lanka",
    "switzerland",
    "tanzania",
    "thailand",
    "tunisia",
    "turkey",
    "turkmenistan",
    "uae",
    "uruguay",
    "uzbekistan",
    "vietnam",
]

# Increase CSV field size limit for large "details" cells.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(10_000_000)
DEFAULT_PARAMS = {
    "ADULT": "2",
    "CHILD": "0",
    "COSTMAX": "",
    "COSTMIN": "",
    "CURRENCY": "1",
    "PARTITION_PRICE": "",
    "PRICE_PAGE": "1",
    "RECONPAGE": "40",
    "REGULAR": "True",
    "SORT_TYPE": "0",
    "STATEINC": "3",
    "THE_BEST_AT_TOP": "True",
    "TOWNFROM": "moskva",
    "CHARTER": "True",
    "FILTER": "1",
    "FREIGHT": "1",
    "FIELD_WITHOUT_FLIGHT": "0",
    "NIGHTMAX": "2",
    "NIGHTMIN": "2",
    "CHECKIN_BEG": DEFAULT_CHECKIN_BEG,
    "CHECKIN_END": DEFAULT_MAX_CHECKIN_BEG,
}


@dataclass
class ParsedTour:
    country_slug: str
    base_link: str
    request_url: str
    townfrom: str
    adult: int
    child: int
    night_min: int
    night_max: int
    checkin_beg: str
    checkin_end: str
    hotel_name: str
    hotel_rating: str
    hotel_stars: str
    hotel_type: str
    main_image_url: str
    common_description: str
    target_description: str
    functions: str
    trip_dates: str
    nights: str
    room: str
    meal: str
    placement: str
    price: str
    booking_link: str
    raw_text: str


def setup_django() -> None:
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


def build_db_emitter(batch_size: int):
    setup_django()
    from django.db import transaction
    from django.db.models import Case, IntegerField, Value, When
    from django.utils.text import slugify

    from tours.embeddings import get_embedder
    from tours.importers import COUNTRY_SLUG_TO_RU, TOWNFROM_SLUG_TO_RU
    from tours.models import Amenity, Favorite, Tour, TourImage, TourText

    def parse_int_db(value: str | int | None) -> int | None:
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def parse_date_yyyymmdd_db(value: str | None) -> date | None:
        value = (value or "").strip()
        if not value:
            return None
        try:
            year = int(value[0:4])
            month = int(value[4:6])
            day = int(value[6:8])
            return date(year, month, day)
        except Exception:
            return None

    def parse_price_db(value: str | None) -> tuple[int | None, str]:
        text = (value or "").strip()
        digits = re.findall(r"\d+", text)
        if not digits:
            return None, text
        try:
            return int("".join(digits)), text
        except ValueError:
            return None, text

    def split_amenities_db(value: str | None) -> list[str]:
        if not value:
            return []
        parts = [p.strip() for p in value.split(";") if p.strip()]
        seen: set[str] = set()
        result: list[str] = []
        for part in parts:
            slug = slugify(part)[:64] or slugify(part, allow_unicode=True)[:64]
            if not slug or slug in seen:
                continue
            seen.add(slug)
            result.append(slug)
        return result

    def parse_rest_type_db(*values: str | None) -> str:
        text = " ".join([v for v in values if v]).lower()
        if not text:
            return ""
        if "пляж" in text or "море" in text:
            return "пляжный"
        if "город" in text or "экскурс" in text:
            return "городской"
        return ""

    def parse_hotel_type_db(*values: str | None) -> str:
        text = " ".join([v for v in values if v]).lower()
        if not text:
            return ""
        if "для взрослых" in text or "взросл" in text or "adults only" in text or "adult only" in text:
            return "Для взрослых"
        if "для детей" in text or "детск" in text or "с детьми" in text or "дет" in text:
            return "Для детей"
        return ""

    def normalize_hotel_type_db(value: str | None) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        lower = value.lower()
        if "взросл" in lower or "adults only" in lower or "adult only" in lower:
            return "Для взрослых"
        if "дет" in lower or "с детьми" in lower:
            return "Для детей"
        return value

    def sha256_text_db(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    infra_re = re.compile(r"\bинфраструктура\b", flags=re.IGNORECASE)
    rules_re = re.compile(r"правила\s+размещения\s+в\s+отелях", flags=re.IGNORECASE)

    def extract_answer_description_db(target_desc: str) -> str:
        target_desc = (target_desc or "").strip()
        if not target_desc:
            return ""
        match = infra_re.search(target_desc)
        extracted = target_desc if not match else target_desc[: match.start()].strip()
        return rules_re.sub("", extracted).strip()

    def to_ru_label_db(value: str | None, mapping: dict[str, str]) -> str:
        text = (value or "").strip()
        if not text:
            return ""
        if re.search(r"[А-Яа-яЁё]", text):
            return text
        return mapping.get(text, text)

    class ParserDBWriter:
        def __init__(self, *, batch_size: int):
            self.batch_size = batch_size
            self.total_flushed = 0
            self.to_create: list[Tour] = []
            self.pending_amenities: list[list[str]] = []
            self.pending_text_hashes: list[tuple[str | None, str | None, str | None]] = []
            self.text_by_hash: dict[str, str] = {}
            self.pending_image_hashes: list[str | None] = []
            self.image_by_hash: dict[str, str] = {}
            self.pending_embed_texts: list[str] = []

        def add_row(self, row: dict[str, Any]) -> None:
            price_value, price_text = parse_price_db(row.get("price"))
            common_desc = str(row.get("common_description") or "").strip()
            target_desc = str(row.get("target_description") or "").strip()
            answer_desc = extract_answer_description_db(target_desc)

            common_hash = sha256_text_db(common_desc) if common_desc else None
            target_hash = sha256_text_db(target_desc) if target_desc else None
            answer_hash = sha256_text_db(answer_desc) if answer_desc else None
            for hash_value, content in (
                (common_hash, common_desc),
                (target_hash, target_desc),
                (answer_hash, answer_desc),
            ):
                if hash_value and hash_value not in self.text_by_hash:
                    self.text_by_hash[hash_value] = content

            country_slug = str(row.get("country_slug") or "").strip()
            townfrom = str(row.get("townfrom") or "").strip()
            image_url = str(row.get("main_image_url") or "").strip() or None
            image_hash = sha256_text_db(image_url) if image_url else None
            if image_hash and image_hash not in self.image_by_hash:
                self.image_by_hash[image_hash] = image_url or ""

            direct_hotel_type = normalize_hotel_type_db(str(row.get("hotel_type") or ""))
            hotel_category = parse_int_db(row.get("hotel_stars"))

            embed_text = " ".join(
                [
                    str(row.get("hotel_name") or "").strip(),
                    str(row.get("meal") or "").strip(),
                    str(row.get("placement") or "").strip(),
                    str(row.get("room") or "").strip(),
                    common_desc,
                    target_desc,
                    answer_desc,
                    str(row.get("raw_text") or "").strip(),
                ]
            ).strip()

            tour = Tour(
                country_slug=country_slug,
                country_ru=to_ru_label_db(country_slug, COUNTRY_SLUG_TO_RU),
                base_link=str(row.get("base_link") or "").strip() or None,
                request_url=str(row.get("request_url") or "").strip(),
                townfrom=townfrom,
                townfrom_ru=to_ru_label_db(townfrom, TOWNFROM_SLUG_TO_RU),
                adult=parse_int_db(row.get("adult")) or 0,
                child=parse_int_db(row.get("child")) or 0,
                night_min=parse_int_db(row.get("night_min")),
                night_max=parse_int_db(row.get("night_max")),
                checkin_beg=parse_date_yyyymmdd_db(str(row.get("checkin_beg") or "")),
                checkin_end=parse_date_yyyymmdd_db(str(row.get("checkin_end") or "")),
                hotel_name=str(row.get("hotel_name") or "").strip(),
                hotel_rating=str(row.get("hotel_rating") or "").strip(),
                trip_dates=str(row.get("trip_dates") or "").strip(),
                nights=parse_int_db(row.get("nights")),
                room=str(row.get("room") or "").strip(),
                meal=str(row.get("meal") or "").strip(),
                placement=str(row.get("placement") or "").strip(),
                rest_type=parse_rest_type_db(common_desc, target_desc, str(row.get("raw_text") or "")),
                hotel_type=direct_hotel_type or parse_hotel_type_db(target_desc, common_desc, str(row.get("raw_text") or "")),
                hotel_category=hotel_category,
                price_text=price_text,
                price_value=price_value,
                booking_link=str(row.get("booking_link") or "").strip() or None,
                raw_text=str(row.get("raw_text") or "").strip(),
            )

            self.to_create.append(tour)
            self.pending_amenities.append(split_amenities_db(str(row.get("functions") or "")))
            self.pending_text_hashes.append((common_hash, target_hash, answer_hash))
            self.pending_image_hashes.append(image_hash)
            self.pending_embed_texts.append(embed_text)

            if len(self.to_create) >= self.batch_size:
                self.flush()

        def flush(self) -> int:
            tours = self.to_create
            if not tours:
                return 0

            request_urls = [tour.request_url for tour in tours if tour.request_url]
            if not request_urls:
                self._reset_batch()
                return 0

            amenity_slugs: set[str] = set()
            for slugs in self.pending_amenities:
                amenity_slugs.update(slugs)

            if amenity_slugs:
                existing = set(Amenity.objects.filter(slug__in=amenity_slugs).values_list("slug", flat=True))
                missing = amenity_slugs - existing
                if missing:
                    Amenity.objects.bulk_create(
                        [Amenity(slug=slug, name=slug.replace("-", " ")) for slug in sorted(missing)],
                        ignore_conflicts=True,
                    )
                slug_to_id = dict(Amenity.objects.filter(slug__in=amenity_slugs).values_list("slug", "id"))
            else:
                slug_to_id = {}

            text_hashes = {hash_value for pair in self.pending_text_hashes for hash_value in pair if hash_value}
            if text_hashes:
                existing_text = dict(TourText.objects.filter(sha256__in=list(text_hashes)).values_list("sha256", "id"))
                missing_text = text_hashes - set(existing_text.keys())
                if missing_text:
                    TourText.objects.bulk_create(
                        [TourText(sha256=hash_value, content=self.text_by_hash.get(hash_value, "")) for hash_value in sorted(missing_text)],
                        ignore_conflicts=True,
                    )
                    existing_text = dict(TourText.objects.filter(sha256__in=list(text_hashes)).values_list("sha256", "id"))

                for tour, (common_hash, target_hash, answer_hash) in zip(tours, self.pending_text_hashes, strict=False):
                    tour.common_description_id = existing_text.get(common_hash) if common_hash else None
                    tour.target_description_id = existing_text.get(target_hash) if target_hash else None
                    tour.answer_description_id = existing_text.get(answer_hash) if answer_hash else None

            image_hashes = {hash_value for hash_value in self.pending_image_hashes if hash_value}
            if image_hashes:
                existing_images = dict(TourImage.objects.filter(sha256__in=list(image_hashes)).values_list("sha256", "id"))
                missing_images = image_hashes - set(existing_images.keys())
                if missing_images:
                    TourImage.objects.bulk_create(
                        [TourImage(sha256=hash_value, url=self.image_by_hash.get(hash_value, "")) for hash_value in sorted(missing_images)],
                        ignore_conflicts=True,
                    )
                    existing_images = dict(TourImage.objects.filter(sha256__in=list(image_hashes)).values_list("sha256", "id"))

                for tour, image_hash in zip(tours, self.pending_image_hashes, strict=False):
                    tour.main_image_id = existing_images.get(image_hash) if image_hash else None

            if self.pending_embed_texts:
                embedder = get_embedder()
                try:
                    vectors = embedder.embed_texts(self.pending_embed_texts)
                    for tour, vector in zip(tours, vectors, strict=False):
                        tour.embedding = vector
                except Exception as exc:
                    print(f"[db] WARNING: embeddings skipped for batch: {exc}", flush=True)

            with transaction.atomic():
                Tour.objects.bulk_create(tours, ignore_conflicts=True)

                created = {
                    tour.request_url: tour.id
                    for tour in Tour.objects.filter(request_url__in=request_urls).only("id", "request_url")
                }

                url_to_category = {
                    tour.request_url: tour.hotel_category
                    for tour in tours
                    if tour.request_url and tour.hotel_category is not None
                }
                if url_to_category:
                    whens = [When(request_url=url, then=Value(category)) for url, category in url_to_category.items()]
                    Tour.objects.filter(
                        request_url__in=list(url_to_category.keys()),
                        hotel_category__isnull=True,
                    ).update(hotel_category=Case(*whens, output_field=IntegerField()))

                through = Tour.amenities.through
                relations = []
                for tour, slugs in zip(tours, self.pending_amenities, strict=False):
                    tour_id = created.get(tour.request_url)
                    if not tour_id:
                        continue
                    for slug in slugs:
                        amenity_id = slug_to_id.get(slug)
                        if amenity_id:
                            relations.append(through(tour_id=tour_id, amenity_id=amenity_id))

                if relations:
                    through.objects.bulk_create(relations, ignore_conflicts=True)

            flushed = len(tours)
            self.total_flushed += flushed
            self._reset_batch()
            return flushed

        def finalize(self) -> int:
            self.flush()
            return self.total_flushed

        def truncate_all(self) -> None:
            with transaction.atomic():
                Favorite.objects.all().delete()
                Tour.amenities.through.objects.all().delete()
                Amenity.objects.all().delete()
                Tour.objects.all().delete()
                TourText.objects.all().delete()
                TourImage.objects.all().delete()

        def _reset_batch(self) -> None:
            self.to_create = []
            self.pending_amenities = []
            self.pending_text_hashes = []
            self.text_by_hash = {}
            self.pending_image_hashes = []
            self.image_by_hash = {}
            self.pending_embed_texts = []

    importer = ParserDBWriter(batch_size=batch_size)

    async def emit(row: dict[str, Any]) -> None:
        await sync_to_async(importer.add_row, thread_sensitive=True)(row)

    async def finalize() -> int:
        return await sync_to_async(importer.finalize, thread_sensitive=True)()

    async def truncate() -> None:
        await sync_to_async(importer.truncate_all, thread_sensitive=True)()

    return emit, finalize, truncate


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def extract_hotel_stars_from_name(hotel_name: str) -> str:
    """
    Extract stars count from hotel name/title.
    Examples: "Hotel Abc 4*", "Hotel Abc 4 *", "Hotel Abc 4 звезды".
    Returns "" if not found.
    """
    s = normalize_space(hotel_name)
    m = re.search(r"\b([1-5])\s*(?:\*|звезд(?:а|ы)?)\b", s, flags=re.I)
    return m.group(1) if m else ""


def infer_hotel_type_from_target_description(target_description: str) -> str:
    """
    Two values:
    - 'с детьми' if there are kid-related keywords
    - 'для взрослых' otherwise
    """
    t = (target_description or "").lower()
    kid_markers = [
        "детск",
        "ребен",
        "дети",
        "kids",
        "child",
        "семейн",
        "для детей",
        "baby",
        "няня",
        "детский бассейн",
        "детская площадка",
        "детский клуб",
    ]
    return "с детьми" if any(k in t for k in kid_markers) else "для взрослых"


def resolve_source_csv(root: Path) -> Path:
    p1 = root / "anextour_tours_dynamics.csv"
    p2 = root / "anextour_tours_dynamic.csv"
    if p1.exists():
        return p1
    if p2.exists():
        return p2
    raise FileNotFoundError("Не найден anextour_tours_dynamics.csv или anextour_tours_dynamic.csv")


def load_city_names(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл городов: {path}")
    return {normalize_space(x).lstrip("\ufeff").lower() for x in path.read_text(encoding="utf-8-sig").splitlines() if normalize_space(x)}


def parse_country_from_link(link: str, city_names: set[str]) -> tuple[str, bool]:
    """Return (country_slug, has_city_prefix)."""
    try:
        parsed = urlparse(link)
    except Exception:
        return "", False
    if parsed.netloc != "anextour.ru":
        return "", False

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "tours":
        return parts[1].lower(), False
    if len(parts) >= 3 and parts[0].lower() in city_names and parts[1] == "tours":
        return parts[2].lower(), True
    return "", False


def extract_description_segment(raw: str) -> str:
    if not raw:
        return ""
    m = re.search(r"(Интересное в .*?)(?=Популярные курорты)", raw, flags=re.S)
    if not m:
        return ""
    return normalize_space(m.group(1))


def country_description_from_rows(rows: list[dict[str, str]], country_slug: str, city_names: set[str]) -> str:
    for row in rows:
        link = row.get("link", "")
        c, has_city = parse_country_from_link(link, city_names)
        if c != country_slug or not has_city:
            continue

        # Prefer details JSON body text/description when available
        details = row.get("details", "")
        if details:
            try:
                d = json.loads(details)
                for key in ("description", "body_text", "raw_text"):
                    txt = d.get(key)
                    seg = extract_description_segment(str(txt or ""))
                    if seg:
                        return seg
            except Exception:
                pass

        # Fallback raw_text column
        seg = extract_description_segment(row.get("raw_text", ""))
        if seg:
            return seg

    return ""


def select_countries(country_slug: str, country_slugs: str, max_countries: int) -> list[str]:
    countries = list(DEFAULT_COUNTRY_SLUGS)
    if country_slug:
        countries = [c for c in countries if c == country_slug.strip().lower()]
    if country_slugs:
        requested = {x.strip().lower() for x in country_slugs.split(",") if x.strip()}
        countries = [c for c in countries if c in requested]
    if max_countries and max_countries > 0:
        countries = countries[:max_countries]
    return countries


def select_towns(townfrom: str, max_towns: int) -> list[str]:
    towns = list(DEFAULT_TOWNS)
    if townfrom:
        towns = [normalize_space(townfrom).lower()]
    if max_towns and max_towns > 0:
        towns = towns[:max_towns]
    return towns


def _abs_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return "https://anextour.ru" + href
    return ""


async def discover_base_links_for_country(page, country_slug: str, *, max_links: int = 0) -> list[str]:
    """
    Discover hotel base links for a country by opening its /tours/<country> listing
    and collecting unique URLs like https://anextour.ru/tours/<country>/<hotel>.
    """
    listing_url = f"https://anextour.ru/tours/{country_slug}"
    try:
        await page.goto(listing_url, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except PlaywrightTimeoutError:
            pass
    except Exception:
        return []

    await click_show_more_until_end(page)

    hrefs = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => e.getAttribute('href')).filter(Boolean)",
    )
    out: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        url = _abs_url(str(href))
        if not url:
            continue
        try:
            p = urlparse(url)
        except Exception:
            continue
        if p.netloc != "anextour.ru":
            continue
        parts = [x for x in p.path.split("/") if x]
        if len(parts) != 3:
            continue
        if parts[0] != "tours":
            continue
        if parts[1].lower() != country_slug.lower():
            continue
        # ensure no query, no fragment: base link only
        if p.query or p.fragment:
            continue
        clean = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
        if clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
        if max_links and max_links > 0 and len(out) >= max_links:
            break
    return out


async def fetch_country_common_description(page, *, town: str, country_slug: str) -> str:
    """
    Try to extract country-level "Интересное в ..." segment from a city-country tours page.
    This replaces CSV-derived common_description.
    """
    urls = [
        f"https://anextour.ru/{town}/tours/{country_slug}",
        f"https://anextour.ru/tours/{country_slug}",
    ]
    for u in urls:
        try:
            await page.goto(u, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except PlaywrightTimeoutError:
                pass
            body_text = await page.inner_text("body")
            desc = extract_description_segment(body_text)
            if desc:
                return desc
        except Exception:
            continue
    return ""


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def collect_country_links(rows: list[dict[str, str]], city_names: set[str]) -> dict[str, list[str]]:
    links_by_country: dict[str, list[str]] = {}

    for row in rows:
        link = row.get("link", "")
        country, has_city = parse_country_from_link(link, city_names)
        if not country:
            continue
        if has_city:
            # skip city-prefixed links for base hotel list
            continue
        links_by_country.setdefault(country, []).append(link)

    if not links_by_country:
        raise RuntimeError("Не найдено ни одной ссылки страны без городского префикса")

    return {k: sorted(set(v)) for k, v in sorted(links_by_country.items(), key=lambda x: x[0])}

def build_url(base_link: str, params: dict[str, str]) -> str:
    parsed = urlparse(base_link)
    q = parse_qs(parsed.query, keep_blank_values=True)
    for k, v in params.items():
        q[k] = [str(v)]
    query = urlencode(q, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))


async def click_show_more_until_end(page: Any, max_clicks: int = 200) -> None:
    clicks = 0
    stale = 0
    prev_count = -1

    while clicks < max_clicks and stale < 8:
        await page.mouse.wheel(0, 5000)
        await page.keyboard.press("End")
        await page.wait_for_timeout(600)

        btn = page.get_by_role("button", name=re.compile(r"показать\s+ещ[её]|загрузить", re.I))
        clicked = False
        if await btn.count() > 0 and await btn.first.is_visible():
            try:
                await btn.first.click(timeout=2500)
                await page.wait_for_timeout(900)
                clicks += 1
                clicked = True
            except Exception:
                pass

        cur = await page.eval_on_selector_all("a[href*='booking'],a[href*='/booking']", "els => els.length")
        if cur <= prev_count and not clicked:
            stale += 1
        else:
            stale = 0
            prev_count = cur


async def extract_offer_cards(page: Any) -> list[dict[str, str]]:
    js = r"""
    () => {
      const clean = (x) => (x || '').replace(/\s+/g, ' ').trim();
      const offerLinks = Array.from(document.querySelectorAll('a[href*="booking"],a[href*="/booking"]'));
      const out = [];

      const iconMap = {
        'tv': 'tv',
        'phone': 'phone',
        'shower': 'shower',
        'air-conditioning': 'air-conditioning',
        'safe': 'safe',
        'wifi': 'wifi',
        'terrace': 'terrace',
        'balcony': 'balcony',
        'mini-bar': 'mini-bar',
        'hairdryer': 'hairdryer',
        'kettle': 'kettle',
        'kitchen': 'kitchen'
      };

      const globalFunctions = [];
      const iconNodes = Array.from(document.querySelectorAll("[style*='roomdesc/']"));
      for (const n of iconNodes) {
        const style = n.getAttribute('style') || '';
        const m = style.match(/roomdesc\/([a-z0-9-]+)\.svg/i);
        if (m) {
          const key = m[1].toLowerCase();
          globalFunctions.push(iconMap[key] || key);
        }
      }

      const mealCodes = ['RO','BB','HB','FB','AI','UAI','AO','BO','HB+','FB+','AI+','UAI+'];

      for (const a of offerLinks) {
        const booking = clean(a.href || a.getAttribute('href') || '');
        if (!booking) continue;

        const card = a.closest('article') || a.closest('li') || a.closest("div[class*='card']") || a.closest("div[class*='offer']") || a.closest('div');
        if (!card) continue;

        const textRaw = (card.innerText || '').trim();
        const text = clean(textRaw);
        if (!text) continue;

        const dateMatch = text.match(/\b\d{2}\.\d{2}\.\d{4}\s*[-–]\s*\d{2}\.\d{2}\.\d{4}\b/);
        const nightsMatch = text.match(/(\d{1,2})\s*ноч/i) || text.match(/ночей?\s*(\d{1,2})/i);
        const priceMatch = text.match(/\d[\d\s]{2,}(?:\s?₽|\s?руб|\s?р\b)/i);

        const lines = textRaw.split('\n').map(clean).filter(Boolean);

        // User requirement: "room" is everything before the "Дата поездки" label.
        let room = '';
        const lowerRaw = textRaw.toLowerCase();
        const idxTrip = lowerRaw.indexOf('дата поездки');
        if (idxTrip >= 0) {
          room = clean(textRaw.slice(0, idxTrip));
        } else {
          // Fallback: everything before the first date range if label is absent.
          if (dateMatch && dateMatch[0]) {
            const idx = text.indexOf(dateMatch[0]);
            if (idx > 0) room = clean(text.slice(0, idx));
          }
        }

        let meal = '';
        let placement = '';
        let funcs = [...globalFunctions];
        let tripDates = dateMatch ? clean(dateMatch[0]) : '';
        let nights = nightsMatch ? clean(nightsMatch[1]) : '';

        for (const line of lines) {
          if (!tripDates) {
            const dm = line.match(/\b\d{2}\.\d{2}\.\d{4}\s*[-–]\s*\d{2}\.\d{2}\.\d{4}\b/);
            if (dm) tripDates = clean(dm[0]);
          }
          if (!nights) {
            const nm = line.match(/(\d{1,2})\s*ноч/i) || line.match(/ночей?\s*(\d{1,2})/i);
            if (nm) nights = clean(nm[1]);
          }

          if (!room && /(room|номер|апартамент|apartment|suite|studio|standard|superior|deluxe|family|economy|villa|bungalow)/i.test(line)) {
            room = line;
          }

          const m = line.toUpperCase().replace(/\s+/g, '');
          if (!meal && mealCodes.includes(m)) meal = m;

          if (!placement && /((\d+)\s*(взр|реб|чел)|adults?|children?|размещ|состав туристов)/i.test(line)) {
            placement = line;
          }

          if (/wi-?fi|бассейн|пляж|спа|сауна|трансфер|спорт|бар|ресторан/i.test(line)) funcs.push(line);
        }

        if (!meal) {
          const mealRe = text.match(/\b(UAI\+|AI\+|FB\+|HB\+|UAI|AI|FB|HB|BB|RO|AO|BO)\b/i);
          if (mealRe) meal = mealRe[1].toUpperCase();
        }

        if (!placement) {
          const plRe = text.match(/(\d+\s*(?:взр|взросл|реб|дет|чел)(?:\s*[+/,]\s*\d+\s*(?:взр|взросл|реб|дет|чел))*)/i);
          if (plRe) placement = clean(plRe[1]);
        }

        if (!room) {
          const rmRe = text.match(/((?:standard|superior|deluxe|economy|family|studio|suite|apartment|villa|bungalow|номер|апартамент)[^,\n]{0,80})/i);
          if (rmRe) room = clean(rmRe[1]);
        }

        out.push({
          functions: Array.from(new Set(funcs)).join('; '),
          trip_dates: tripDates,
          nights: nights,
          room: clean(room),
          meal: clean(meal),
          placement: clean(placement),
          price: priceMatch ? clean(priceMatch[0]) : '',
          booking_link: booking,
          raw_text: text
        });
      }

      return out;
    }
    """
    items = await page.evaluate(js)
    uniq = {}
    for it in items:
        key = (it.get("booking_link", ""), it.get("raw_text", ""))
        uniq[key] = it
    return list(uniq.values())


async def extract_base_hotel_details(page: Any) -> dict[str, str]:
    """
    Extract hotel name + main image URL from the hotel (base_link) page.
    """
    js = r"""
    () => {
      const clean = (x) => (x || '').replace(/\s+/g, ' ').trim();
      const abs = (u) => {
        if (!u) return '';
        if (u.startsWith('//')) return 'https:' + u;
        return u;
      };

      const ogImage = document.querySelector('meta[property="og:image"]')?.getAttribute('content') || '';

      let hotelName = clean(document.querySelector('h1[data-hotelinc]')?.textContent || '');
      if (!hotelName) hotelName = clean(document.querySelector('h1')?.textContent || '');
      if (!hotelName) hotelName = clean(document.title || '');

      // Primary: first photo in the gallery block (grid with hotel images)
      let imageUrl = '';
      const gridImg =
        document.querySelector('div.grid.gap-16.w-full img[src]') ||
        document.querySelector('div.grid img[src]');
      if (gridImg) imageUrl = abs(clean(gridImg.getAttribute('src') || ''));

      // Fallbacks
      if (!imageUrl) imageUrl = abs(clean(ogImage));
      if (!imageUrl) {
        const imgs = Array.from(document.querySelectorAll('img[src]'))
          .map((img) => img.getAttribute('src') || '')
          .map(clean)
          .filter((s) => s.includes('files.anextour.ru/hotel/') || s.includes('/hotel/'));
        if (imgs.length) imageUrl = abs(imgs[0]);
      }
      if (!imageUrl) {
        const imgs = Array.from(document.querySelectorAll('img[src]'))
          .map((img) => img.getAttribute('src') || '')
          .map(clean)
          .filter(Boolean);
        if (imgs.length) imageUrl = abs(imgs[0]);
      }

      // Stars are usually rendered as: "4" + star icon near the title.
      let stars = '';
      const title = document.querySelector('h1[data-hotelinc]') || document.querySelector('h1');
      if (title) {
        const wrap = title.parentElement;
        if (wrap) {
          const candidates = Array.from(wrap.querySelectorAll('div'))
            .map((d) => clean(d.textContent || ''))
            .filter(Boolean);
          for (const t of candidates) {
            const m = t.match(/\b([1-5])\b/);
            if (m && t.length <= 3) { stars = m[1]; break; }
          }
        }
      }

      // Rating (e.g. 4.7) is typically shown as a green badge.
      let rating = '';
      const ratingEl =
        document.querySelector('span.bg-green-dark') ||
        document.querySelector('div.text-12 span') ||
        null;
      if (ratingEl) {
        const txt = clean(ratingEl.textContent || '');
        if (/^\d+(?:[.,]\d+)?$/.test(txt)) rating = txt.replace(',', '.');
      }

      return { hotel_name: hotelName, main_image_url: imageUrl, hotel_rating: rating, hotel_stars: stars };
    }
    """
    try:
        d = await page.evaluate(js)

        js_selected_tabpanel_text = r"""
        () => {
          const clean = (x) => (x || '').replace(/\s+/g, ' ').trim();
          const norm = (x) => clean(String(x || '').replace(/\s+/g, ' '));

          const selectedTab = document.querySelector('[role="tab"][aria-selected="true"]');
          let panel = null;
          if (selectedTab) {
            const ctrl = selectedTab.getAttribute('aria-controls') || '';
            if (ctrl) panel = document.getElementById(ctrl);
            if (!panel) {
              const tabId = selectedTab.getAttribute('id') || '';
              if (tabId) panel = document.querySelector(`[role="tabpanel"][aria-labelledby="${tabId}"]`);
            }
          }
          if (!panel) {
            // Fallback: take the first tabpanel on the page.
            panel = document.querySelector('[role="tabpanel"]');
          }
          if (!panel) return '';

          // Prefer explicit WYSIWYG block, but also include any additional text in the panel.
          const wys = panel.querySelector('.wysiwyg-data');
          const t1 = wys ? norm(wys.innerText || '') : '';
          const t2 = norm(panel.innerText || '');
          if (t1 && t2 && t2.length > t1.length) return t2;
          return t1 || t2 || '';
        }
        """

        async def click_tab(name_re: re.Pattern[str]) -> None:
            tab = page.get_by_role("tab", name=name_re)
            if await tab.count() > 0:
                try:
                    await tab.first.click(timeout=2500)
                except Exception:
                    pass
                await page.wait_for_timeout(700)

        # Build target_description from two tabs: "Информация" + "Услуги и питание"
        info_text = ""
        services_text = ""
        try:
            await click_tab(re.compile(r"^информация$", re.I))
            info_text = normalize_space(await page.evaluate(js_selected_tabpanel_text))
        except Exception:
            info_text = ""
        try:
            await click_tab(re.compile(r"услуги\s+и\s+питание", re.I))
            services_text = normalize_space(await page.evaluate(js_selected_tabpanel_text))
        except Exception:
            services_text = ""

        combined = "\n\n".join([t for t in (info_text, services_text) if t])
        target_desc = normalize_space(combined)

        hotel_name = normalize_space(d.get("hotel_name", ""))
        target_desc = normalize_space(combined)
        hotel_stars = normalize_space(d.get("hotel_stars", "")) or extract_hotel_stars_from_name(hotel_name)
        return {
            "hotel_name": hotel_name,
            "hotel_rating": normalize_space(d.get("hotel_rating", "")),
            "hotel_stars": hotel_stars,
            "hotel_type": infer_hotel_type_from_target_description(target_desc),
            "main_image_url": normalize_space(d.get("main_image_url", "")),
            "target_description": target_desc,
        }
    except Exception:
        return {
            "hotel_name": "",
            "hotel_rating": "",
            "hotel_stars": "",
            "hotel_type": "",
            "main_image_url": "",
            "target_description": "",
        }

async def has_results_for_date(page: Any, base_link: str, townfrom: str, checkin_beg: str) -> bool:
    d = datetime.strptime(checkin_beg, "%Y%m%d").date()
    params = dict(DEFAULT_PARAMS)
    params.update(
        {
            "TOWNFROM": townfrom,
            "ADULT": "1",
            "CHILD": "0",
            "NIGHTMIN": "2",
            "NIGHTMAX": "2",
            "CHECKIN_BEG": d.strftime("%Y%m%d"),
            "CHECKIN_END": (d + timedelta(days=7)).strftime("%Y%m%d"),
        }
    )
    url = build_url(base_link, params)
    try:
        await page.goto(url, wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        return False
    except Exception:
        return False
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except PlaywrightTimeoutError:
        pass

    await click_show_more_until_end(page, max_clicks=60)
    offers = await extract_offer_cards(page)
    return len(offers) > 0


async def find_first_working_date(page: Any, base_link: str, townfrom: str, start_yyyymmdd: str, max_checkin_beg: str, max_days: int = 40) -> str | None:
    start = datetime.strptime(start_yyyymmdd, "%Y%m%d").date()
    limit = datetime.strptime(max_checkin_beg, "%Y%m%d").date()
    for i in range(max_days):
        d = start + timedelta(days=i)
        if d > limit:
            break
        beg = d.strftime("%Y%m%d")
        ok = await has_results_for_date(page, base_link, townfrom, beg)
        if ok:
            return beg
    return None


def append_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    need_header = (not path.exists()) or path.stat().st_size == 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if need_header:
            writer.writeheader()
        writer.writerows(rows)


def append_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def materialize_json_from_jsonl(jsonl_path: Path, json_out: Path) -> None:
    if not jsonl_path.exists():
        json_out.write_text("[]", encoding="utf-8")
        return

    json_out.parent.mkdir(parents=True, exist_ok=True)
    with json_out.open("w", encoding="utf-8") as wf, jsonl_path.open("r", encoding="utf-8") as rf:
        wf.write("[")
        first = True
        for line in rf:
            line = line.strip()
            if not line:
                continue
            if first:
                first = False
            else:
                wf.write(",")
            wf.write(line)
        wf.write("]")


async def run(args: argparse.Namespace) -> None:
    # Default mode: fully self-contained discovery (no CSV required).
    rows: list[dict[str, str]] = []
    city_names: set[str] = set(DEFAULT_TOWNS)
    links_by_country: dict[str, list[str]] = {}
    root = Path(args.root)
    project_root = Path(__file__).resolve().parent

    countries = select_countries(args.country_slug, args.country_slugs, args.max_countries)
    towns = select_towns(args.townfrom, args.max_towns)

    print("[info] source: code(discovery)")
    print(f"[info] countries total: {len(countries)}")
    print(f"[info] towns: {len(towns)}")

    csv_out = Path(args.out_csv)
    json_out = Path(args.out_json)
    jsonl_out = Path(str(json_out) + ".jsonl")

    stop_flag = Path(args.stop_flag) if args.stop_flag else (project_root / "STOP_PARSING.flag")
    if args.debug_stages:
        print(f"[debug] stop_flag path: {stop_flag}", flush=True)
    flush_interval = max(10, args.flush_interval_sec)
    db_emit = None
    db_finalize = None
    db_truncate = None

    if args.write_db:
        db_emit, db_finalize, db_truncate = build_db_emitter(args.db_batch_size)

    if args.reset_output and args.write_output:
        for p in (csv_out, json_out, jsonl_out):
            if p.exists():
                p.unlink()
    if args.reset_db and db_truncate is not None:
        await db_truncate()

    fieldnames = list(ParsedTour.__annotations__.keys())
    buffer: list[dict[str, Any]] = []
    total_written = 0
    last_flush = time.monotonic()
    stop_requested = False

    def flush(force: bool = False) -> None:
        nonlocal buffer, total_written, last_flush
        if not args.write_output:
            buffer = []
            last_flush = time.monotonic()
            return
        now = time.monotonic()
        if not buffer:
            return
        if not force and (now - last_flush) < flush_interval:
            return

        append_csv_rows(csv_out, buffer, fieldnames)
        append_jsonl_rows(jsonl_out, buffer)
        total_written += len(buffer)
        print(f"[flush] wrote {len(buffer)} rows (total={total_written})")
        buffer = []
        last_flush = now

    async def emit_row(row: dict[str, Any]) -> None:
        if db_emit is not None:
            await db_emit(row)
        buffer.append(row)
        flush(force=False)

    stop_requested = await run_core(
        args,
        rows=rows,
        city_names=city_names,
        links_by_country=links_by_country,
        countries=countries,
        towns=towns,
        stop_flag=stop_flag,
        emit_row=emit_row,
    )

    flush(force=True)
    if db_finalize is not None:
        written_to_db = await db_finalize()
        print(f"[done] db_rows_flushed: {written_to_db}")
    if args.write_output:
        materialize_json_from_jsonl(jsonl_out, json_out)

    status = "stopped_by_flag" if stop_requested else "completed"
    print(f"[done] status: {status}")
    if args.write_output:
        print(f"[done] json: {json_out}")
        print(f"[done] csv:  {csv_out}")
        print(f"[done] rows_written: {total_written}")

async def run_core(
    args: argparse.Namespace,
    *,
    rows: list[dict[str, str]],
    city_names: set[str],
    links_by_country: dict[str, list[str]],
    countries: list[str],
    towns: list[str],
    stop_flag: Path,
    emit_row,
) -> bool:
    """
    Core parsing loop that emits ParsedTour rows to `emit_row` (dict).
    Returns True if stopped by stop-flag.

    This allows writing to other sinks (e.g. direct DB upserts) without CSV промежуточных файлов.
    """
    if args.debug_stages:
        print("[debug] run_core: entering async_playwright", flush=True)
    async with async_playwright() as p:
        if args.debug_stages:
            print("[debug] run_core: launching browser", flush=True)
        browser = await p.chromium.launch(headless=args.headless)
        if args.debug_stages:
            print("[debug] run_core: browser launched", flush=True)
        semaphore = asyncio.Semaphore(max(1, args.country_workers))
        tasks = [
            asyncio.create_task(
                process_country(
                    browser=browser,
                    semaphore=semaphore,
                    args=args,
                    rows=rows,
                    city_names=city_names,
                    links_by_country=links_by_country,
                    towns=towns,
                    stop_flag=stop_flag,
                    country_slug=country_slug,
                    emit_row=emit_row,
                )
            )
            for country_slug in countries
        ]
        if args.debug_stages:
            print(f"[debug] run_core: created {len(tasks)} country tasks", flush=True)

        results = []
        if tasks:
            results = await asyncio.gather(*tasks)
        if args.debug_stages:
            print("[debug] run_core: tasks completed", flush=True)

        await browser.close()
        if args.debug_stages:
            print("[debug] run_core: browser closed", flush=True)

    return any(results) or stop_flag.exists()


def _empty_base_details() -> dict[str, str]:
    return {
        "hotel_name": "",
        "hotel_rating": "",
        "hotel_stars": "",
        "hotel_type": "",
        "main_image_url": "",
        "target_description": "",
    }


async def process_country(
    *,
    browser,
    semaphore: asyncio.Semaphore,
    args: argparse.Namespace,
    rows: list[dict[str, str]],
    city_names: set[str],
    links_by_country: dict[str, list[str]],
    towns: list[str],
    stop_flag: Path,
    country_slug: str,
    emit_row,
) -> bool:
    async with semaphore:
        if stop_flag.exists():
            return True

        country_started_at = time.monotonic()

        def debug_log(message: str) -> None:
            if args.debug_stages:
                elapsed = time.monotonic() - country_started_at
                print(f"[debug] {country_slug} +{elapsed:.1f}s {message}", flush=True)

        context = await browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1600, "height": 1000},
        )
        page = await context.new_page()
        details_page = await context.new_page()
        page.set_default_timeout(args.timeout_ms)
        details_page.set_default_timeout(args.timeout_ms)

        base_link_cache: dict[str, dict[str, str]] = {}
        stop_requested = False
        try:
            debug_log("worker started")
            base_links = links_by_country.get(country_slug, [])
            if args.base_link:
                base_links = [args.base_link]
            if args.max_hotels > 0:
                base_links = base_links[: args.max_hotels]
            if not base_links:
                debug_log("discovering base links")
                base_links = await discover_base_links_for_country(details_page, country_slug, max_links=args.max_hotels)
                debug_log(f"discovered {len(base_links)} base links")

            if rows:
                common_description = country_description_from_rows(rows, country_slug, city_names)
                debug_log(f"country description from rows len={len(common_description)}")
            else:
                desc_town = towns[0] if towns else DEFAULT_PARAMS.get("TOWNFROM", "moskva")
                debug_log(f"fetching country description for town={desc_town}")
                common_description = await fetch_country_common_description(
                    details_page,
                    town=desc_town,
                    country_slug=country_slug,
                )
                debug_log(f"country description fetched len={len(common_description)}")
            print(f"[info] country: {country_slug}, hotels={len(base_links)}")

            for base_link in base_links:
                if stop_flag.exists():
                    stop_requested = True
                    break

                if base_link in base_link_cache:
                    base_details = base_link_cache[base_link]
                else:
                    try:
                        debug_log(f"loading hotel page {base_link}")
                        await details_page.goto(base_link, wait_until="domcontentloaded")
                        try:
                            await details_page.wait_for_load_state("networkidle", timeout=8000)
                        except PlaywrightTimeoutError:
                            pass
                        base_details = await extract_base_hotel_details(details_page)
                        debug_log(
                            "hotel details loaded "
                            f"name={bool(base_details.get('hotel_name'))} "
                            f"target_len={len(base_details.get('target_description', ''))}"
                        )
                    except Exception:
                        debug_log(f"hotel details failed for {base_link}")
                        base_details = _empty_base_details()
                    base_link_cache[base_link] = base_details

                for town in towns:
                    if stop_flag.exists():
                        stop_requested = True
                        break

                    debug_log(f"finding first working date for town={town}")
                    first_beg = await find_first_working_date(
                        page,
                        base_link,
                        town,
                        args.start_checkin_beg,
                        args.max_checkin_beg,
                        max_days=args.max_date_probe_days,
                    )
                    if not first_beg:
                        debug_log(f"no working date for town={town}")
                        print(f"[warn] no working date: {base_link} / {town}")
                        continue
                    debug_log(f"first working date={first_beg} for town={town}")

                    beg_date = datetime.strptime(first_beg, "%Y%m%d").date()
                    end_date = (beg_date + timedelta(days=7)).strftime("%Y%m%d")

                    for adult in range(1, args.adult_max + 1):
                        if stop_flag.exists():
                            stop_requested = True
                            break
                        for child in range(0, args.child_max + 1):
                            if stop_flag.exists():
                                stop_requested = True
                                break
                            for nmin, nmax in NIGHT_RANGES:
                                if stop_flag.exists():
                                    stop_requested = True
                                    break

                                params = dict(DEFAULT_PARAMS)
                                params.update(
                                    {
                                        "TOWNFROM": town,
                                        "ADULT": str(adult),
                                        "CHILD": str(child),
                                        "NIGHTMIN": str(nmin),
                                        "NIGHTMAX": str(nmax),
                                        "CHECKIN_BEG": first_beg,
                                        "CHECKIN_END": end_date,
                                    }
                                )
                                req_url = build_url(base_link, params)

                                try:
                                    debug_log(
                                        f"loading offers town={town} adult={adult} child={child} nights={nmin}-{nmax}"
                                    )
                                    await page.goto(req_url, wait_until="domcontentloaded")
                                except PlaywrightTimeoutError:
                                    debug_log("offers page goto timeout")
                                    continue
                                except Exception:
                                    debug_log("offers page goto failed")
                                    continue
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=8000)
                                except PlaywrightTimeoutError:
                                    pass

                                await click_show_more_until_end(page)
                                offers = await extract_offer_cards(page)
                                debug_log(
                                    f"offers extracted count={len(offers)} town={town} adult={adult} child={child} nights={nmin}-{nmax}"
                                )

                                for offer in offers:
                                    await emit_row(
                                        asdict(
                                            ParsedTour(
                                                country_slug=country_slug,
                                                base_link=base_link,
                                                request_url=req_url,
                                                townfrom=town,
                                                adult=adult,
                                                child=child,
                                                night_min=nmin,
                                                night_max=nmax,
                                                checkin_beg=first_beg,
                                                checkin_end=end_date,
                                                hotel_name=base_details.get("hotel_name", ""),
                                                hotel_rating=base_details.get("hotel_rating", ""),
                                                hotel_stars=base_details.get("hotel_stars", ""),
                                                hotel_type=base_details.get("hotel_type", ""),
                                                main_image_url=base_details.get("main_image_url", ""),
                                                common_description=common_description,
                                                target_description=base_details.get("target_description", ""),
                                                functions=offer.get("functions", ""),
                                                trip_dates=offer.get("trip_dates", ""),
                                                nights=offer.get("nights", ""),
                                                room=offer.get("room", ""),
                                                meal=offer.get("meal", ""),
                                                placement=offer.get("placement", ""),
                                                price=offer.get("price", ""),
                                                booking_link=offer.get("booking_link", ""),
                                                raw_text=offer.get("raw_text", ""),
                                            )
                                        )
                                    )
                                if offers:
                                    debug_log(f"emitted {len(offers)} rows")

                                print(
                                    f"[ok] {country_slug} {town} A{adult} C{child} N{nmin}-{nmax} "
                                    f"beg={first_beg} offers={len(offers)}"
                                )

                            if stop_requested:
                                break
                        if stop_requested:
                            break
                    if stop_requested:
                        break
                if stop_requested:
                    break
        finally:
            debug_log("closing worker context")
            await context.close()

        return stop_requested

def build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate available tours csv/json for all countries")
    p.add_argument("--root", default=r"D:\asoiu")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--timeout-ms", type=int, default=30000)
    p.add_argument("--start-checkin-beg", default=DEFAULT_CHECKIN_BEG)
    p.add_argument("--max-checkin-beg", default=DEFAULT_MAX_CHECKIN_BEG)
    p.add_argument("--max-date-probe-days", type=int, default=40)
    p.add_argument("--max-hotels", type=int, default=1, help="Limit hotels per country (0 = all)")
    p.add_argument("--max-towns", type=int, default=3, help="Limit towns (0 = all)")
    p.add_argument("--townfrom", default="", help="Force one departure town slug (e.g. moskva)")
    p.add_argument("--base-link", default="", help="Force one hotel base_link to parse (exact URL)")
    p.add_argument("--max-countries", type=int, default=0, help="Limit countries (0 = all)")
    p.add_argument("--country-slug", default="", help="Parse only one country slug")
    p.add_argument("--country-slugs", default="", help="Comma-separated country slugs to parse")
    p.add_argument("--out-json", default=r"D:\asoiu\anextour_available_tours_all_countries_example.json")
    p.add_argument("--out-csv", default=r"D:\asoiu\anextour_available_tours_all_countries_example.csv")
    p.add_argument("--adult-max", type=int, default=10, help="Max adults (start is always 1)")
    p.add_argument("--child-max", type=int, default=10, help="Max children (start is always 0)")
    p.add_argument("--flush-interval-sec", type=int, default=120, help="Flush partial results every N seconds")
    p.add_argument("--country-workers", type=int, default=20, help="How many countries to parse in parallel")
    p.add_argument("--db-batch-size", type=int, default=200, help="Batch size for direct DB writes")
    p.add_argument("--debug-stages", action="store_true", help="Print detailed stage-by-stage parser diagnostics")
    p.add_argument("--write-db", dest="write_db", action="store_true", help="Write parsed tours directly to Django DB")
    p.add_argument("--no-write-db", dest="write_db", action="store_false", help="Disable direct DB writes")
    p.add_argument("--write-output", action="store_true", help="Additionally save parsed rows to CSV/JSON files")
    p.add_argument("--reset-db", action="store_true", help="Truncate tours-related tables before direct DB write")
    p.add_argument("--stop-flag", default="", help="Path to stop flag file for safe stop")
    p.add_argument("--reset-output", action="store_true", help="Remove old out files before run")
    p.set_defaults(write_db=True)
    return p.parse_args()

def main() -> None:
    args = build_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()



















