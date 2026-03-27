import hashlib
import re
from datetime import date

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.utils.text import slugify

from tours.embeddings import get_embedder
from tours.models import Amenity, Favorite, Tour, TourImage, TourText


def parse_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_date_yyyymmdd(value: str | None) -> date | None:
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


def parse_price(value: str | None) -> tuple[int | None, str]:
    text = (value or "").strip()
    digits = _PRICE_RE.findall(text)
    if not digits:
        return None, text
    try:
        return int("".join(digits)), text
    except ValueError:
        return None, text


def parse_hotel_category_from_csv(value: str | None) -> int | None:
    return parse_int(value)


def split_amenities(value: str | None) -> list[str]:
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


def parse_rest_type(*values: str | None) -> str:
    text = " ".join([v for v in values if v]).lower()
    if not text:
        return ""
    if "пляж" in text or "море" in text:
        return "пляжный"
    if "город" in text or "экскурс" in text:
        return "городской"
    return ""


def parse_hotel_type(*values: str | None) -> str:
    text = " ".join([v for v in values if v]).lower()
    if not text:
        return ""
    if "для взрослых" in text or "взросл" in text or "adults only" in text or "adult only" in text:
        return "Для взрослых"
    if "для детей" in text or "детск" in text or "с детьми" in text or "дет" in text:
        return "Для детей"
    return ""


def normalize_hotel_type(value: str | None) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    lower = value.lower()
    if "взросл" in lower or "adults only" in lower or "adult only" in lower:
        return "Для взрослых"
    if "дет" in lower or "с детьми" in lower:
        return "Для детей"
    return value


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_INFRA_RE = re.compile(r"\bинфраструктура\b", flags=re.IGNORECASE)
_RULES_RE = re.compile(r"правила\s+размещения\s+в\s+отелях", flags=re.IGNORECASE)


def extract_answer_description(target_desc: str) -> str:
    target_desc = (target_desc or "").strip()
    if not target_desc:
        return ""
    match = _INFRA_RE.search(target_desc)
    extracted = target_desc if not match else target_desc[: match.start()].strip()
    return _RULES_RE.sub("", extracted).strip()


def to_ru_label(value: str | None, mapping: dict[str, str]) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if re.search(r"[А-Яа-яЁё]", v):
        return v
    return mapping.get(v, v)


COUNTRY_SLUG_TO_RU: dict[str, str] = {
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


TOWNFROM_SLUG_TO_RU: dict[str, str] = {
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
    "moskva": "Москва",
    "moscow": "Москва",
    "spb": "Санкт-Петербург",
}


class TourRowImporter:
    def __init__(self, *, batch_size: int = 1000, log=None):
        self.batch_size = batch_size
        self.log = log or (lambda *_args, **_kwargs: None)
        self.total_seen = 0
        self.total_flushed = 0
        self.to_create: list[Tour] = []
        self.pending_amenities: list[list[str]] = []
        self.pending_text_hashes: list[tuple[str | None, str | None, str | None]] = []
        self.text_by_hash: dict[str, str] = {}
        self.pending_image_hashes: list[str | None] = []
        self.image_by_hash: dict[str, str] = {}
        self.pending_embed_texts: list[str] = []

    def add_row(self, row: dict[str, str | int | None]) -> None:
        self.total_seen += 1
        price_value, price_text = parse_price(row.get("price"))  # type: ignore[arg-type]

        common_desc = str(row.get("common_description") or "").strip()
        target_desc = str(row.get("target_description") or "").strip()
        answer_desc = extract_answer_description(target_desc)

        common_hash = sha256_text(common_desc) if common_desc else None
        target_hash = sha256_text(target_desc) if target_desc else None
        answer_hash = sha256_text(answer_desc) if answer_desc else None
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
        image_hash = sha256_text(image_url) if image_url else None
        if image_hash and image_hash not in self.image_by_hash:
            self.image_by_hash[image_hash] = image_url or ""

        direct_hotel_type = normalize_hotel_type(str(row.get("hotel_type") or ""))
        hotel_category = parse_hotel_category_from_csv(str(row.get("hotel_stars") or ""))

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
            country_ru=to_ru_label(country_slug, COUNTRY_SLUG_TO_RU),
            base_link=str(row.get("base_link") or "").strip() or None,
            request_url=str(row.get("request_url") or "").strip(),
            townfrom=townfrom,
            townfrom_ru=to_ru_label(townfrom, TOWNFROM_SLUG_TO_RU),
            adult=parse_int(row.get("adult")) or 0,
            child=parse_int(row.get("child")) or 0,
            night_min=parse_int(row.get("night_min")),
            night_max=parse_int(row.get("night_max")),
            checkin_beg=parse_date_yyyymmdd(str(row.get("checkin_beg") or "")),
            checkin_end=parse_date_yyyymmdd(str(row.get("checkin_end") or "")),
            hotel_name=str(row.get("hotel_name") or "").strip(),
            hotel_rating=str(row.get("hotel_rating") or "").strip(),
            trip_dates=str(row.get("trip_dates") or "").strip(),
            nights=parse_int(row.get("nights")),
            room=str(row.get("room") or "").strip(),
            meal=str(row.get("meal") or "").strip(),
            placement=str(row.get("placement") or "").strip(),
            rest_type=parse_rest_type(common_desc, target_desc, str(row.get("raw_text") or "")),
            hotel_type=direct_hotel_type or parse_hotel_type(target_desc, common_desc, str(row.get("raw_text") or "")),
            hotel_category=hotel_category,
            price_text=price_text,
            price_value=price_value,
            booking_link=str(row.get("booking_link") or "").strip() or None,
            raw_text=str(row.get("raw_text") or "").strip(),
        )

        self.to_create.append(tour)
        self.pending_amenities.append(split_amenities(str(row.get("functions") or "")))
        self.pending_text_hashes.append((common_hash, target_hash, answer_hash))
        self.pending_image_hashes.append(image_hash)
        self.pending_embed_texts.append(embed_text)

        if len(self.to_create) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        tours = self.to_create
        if not tours:
            return 0

        request_urls = [t.request_url for t in tours if t.request_url]
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
                    [Amenity(slug=s, name=s.replace("-", " ")) for s in sorted(missing)],
                    ignore_conflicts=True,
                )
            slug_to_id = dict(Amenity.objects.filter(slug__in=amenity_slugs).values_list("slug", "id"))
        else:
            slug_to_id = {}

        text_hashes = {h for pair in self.pending_text_hashes for h in pair if h}
        if text_hashes:
            existing_text = dict(TourText.objects.filter(sha256__in=list(text_hashes)).values_list("sha256", "id"))
            missing_text = text_hashes - set(existing_text.keys())
            if missing_text:
                TourText.objects.bulk_create(
                    [TourText(sha256=h, content=self.text_by_hash.get(h, "")) for h in sorted(missing_text)],
                    ignore_conflicts=True,
                )
                existing_text = dict(TourText.objects.filter(sha256__in=list(text_hashes)).values_list("sha256", "id"))

            for tour, (common_hash, target_hash, answer_hash) in zip(tours, self.pending_text_hashes, strict=False):
                tour.common_description_id = existing_text.get(common_hash) if common_hash else None
                tour.target_description_id = existing_text.get(target_hash) if target_hash else None
                tour.answer_description_id = existing_text.get(answer_hash) if answer_hash else None

        image_hashes = {h for h in self.pending_image_hashes if h}
        if image_hashes:
            existing_images = dict(TourImage.objects.filter(sha256__in=list(image_hashes)).values_list("sha256", "id"))
            missing_images = image_hashes - set(existing_images.keys())
            if missing_images:
                TourImage.objects.bulk_create(
                    [TourImage(sha256=h, url=self.image_by_hash.get(h, "")) for h in sorted(missing_images)],
                    ignore_conflicts=True,
                )
                existing_images = dict(TourImage.objects.filter(sha256__in=list(image_hashes)).values_list("sha256", "id"))

            for tour, image_hash in zip(tours, self.pending_image_hashes, strict=False):
                tour.main_image_id = existing_images.get(image_hash) if image_hash else None

        if self.pending_embed_texts:
            embedder = get_embedder()
            try:
                vectors = embedder.embed_texts(self.pending_embed_texts)
                for tour, vec in zip(tours, vectors, strict=False):
                    tour.embedding = vec
            except Exception as exc:
                self.log(f"WARNING: embeddings skipped for batch: {exc}")

        with transaction.atomic():
            Tour.objects.bulk_create(tours, ignore_conflicts=True)

            created = {
                t.request_url: t.id
                for t in Tour.objects.filter(request_url__in=request_urls).only("id", "request_url")
            }

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
            for tour, slugs in zip(tours, self.pending_amenities, strict=False):
                tour_id = created.get(tour.request_url)
                if not tour_id:
                    continue
                for slug in slugs:
                    amenity_id = slug_to_id.get(slug)
                    if amenity_id:
                        rels.append(through(tour_id=tour_id, amenity_id=amenity_id))

            if rels:
                through.objects.bulk_create(rels, ignore_conflicts=True)

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
