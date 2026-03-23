import csv
import hashlib
import re
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.utils.text import slugify

from tours.embeddings import get_embedder
from tours.models import Amenity, Favorite, Tour, TourImage, TourText


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

def _parse_price(value: str | None) -> tuple[int | None, str]:
    text = (value or "").strip()
    digits = _PRICE_RE.findall(text)
    if not digits:
        return None, text
    try:
        return int("".join(digits)), text
    except ValueError:
        return None, text


def _parse_hotel_category_from_csv(value: str | None) -> int | None:
    return _parse_int(value)


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


def _parse_rest_type(*values: str | None) -> str:
    text = " ".join([v for v in values if v]).lower()
    if not text:
        return ""
    if "пляж" in text or "море" in text:
        return "пляжный"
    if "город" in text or "экскурс" in text:
        return "городской"
    return ""


def _parse_hotel_type(*values: str | None) -> str:
    text = " ".join([v for v in values if v]).lower()
    if not text:
        return ""
    if (
        "для взрослых" in text
        or "взросл" in text
        or "adults only" in text
        or "adult only" in text
    ):
        return "Для взрослых"
    if "для детей" in text or "детск" in text or "с детьми" in text or "дет" in text:
        return "Для детей"
    return ""


def _normalize_hotel_type(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    lower = value.lower()
    if "взросл" in lower or "adults only" in lower or "adult only" in lower:
        return "Для взрослых"
    if "дет" in lower or "с детьми" in lower:
        return "Для детей"
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_INFRA_RE = re.compile(r"\bинфраструктура\b", flags=re.IGNORECASE)
_RULES_RE = re.compile(r"правила\s+размещения\s+в\s+отелях", flags=re.IGNORECASE)


def _extract_answer_description(target_desc: str) -> str:
    target_desc = (target_desc or "").strip()
    if not target_desc:
        return ""
    m = _INFRA_RE.search(target_desc)
    if not m:
        extracted = target_desc
    else:
        extracted = target_desc[: m.start()].strip()

    extracted = _RULES_RE.sub("", extracted).strip()
    return extracted


def _to_ru_label(value: str | None, mapping: dict[str, str]) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    # if it's already in Cyrillic, keep as-is
    if re.search(r"[А-Яа-яЁё]", v):
        return v
    return mapping.get(v, v)


_COUNTRY_SLUG_TO_RU: dict[str, str] = {
    "abkhazia": "Абхазия",
    "andorra": "Андорра",
    "argentina": "Аргентина",
    "armenia": "Армения",
    "aruba": "Аруба",
    "austria": "Австрия",
    "azerbaijan": "Азербайджан",
    "bahrain": "Бахрейн",
    "belarus": "Беларусь",
    "belgium": "Бельгия",
    "brazil": "Бразилия",
    "bulgaria": "Болгария",
    "cambodia": "Камбоджа",
    "cape-verde": "Кабо-Верде",
    "chile": "Чили",
    "china": "Китай",
    "china-hong-kong-sar": "Гонконг",
    "china-macau-sar": "Макао",
    "costa-rica": "Коста-Рика",
    "croatia": "Хорватия",
    "cuba": "Куба",
    "cyprus": "Кипр",
    "czech-republic": "Чехия",
    "dominican-republic": "Доминикана",
    "egypt": "Египет",
    "fiji": "Фиджи",
    "france": "Франция",
    "georgia": "Грузия",
    "germany": "Германия",
    "greece": "Греция",
    "hungary": "Венгрия",
    "india": "Индия",
    "indonesia": "Индонезия",
    "israel": "Израиль",
    "italy": "Италия",
    "jamaica": "Ямайка",
    "japan": "Япония",
    "jordan": "Иордания",
    "kazakhstan": "Казахстан",
    "kenya": "Кения",
    "kyrgyzstan": "Кыргызстан",
    "lebanon": "Ливан",
    "madagascar": "Мадагаскар",
    "malaysia": "Малайзия",
    "maldives": "Мальдивы",
    "malta": "Мальта",
    "mauritius": "Мавритания",
    "mexico": "Мексика",
    "mongolia": "Монголия",
    "montenegro": "Черногория",
    "morocco": "Марокко",
    "namibia": "Намибия",
    "nepal": "Непал",
    "netherlands": "Нидерланды",
    "oman": "Оман",
    "panama": "Панама",
    "peru": "Перу",
    "philippines": "Филиппины",
    "portugal": "Португалия",
    "qatar": "Катар",
    "russia": "Россия",
    "saudi-arabia": "Саудовская Аравия",
    "serbia": "Сербия",
    "seychelles": "Сейшелы",
    "singapore": "Сингапур",
    "slovenia": "Словения",
    "south-korea": "Южная Корея",
    "spain": "Испания",
    "sri-lanka": "Шри-Ланка",
    "switzerland": "Швейцария",
    "tanzania": "Танзания",
    "thailand": "Таиланд",
    "tunisia": "Тунис",
    "turkey": "Турция",
    "turkmenistan": "Туркменистан",
    "uae": "ОАЭ",
    "uruguay": "Уругвай",
    "uzbekistan": "Узбекистан",
    "vietnam": "Вьетнам",
}


_TOWNFROM_SLUG_TO_RU: dict[str, str] = {
    "barnaul": "Барнаул",
    "chelyabinsk": "Челябинск",
    "ekaterinburg": "Екатеринбург",
    "kaliningrad": "Калининград",
    "kazan": "Казань",
    "krasnodar": "Краснодар",
    "n-novgorod": "Нижний Новгород",
    "novosibirsk": "Новосибирск",
    "omsk": "Омск",
    "perm": "Пермь",
    "rostov-na-donu": "Ростов-на-Дону",
    "samara": "Самара",
    "sankt-peterburg": "Санкт-Петербург",
    "tyumen": "Тюмень",
    "vladivostok": "Владивосток",
    "volgograd": "Волгоград",
    # legacy aliases
    "moskva": "Москва",
    "moscow": "Москва",
    "spb": "Санкт-Петербург",
}


class Command(BaseCommand):
    help = "Import tours from CSV files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            default=None,
            help="Path to a single CSV file to import (overrides --csv-dir).",
        )
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
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing tours/amenities/favorites before import.",
        )

    def handle(self, *args, **options):
        csv_file = options.get("csv_file")
        if csv_file:
            csv_path = Path(csv_file)
            if not csv_path.exists():
                raise SystemExit(f"CSV file not found: {csv_path}")
            csv_files = [csv_path]
            base_dir = None
        else:
            if options["csv_dir"]:
                base_dir = Path(options["csv_dir"])
            else:
                cwd = Path.cwd()
                # Prefer current dir if it contains CSV examples (e.g. belarus in repo root).
                if list(cwd.glob("anextour_available_tours_*.csv")):
                    base_dir = cwd
                elif (cwd / "parsed_country").exists():
                    base_dir = cwd / "parsed_country"
                else:
                    base_dir = cwd / "Распаршенные страны"
        limit = options["limit"]
        batch_size = options["batch_size"]
        truncate = bool(options.get("truncate"))

        if truncate:
            self.stdout.write("Truncating existing tours data...")
            with transaction.atomic():
                Favorite.objects.all().delete()
                Tour.amenities.through.objects.all().delete()
                Amenity.objects.all().delete()
                Tour.objects.all().delete()
                TourText.objects.all().delete()
                TourImage.objects.all().delete()

        if base_dir is not None:
            if not base_dir.exists():
                raise SystemExit(f"CSV dir not found: {base_dir}")

            csv_files = sorted(base_dir.glob("anextour_available_tours_*.csv"))
            if not csv_files:
                # fallback: any csv
                csv_files = sorted(base_dir.glob("*.csv"))
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
        pending_text_hashes: list[tuple[str | None, str | None, str | None]] = []
        text_by_hash: dict[str, str] = {}

        pending_image_hashes: list[str | None] = []
        image_by_hash: dict[str, str] = {}

        pending_embed_texts: list[str] = []

        # utf-8-sig gracefully handles CSVs saved with BOM (common on Windows)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                price_value, price_text = _parse_price(row.get("price"))

                common_desc = (row.get("common_description") or "").strip()
                target_desc = (row.get("target_description") or "").strip()
                answer_desc = _extract_answer_description(target_desc)
                common_hash = _sha256_text(common_desc) if common_desc else None
                target_hash = _sha256_text(target_desc) if target_desc else None
                answer_hash = _sha256_text(answer_desc) if answer_desc else None
                if common_hash and common_hash not in text_by_hash:
                    text_by_hash[common_hash] = common_desc
                if target_hash and target_hash not in text_by_hash:
                    text_by_hash[target_hash] = target_desc
                if answer_hash and answer_hash not in text_by_hash:
                    text_by_hash[answer_hash] = answer_desc

                hotel_category = _parse_hotel_category_from_csv(row.get("hotel_stars"))
                direct_hotel_type = _normalize_hotel_type(row.get("hotel_type"))

                country_slug = (row.get("country_slug") or "").strip()
                townfrom = (row.get("townfrom") or "").strip()

                image_url = (row.get("main_image_url") or "").strip() or None
                image_hash = _sha256_text(image_url) if image_url else None
                if image_hash and image_hash not in image_by_hash:
                    image_by_hash[image_hash] = image_url or ""

                embed_text = " ".join(
                    [
                        (row.get("hotel_name") or "").strip(),
                        (row.get("meal") or "").strip(),
                        (row.get("placement") or "").strip(),
                        (row.get("room") or "").strip(),
                        common_desc,
                        target_desc,
                        answer_desc,
                        (row.get("raw_text") or "").strip(),
                    ]
                ).strip()

                tour = Tour(
                    country_slug=country_slug,
                    country_ru=_to_ru_label(country_slug, _COUNTRY_SLUG_TO_RU),
                    base_link=(row.get("base_link") or "").strip() or None,
                    request_url=(row.get("request_url") or "").strip(),
                    townfrom=townfrom,
                    townfrom_ru=_to_ru_label(townfrom, _TOWNFROM_SLUG_TO_RU),
                    adult=_parse_int(row.get("adult")) or 0,
                    child=_parse_int(row.get("child")) or 0,
                    night_min=_parse_int(row.get("night_min")),
                    night_max=_parse_int(row.get("night_max")),
                    checkin_beg=_parse_date_yyyymmdd(row.get("checkin_beg")),
                    checkin_end=_parse_date_yyyymmdd(row.get("checkin_end")),
                    hotel_name=(row.get("hotel_name") or "").strip(),
                    hotel_rating=(row.get("hotel_rating") or "").strip(),
                    trip_dates=(row.get("trip_dates") or "").strip(),
                    nights=_parse_int(row.get("nights")),
                    room=(row.get("room") or "").strip(),
                    meal=(row.get("meal") or "").strip(),
                    placement=(row.get("placement") or "").strip(),
                    rest_type=_parse_rest_type(common_desc, target_desc, row.get("raw_text")),
                    hotel_type=direct_hotel_type
                    or _parse_hotel_type(target_desc, common_desc, row.get("raw_text")),
                    hotel_category=hotel_category,
                    price_text=price_text,
                    price_value=price_value,
                    booking_link=(row.get("booking_link") or "").strip() or None,
                    raw_text=(row.get("raw_text") or "").strip(),
                )
                to_create.append(tour)
                pending_amenities.append(_split_amenities(row.get("functions")))
                pending_text_hashes.append((common_hash, target_hash, answer_hash))
                pending_image_hashes.append(image_hash)
                pending_embed_texts.append(embed_text)

                if len(to_create) >= batch_size:
                    total = self._flush_batch(
                        to_create,
                        pending_amenities,
                        pending_text_hashes,
                        text_by_hash,
                        pending_image_hashes,
                        image_by_hash,
                        pending_embed_texts,
                        total,
                        limit,
                    )
                    to_create.clear()
                    pending_amenities.clear()
                    pending_text_hashes.clear()
                    text_by_hash.clear()
                    pending_image_hashes.clear()
                    image_by_hash.clear()
                    pending_embed_texts.clear()
                    if limit is not None and total >= limit:
                        return total

        if to_create:
            total = self._flush_batch(
                to_create,
                pending_amenities,
                pending_text_hashes,
                text_by_hash,
                pending_image_hashes,
                image_by_hash,
                pending_embed_texts,
                total,
                limit,
            )
        return total

    def _flush_batch(
        self,
        tours: list[Tour],
        pending_amenities: list[list[str]],
        pending_text_hashes: list[tuple[str | None, str | None, str | None]],
        text_by_hash: dict[str, str],
        pending_image_hashes: list[str | None],
        image_by_hash: dict[str, str],
        pending_embed_texts: list[str],
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

        # 1b) ensure TourText exists (common/target descriptions)
        text_hashes = {h for pair in pending_text_hashes for h in pair if h}
        if text_hashes:
            existing_text = dict(
                TourText.objects.filter(sha256__in=list(text_hashes)).values_list("sha256", "id")
            )
            missing_text = text_hashes - set(existing_text.keys())
            if missing_text:
                TourText.objects.bulk_create(
                    [
                        TourText(sha256=h, content=text_by_hash.get(h, ""))
                        for h in sorted(missing_text)
                    ],
                    ignore_conflicts=True,
                )
                existing_text = dict(
                    TourText.objects.filter(sha256__in=list(text_hashes)).values_list("sha256", "id")
                )

            for tour, (common_hash, target_hash, answer_hash) in zip(
                tours, pending_text_hashes, strict=False
            ):
                tour.common_description_id = existing_text.get(common_hash) if common_hash else None
                tour.target_description_id = existing_text.get(target_hash) if target_hash else None
                tour.answer_description_id = existing_text.get(answer_hash) if answer_hash else None

        # 1c) ensure TourImage exists (main_image_url -> FK)
        image_hashes = {h for h in pending_image_hashes if h}
        if image_hashes:
            existing_images = dict(
                TourImage.objects.filter(sha256__in=list(image_hashes)).values_list("sha256", "id")
            )
            missing_images = image_hashes - set(existing_images.keys())
            if missing_images:
                TourImage.objects.bulk_create(
                    [
                        TourImage(sha256=h, url=image_by_hash.get(h, ""))
                        for h in sorted(missing_images)
                    ],
                    ignore_conflicts=True,
                )
                existing_images = dict(
                    TourImage.objects.filter(sha256__in=list(image_hashes)).values_list("sha256", "id")
                )

            for tour, img_hash in zip(tours, pending_image_hashes, strict=False):
                tour.main_image_id = existing_images.get(img_hash) if img_hash else None

        # 1d) compute embeddings (pgvector) for semantic search
        if pending_embed_texts:
            embedder = get_embedder()
            try:
                vectors = embedder.embed_texts(pending_embed_texts)
                for tour, vec in zip(tours, vectors, strict=False):
                    tour.embedding = vec
            except Exception as e:
                self.stderr.write(f"WARNING: embeddings skipped for batch: {e}")

        # 2) insert tours (skip duplicates by request_url)
        with transaction.atomic():
            Tour.objects.bulk_create(tours, ignore_conflicts=True)

            created = {
                t.request_url: t.id
                for t in Tour.objects.filter(request_url__in=request_urls).only("id", "request_url")
            }

            # 2b) backfill hotel_category for existing rows (bulk_create ignore_conflicts won't update)
            url_to_category = {
                t.request_url: t.hotel_category for t in tours if t.request_url and t.hotel_category is not None
            }
            if url_to_category:
                whens = [When(request_url=url, then=Value(category)) for url, category in url_to_category.items()]
                Tour.objects.filter(
                    request_url__in=list(url_to_category.keys()),
                    hotel_category__isnull=True,
                ).update(hotel_category=Case(*whens, output_field=IntegerField()))

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
