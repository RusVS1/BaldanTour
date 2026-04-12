from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema
from pgvector.django import CosineDistance
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .embeddings import get_embedder
from .models import Favorite, Tour
from .reranker import get_reranker

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
    # legacy aliases
    "moskva": "Москва",
    "moscow": "Москва",
    "spb": "Санкт-Петербург",
}


def _to_ru_label(value: str, mapping: dict[str, str]) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if any("А" <= ch <= "я" or ch in ("Ё", "ё") for ch in v):
        return v
    return mapping.get(v, v)


def _parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _bad_request(error: str, field: str | None = None) -> Response:
    payload = {"error": error}
    if field:
        payload["field"] = field
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


def _parse_page_params(params) -> tuple[int, int, Response | None]:
    page_raw = params.get("page")
    page_size_raw = params.get("page_size")
    page = _parse_int(page_raw) if page_raw not in (None, "") else 1
    page_size = _parse_int(page_size_raw) if page_size_raw not in (None, "") else 50
    if page is None or page < 1:
        return 1, 50, _bad_request("invalid_integer", "page")
    if page_size is None or page_size < 1:
        return 1, 50, _bad_request("invalid_integer", "page_size")
    return page, min(page_size, 100), None


QUERY_LIMIT = 500
AI_DEFAULT_LIMIT = 10
AI_MAX_LIMIT = 20
AI_CANDIDATE_LIMIT = 80

COUNTRY_QUERY_ALIASES = {
    "турция": "turkey",
    "турции": "turkey",
    "турцию": "turkey",
    "turkey": "turkey",
    "египет": "egypt",
    "египта": "egypt",
    "egypt": "egypt",
    "таиланд": "thailand",
    "тайланд": "thailand",
    "thailand": "thailand",
    "оаэ": "uae",
    "эмираты": "uae",
    "uae": "uae",
    "абхазия": "abkhazia",
    "абхазию": "abkhazia",
    "abkhazia": "abkhazia",
    "беларусь": "belarus",
    "беларуси": "belarus",
    "belarus": "belarus",
    "азербайджан": "azerbaijan",
    "азербайджане": "azerbaijan",
    "azerbaijan": "azerbaijan",
    "узбекистан": "uzbekistan",
    "узбекистане": "uzbekistan",
    "uzbekistan": "uzbekistan",
}

TOWN_QUERY_ALIASES = {
    "москва": "moskva",
    "москвы": "moskva",
    "moscow": "moskva",
    "moskva": "moskva",
    "санкт-петербург": "sankt-peterburg",
    "петербург": "sankt-peterburg",
    "spb": "sankt-peterburg",
}

MEAL_QUERY_ALIASES = {
    "все включено": "AI",
    "всё включено": "AI",
    "all inclusive": "AI",
    "завтрак": "BB",
    "завтраки": "BB",
    "без питания": "RO",
    "полупансион": "HB",
    "полный пансион": "FB",
}


def _detect_query_filters(query: str) -> dict[str, str]:
    q = " ".join((query or "").lower().replace("ё", "е").split())
    detected: dict[str, str] = {}
    for token, slug in COUNTRY_QUERY_ALIASES.items():
        if token in q:
            detected["country_slug"] = slug
            break
    for token, slug in TOWN_QUERY_ALIASES.items():
        if token in q:
            detected["townfrom"] = slug
            break
    for token, meal in MEAL_QUERY_ALIASES.items():
        if token in q:
            detected["meal"] = meal
            break
    if any(token in q for token in ("пляж", "море", "берег")):
        detected["rest_type"] = "пляжный"
    if any(token in q for token in ("ребен", "деть", "семей")):
        detected["hotel_type"] = "для детей"
    return detected


def _tour_ai_text(tour: Tour) -> str:
    return " ".join(
        part
        for part in [
            tour.hotel_name,
            tour.country_ru,
            tour.country_slug,
            tour.townfrom_ru,
            tour.townfrom,
            tour.hotel_type,
            tour.rest_type,
            tour.meal,
            _meal_extension(tour.meal),
            tour.room,
            tour.placement,
            _text_content(tour.common_description)[:1200],
            _text_content(tour.target_description)[:1200],
            _text_content(tour.answer_description)[:1200],
            (tour.raw_text or "")[:1200],
        ]
        if part
    )


def _hotel_name_from_base_link(base_link: str | None) -> str:
    if not base_link:
        return ""
    path = urlparse(base_link).path.strip("/")
    return path.split("/")[-1] if path else ""


def _booking_url_for_tour(tour: Tour) -> str | None:
    url = (tour.booking_link or "").strip()
    if not url:
        return None
    path = urlparse(url).path.lower()
    # Parser may keep synthetic /tours/...#offer links internally to deduplicate
    # offers, but the public API should expose only real booking links.
    if "/booking/" not in path:
        return None
    return url


def _description_for_tour(tour: Tour) -> str:
    # Backward-compatible single "description" (if needed somewhere)
    return (tour.raw_text or "").strip()


def _text_content(text: object | None) -> str:
    return (getattr(text, "content", "") or "").strip()


MEAL_EXTENSION_MAP = {
    "RO": "Без питания",
    "BB": "Завтрак",
    "HB": "Полупансион",
    "FB": "Полный пансион",
    "AI": "Все включено",
    "UAI": "Все включено + импортные продукты",
    "HB+": "Расширенный полупансион",
    "FB+": "Расширенный полный пансион",
}


def _meal_extension(meal: str | None) -> str:
    code = (meal or "").strip()
    if not code:
        return ""
    code = code.upper()
    return MEAL_EXTENSION_MAP.get(code, "")


def _looks_cyrillic(value: str) -> bool:
    return any("А" <= ch <= "я" or ch in ("Ё", "ё") for ch in (value or ""))


def _value_from_label(value_or_label: str, mapping: dict[str, str]) -> str:
    """
    Returns "value" (slug/code) even if user passed a Russian label.
    If the value is unknown, returns the original string.
    """
    v = (value_or_label or "").strip()
    if not v:
        return ""
    if not _looks_cyrillic(v):
        return v
    for slug, label in mapping.items():
        if (label or "").strip().lower() == v.lower():
            return slug
    return v


def _label_from_value(value_or_label: str, mapping: dict[str, str]) -> str:
    v = (value_or_label or "").strip()
    if not v:
        return ""
    if _looks_cyrillic(v):
        return v
    return mapping.get(v, v)


@dataclass(frozen=True)
class TourSearchParams:
    townfrom: str
    country_slug: str
    departure_from: date
    departure_to: date
    nights_min: int
    nights_max: int
    child: int
    adult: int
    rest_type: str | None
    hotel_type: str | None
    hotel_category: int | None
    meal: str | None
    sort: str
    page: int
    page_size: int


class TourSearchResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    base_link = serializers.CharField(allow_blank=True, allow_null=True)
    hotel_slug = serializers.CharField()
    hotel_name = serializers.CharField()
    hotel_rating = serializers.CharField(allow_blank=True)
    trip_dates = serializers.CharField(allow_blank=True)
    departure_from = serializers.DateField(allow_null=True)
    departure_to = serializers.DateField(allow_null=True)
    nights = serializers.IntegerField(allow_null=True)
    hotel_type = serializers.CharField(allow_blank=True, allow_null=True)
    meal = serializers.CharField(allow_blank=True, allow_null=True)
    meal_extension = serializers.CharField(allow_blank=True)
    main_image_url = serializers.CharField(allow_blank=True, allow_null=True)
    price_per_person = serializers.IntegerField(allow_null=True)
    booking_url = serializers.CharField(allow_blank=True, allow_null=True)
    buy_link = serializers.CharField(allow_blank=True, allow_null=True)
    common_description = serializers.CharField(allow_blank=True)
    target_description = serializers.CharField(allow_blank=True)
    answer_description = serializers.CharField(allow_blank=True)
    meta = serializers.DictField()


class TourSearchMetaRequestedSerializer(serializers.Serializer):
    townfrom = serializers.CharField()
    country_slug = serializers.CharField()
    townfrom_value = serializers.CharField()
    country_value = serializers.CharField()
    departure_from = serializers.DateField()
    departure_to = serializers.DateField()
    nights_min = serializers.IntegerField()
    nights_max = serializers.IntegerField()
    child = serializers.IntegerField()
    adult = serializers.IntegerField()
    rest_type = serializers.CharField(allow_null=True, required=False)
    hotel_type = serializers.CharField(allow_null=True, required=False)
    hotel_category = serializers.IntegerField(allow_null=True, required=False)
    meal = serializers.CharField(allow_null=True, required=False)
    sort = serializers.CharField()


class TourSearchMetaSerializer(serializers.Serializer):
    requested = TourSearchMetaRequestedSerializer()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    count = serializers.IntegerField()


class TourSearchEnvelopeSerializer(serializers.Serializer):
    meta = TourSearchMetaSerializer()
    results = TourSearchResponseSerializer(many=True)


class ValuesStringEnvelopeSerializer(serializers.Serializer):
    values = serializers.ListField(child=serializers.CharField())


class ValuesIntEnvelopeSerializer(serializers.Serializer):
    values = serializers.ListField(child=serializers.IntegerField())


class FilterOptionSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()


class FilterOptionIntSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.IntegerField()


class ValuesOptionsEnvelopeSerializer(serializers.Serializer):
    values = FilterOptionSerializer(many=True)


class ValuesOptionsIntEnvelopeSerializer(serializers.Serializer):
    values = FilterOptionIntSerializer(many=True)


class OkEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField()


class HealthAPI(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OkEnvelopeSerializer)
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return Response({"ok": True})


class TourSearchAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TourSearchEnvelopeSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "search"

    SORT_MAP = {
        "price_desc": ["-price_value", "id"],
        "price_asc": ["price_value", "id"],
        "hotel_category": ["hotel_category", "price_value", "id"],
        "hotel_type": ["hotel_type", "price_value", "id"],
        "rest_type": ["rest_type", "price_value", "id"],
        "meal": ["meal", "price_value", "id"],
    }

    @extend_schema(
        parameters=[
            OpenApiParameter("townfrom", OpenApiTypes.STR, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("country_slug", OpenApiTypes.STR, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("departure_from", OpenApiTypes.DATE, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("departure_to", OpenApiTypes.DATE, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("nights_min", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("nights_max", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("child", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("adult", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("rest_type", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("hotel_type", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("hotel_category", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("meal", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                "sort",
                OpenApiTypes.STR,
                required=False,
                location=OpenApiParameter.QUERY,
                description="price_desc|price_asc|hotel_category|hotel_type|rest_type|meal",
            ),
            OpenApiParameter("page", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
        ],
        responses=TourSearchEnvelopeSerializer,
    )
    def get(self, request):
        params = request.query_params

        townfrom_in = (params.get("townfrom") or "").strip()
        country_in = (params.get("country_slug") or params.get("country") or "").strip()

        townfrom_value = _value_from_label(townfrom_in, TOWNFROM_SLUG_TO_RU)
        country_value = _value_from_label(country_in, COUNTRY_SLUG_TO_RU)

        townfrom_label = _label_from_value(townfrom_in, TOWNFROM_SLUG_TO_RU)
        country_label = _label_from_value(country_in, COUNTRY_SLUG_TO_RU)

        departure_from = _parse_date(params.get("departure_from") or params.get("checkin_from"))
        departure_to = _parse_date(params.get("departure_to") or params.get("checkin_to"))

        nights_min = _parse_int(params.get("nights_min"))
        nights_max = _parse_int(params.get("nights_max"))
        child = _parse_int(params.get("child"))
        adult = _parse_int(params.get("adult"))

        missing = []
        if not townfrom_in:
            missing.append("townfrom")
        if not country_in:
            missing.append("country_slug")
        if departure_from is None:
            missing.append("departure_from")
        if departure_to is None:
            missing.append("departure_to")
        if nights_min is None:
            missing.append("nights_min")
        if nights_max is None:
            missing.append("nights_max")
        if child is None:
            missing.append("child")
        if adult is None:
            missing.append("adult")

        if missing:
            return Response(
                {"error": "missing_required_params", "missing": missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rest_type = (params.get("rest_type") or "").strip() or None
        hotel_type = (params.get("hotel_type") or "").strip() or None
        meal = (params.get("meal") or "").strip() or None

        hotel_category = None
        if (params.get("hotel_category") or "").strip():
            hotel_category = _parse_int(params.get("hotel_category"))
            if hotel_category is None:
                return _bad_request("invalid_integer", "hotel_category")

        sort = (params.get("sort") or "price_asc").strip()
        if sort not in self.SORT_MAP:
            return _bad_request("invalid_sort", "sort")

        page, page_size, page_error = _parse_page_params(params)
        if page_error is not None:
            return page_error

        price_from = _parse_int(params.get("price_from") or params.get("price_min"))
        price_to = _parse_int(params.get("price_to") or params.get("price_max"))
        if (params.get("price_from") or params.get("price_min")) and price_from is None:
            return _bad_request("invalid_integer", "price_from")
        if (params.get("price_to") or params.get("price_max")) and price_to is None:
            return _bad_request("invalid_integer", "price_to")
        if price_from is not None and price_from < 0:
            return _bad_request("negative_price", "price_from")
        if price_to is not None and price_to < 0:
            return _bad_request("negative_price", "price_to")

        search_params = TourSearchParams(
            townfrom=townfrom_in,
            country_slug=country_in,
            departure_from=departure_from,
            departure_to=departure_to,
            nights_min=nights_min,
            nights_max=nights_max,
            child=child,
            adult=adult,
            rest_type=rest_type,
            hotel_type=hotel_type,
            hotel_category=hotel_category,
            meal=meal,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        qs = Tour.objects.all()
        qs = qs.filter(
            (Q(townfrom__iexact=townfrom_value) | Q(townfrom_ru__iexact=townfrom_label))
            & (Q(country_slug__iexact=country_value) | Q(country_ru__iexact=country_label))
        )
        qs = qs.filter(adult=adult, child=child)
        qs = qs.filter(nights__gte=nights_min, nights__lte=nights_max)
        qs = qs.filter(checkin_beg__lte=departure_to, checkin_end__gte=departure_from)

        if rest_type:
            qs = qs.filter(rest_type__iexact=rest_type)
        if hotel_type:
            qs = qs.filter(hotel_type__iexact=hotel_type)
        if hotel_category is not None:
            qs = qs.filter(hotel_category=hotel_category)
        if meal:
            qs = qs.filter(meal__iexact=meal)
        if price_from is not None:
            qs = qs.filter(price_value__gte=price_from * max(adult, 1))
        if price_to is not None:
            qs = qs.filter(price_value__lte=price_to * max(adult, 1))

        qs = qs.order_by(*self.SORT_MAP[sort])
        qs = qs.select_related("common_description", "target_description", "answer_description", "main_image")

        total = qs.count()
        offset = (page - 1) * page_size
        tours = list(qs[offset : offset + page_size])

        requested_meta = {
            # Keep backward-compatible keys (RU labels) + explicit value fields (slugs).
            "townfrom": townfrom_label,
            "country_slug": country_label,
            "townfrom_value": townfrom_value,
            "country_value": country_value,
            "departure_from": departure_from.isoformat(),
            "departure_to": departure_to.isoformat(),
            "nights_min": nights_min,
            "nights_max": nights_max,
            "child": child,
            "adult": adult,
            "rest_type": rest_type,
            "hotel_type": hotel_type,
            "hotel_category": hotel_category,
            "meal": meal,
            "sort": sort,
            "price_from": price_from,
            "price_to": price_to,
        }

        results = []
        for tour in tours:
            resolved_meta = dict(requested_meta)
            if resolved_meta["rest_type"] is None:
                resolved_meta["rest_type"] = tour.rest_type or None
            if resolved_meta["hotel_type"] is None:
                resolved_meta["hotel_type"] = tour.hotel_type or None
            if resolved_meta["hotel_category"] is None:
                resolved_meta["hotel_category"] = tour.hotel_category
            if resolved_meta["meal"] is None:
                resolved_meta["meal"] = tour.meal or None

            price_per_person = None
            if tour.price_value is not None and tour.adult:
                price_per_person = int(tour.price_value // max(tour.adult, 1))

            results.append(
                {
                    "id": tour.id,
                    "base_link": tour.base_link,
                    "hotel_slug": _hotel_name_from_base_link(tour.base_link),
                    "hotel_name": tour.hotel_name or _hotel_name_from_base_link(tour.base_link),
                    "hotel_rating": tour.hotel_rating or "",
                    "trip_dates": tour.trip_dates or "",
                    "departure_from": tour.checkin_beg.isoformat() if tour.checkin_beg else None,
                    "departure_to": tour.checkin_end.isoformat() if tour.checkin_end else None,
                    "nights": tour.nights,
                    "hotel_type": tour.hotel_type or None,
                    "meal": tour.meal or None,
                    "meal_extension": _meal_extension(tour.meal),
                    "main_image_url": tour.main_image.url if tour.main_image else None,
                    "price_per_person": price_per_person,
                    "booking_url": _booking_url_for_tour(tour),
                    "buy_link": _booking_url_for_tour(tour),
                    "common_description": _text_content(tour.common_description),
                    "target_description": _text_content(tour.target_description),
                    "answer_description": _text_content(tour.answer_description),
                    "meta": resolved_meta,
                }
            )

        return Response(
            {
                "meta": {
                    "requested": requested_meta,
                    "page": page,
                    "page_size": page_size,
                    "count": total,
                },
                "results": results,
            }
        )


class FilterRestTypeAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(responses=ValuesOptionsEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(rest_type="")
            .order_by("rest_type")
            .values_list("rest_type", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": v, "value": v} for v in values]})


class FilterHotelTypeAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(responses=ValuesOptionsEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(hotel_type="")
            .order_by("hotel_type")
            .values_list("hotel_type", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": v, "value": v} for v in values]})


class FilterMealAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(responses=ValuesOptionsEnvelopeSerializer)
    def get(self, request):
        values = list(
            Tour.objects.exclude(meal="")
            .order_by("meal")
            .values_list("meal", flat=True)
            .distinct()
        )
        seen: set[str] = set()
        options = []
        for v in values:
            code = (v or "").strip()
            if not code:
                continue
            code = code.upper()
            if code in seen:
                continue
            seen.add(code)

            ext = _meal_extension(code)
            label = f"{ext} ({code})" if ext else code
            options.append({"label": label, "value": code})

        return Response({"values": options})


class FilterTownFromAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(responses=ValuesOptionsEnvelopeSerializer)
    def get(self, request):
        pairs = (
            Tour.objects.exclude(townfrom="")
            .exclude(townfrom_ru="")
            .order_by("townfrom_ru", "townfrom")
            .values_list("townfrom_ru", "townfrom")
            .distinct()
        )
        return Response({"values": [{"label": label, "value": value} for (label, value) in pairs]})


class FilterCountryAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(responses=ValuesOptionsEnvelopeSerializer)
    def get(self, request):
        pairs = (
            Tour.objects.exclude(country_slug="")
            .exclude(country_ru="")
            .order_by("country_ru", "country_slug")
            .values_list("country_ru", "country_slug")
            .distinct()
        )
        return Response({"values": [{"label": label, "value": value} for (label, value) in pairs]})


class FilterHotelCategoryAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesOptionsIntEnvelopeSerializer

    @extend_schema(responses=ValuesOptionsIntEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(hotel_category__isnull=True)
            .order_by("hotel_category")
            .values_list("hotel_category", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": str(v), "value": v} for v in values]})


def _check_favorites_access(request, user_id: int) -> None:
    if request.user.is_staff or request.user.is_superuser:
        return
    if request.user.id != user_id:
        raise serializers.ValidationError("Forbidden.")


class FavoriteFilterRestTypeAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=ValuesOptionsEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            _check_favorites_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        values = (
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(rest_type="")
            .order_by("rest_type")
            .values_list("rest_type", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": v, "value": v} for v in values]})


class FavoriteFilterHotelTypeAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=ValuesOptionsEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            _check_favorites_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        values = (
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(hotel_type="")
            .order_by("hotel_type")
            .values_list("hotel_type", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": v, "value": v} for v in values]})


class FavoriteFilterMealAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=ValuesOptionsEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            _check_favorites_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        values = list(
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(meal="")
            .order_by("meal")
            .values_list("meal", flat=True)
            .distinct()
        )
        seen: set[str] = set()
        options = []
        for v in values:
            code = (v or "").strip()
            if not code:
                continue
            code = code.upper()
            if code in seen:
                continue
            seen.add(code)

            ext = _meal_extension(code)
            label = f"{ext} ({code})" if ext else code
            options.append({"label": label, "value": code})

        return Response({"values": options})


class FavoriteFilterTownFromAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=ValuesOptionsEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            _check_favorites_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        pairs = (
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(townfrom="")
            .exclude(townfrom_ru="")
            .order_by("townfrom_ru", "townfrom")
            .values_list("townfrom_ru", "townfrom")
            .distinct()
        )
        return Response({"values": [{"label": label, "value": value} for (label, value) in pairs]})


class FavoriteFilterCountryAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ValuesOptionsEnvelopeSerializer

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=ValuesOptionsEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            _check_favorites_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        pairs = (
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(country_slug="")
            .exclude(country_ru="")
            .order_by("country_ru", "country_slug")
            .values_list("country_ru", "country_slug")
            .distinct()
        )
        return Response({"values": [{"label": label, "value": value} for (label, value) in pairs]})


class FavoriteFilterHotelCategoryAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ValuesOptionsIntEnvelopeSerializer

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=ValuesOptionsIntEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            _check_favorites_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        values = (
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(hotel_category__isnull=True)
            .order_by("hotel_category")
            .values_list("hotel_category", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": str(v), "value": v} for v in values]})


class FavoriteAddRequestSerializer(serializers.Serializer):
    tour_id = serializers.IntegerField()


class FavoriteMetaSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    requested = serializers.DictField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    count = serializers.IntegerField()


class FavoriteEnvelopeSerializer(serializers.Serializer):
    meta = FavoriteMetaSerializer()
    results = TourSearchResponseSerializer(many=True)


class FavoriteToursAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FavoriteEnvelopeSerializer

    def _check_access(self, request, user_id: int) -> None:
        _check_favorites_access(request, user_id)

    @extend_schema(
        parameters=[
            OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH),
            OpenApiParameter("townfrom", OpenApiTypes.STR, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("country_slug", OpenApiTypes.STR, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("departure_from", OpenApiTypes.DATE, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("departure_to", OpenApiTypes.DATE, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("nights_min", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("nights_max", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("child", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("adult", OpenApiTypes.INT, required=True, location=OpenApiParameter.QUERY),
            OpenApiParameter("rest_type", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("hotel_type", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("hotel_category", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("meal", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                "sort",
                OpenApiTypes.STR,
                required=False,
                location=OpenApiParameter.QUERY,
                description="price_desc|price_asc|hotel_category|hotel_type|rest_type|meal",
            ),
            OpenApiParameter("page", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
        ],
        responses=FavoriteEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            self._check_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        params = request.query_params

        townfrom_in = (params.get("townfrom") or "").strip()
        country_in = (params.get("country_slug") or params.get("country") or "").strip()

        departure_from = _parse_date(params.get("departure_from") or params.get("checkin_from"))
        departure_to = _parse_date(params.get("departure_to") or params.get("checkin_to"))

        nights_min = _parse_int(params.get("nights_min"))
        nights_max = _parse_int(params.get("nights_max"))
        child = _parse_int(params.get("child"))
        adult = _parse_int(params.get("adult"))

        missing = []
        if not townfrom_in:
            missing.append("townfrom")
        if not country_in:
            missing.append("country_slug")
        if departure_from is None:
            missing.append("departure_from")
        if departure_to is None:
            missing.append("departure_to")
        if nights_min is None:
            missing.append("nights_min")
        if nights_max is None:
            missing.append("nights_max")
        if child is None:
            missing.append("child")
        if adult is None:
            missing.append("adult")

        if missing:
            return Response(
                {"error": "missing_required_params", "missing": missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rest_type = (params.get("rest_type") or "").strip() or None
        hotel_type = (params.get("hotel_type") or "").strip() or None
        meal = (params.get("meal") or "").strip() or None

        hotel_category = None
        if (params.get("hotel_category") or "").strip():
            hotel_category = _parse_int(params.get("hotel_category"))
            if hotel_category is None:
                return _bad_request("invalid_integer", "hotel_category")

        sort = (params.get("sort") or "price_asc").strip()
        if sort not in TourSearchAPI.SORT_MAP:
            return _bad_request("invalid_sort", "sort")

        page, page_size, page_error = _parse_page_params(params)
        if page_error is not None:
            return page_error

        price_from = _parse_int(params.get("price_from") or params.get("price_min"))
        price_to = _parse_int(params.get("price_to") or params.get("price_max"))
        if (params.get("price_from") or params.get("price_min")) and price_from is None:
            return _bad_request("invalid_integer", "price_from")
        if (params.get("price_to") or params.get("price_max")) and price_to is None:
            return _bad_request("invalid_integer", "price_to")
        if price_from is not None and price_from < 0:
            return _bad_request("negative_price", "price_from")
        if price_to is not None and price_to < 0:
            return _bad_request("negative_price", "price_to")

        townfrom_value = _value_from_label(townfrom_in, TOWNFROM_SLUG_TO_RU)
        country_value = _value_from_label(country_in, COUNTRY_SLUG_TO_RU)
        townfrom_label = _label_from_value(townfrom_in, TOWNFROM_SLUG_TO_RU)
        country_label = _label_from_value(country_in, COUNTRY_SLUG_TO_RU)

        qs = Tour.objects.filter(favorites__user_id=user_id)

        qs = qs.filter(
            (Q(townfrom__iexact=townfrom_value) | Q(townfrom_ru__iexact=townfrom_label))
            & (Q(country_slug__iexact=country_value) | Q(country_ru__iexact=country_label))
        )
        qs = qs.filter(adult=adult, child=child)
        qs = qs.filter(nights__gte=nights_min, nights__lte=nights_max)
        qs = qs.filter(checkin_beg__lte=departure_to, checkin_end__gte=departure_from)

        if rest_type:
            qs = qs.filter(rest_type__iexact=rest_type)
        if hotel_type:
            qs = qs.filter(hotel_type__iexact=hotel_type)
        if hotel_category is not None:
            qs = qs.filter(hotel_category=hotel_category)
        if meal:
            qs = qs.filter(meal__iexact=meal)
        if price_from is not None:
            qs = qs.filter(price_value__gte=price_from * max(adult, 1))
        if price_to is not None:
            qs = qs.filter(price_value__lte=price_to * max(adult, 1))

        qs = qs.order_by(*TourSearchAPI.SORT_MAP[sort])
        qs = qs.select_related("common_description", "target_description", "answer_description", "main_image")

        total = qs.count()
        offset = (page - 1) * page_size
        tours = list(qs[offset : offset + page_size])

        requested_meta = {
            "townfrom": townfrom_label,
            "country_slug": country_label,
            "townfrom_value": townfrom_value,
            "country_value": country_value,
            "departure_from": departure_from.isoformat(),
            "departure_to": departure_to.isoformat(),
            "nights_min": nights_min,
            "nights_max": nights_max,
            "child": child,
            "adult": adult,
            "rest_type": rest_type,
            "hotel_type": hotel_type,
            "hotel_category": hotel_category,
            "meal": meal,
            "sort": sort,
            "price_from": price_from,
            "price_to": price_to,
        }

        results = []
        for tour in tours:
            resolved_meta = dict(requested_meta)
            if resolved_meta["rest_type"] is None:
                resolved_meta["rest_type"] = tour.rest_type or None
            if resolved_meta["hotel_type"] is None:
                resolved_meta["hotel_type"] = tour.hotel_type or None
            if resolved_meta["hotel_category"] is None:
                resolved_meta["hotel_category"] = tour.hotel_category
            if resolved_meta["meal"] is None:
                resolved_meta["meal"] = tour.meal or None

            price_per_person = None
            if tour.price_value is not None and tour.adult:
                price_per_person = int(tour.price_value // max(tour.adult, 1))

            results.append(
                {
                    "id": tour.id,
                    "base_link": tour.base_link,
                    "hotel_slug": _hotel_name_from_base_link(tour.base_link),
                    "hotel_name": tour.hotel_name or _hotel_name_from_base_link(tour.base_link),
                    "hotel_rating": tour.hotel_rating or "",
                    "trip_dates": tour.trip_dates or "",
                    "departure_from": tour.checkin_beg.isoformat() if tour.checkin_beg else None,
                    "departure_to": tour.checkin_end.isoformat() if tour.checkin_end else None,
                    "nights": tour.nights,
                    "hotel_type": tour.hotel_type or None,
                    "meal": tour.meal or None,
                    "meal_extension": _meal_extension(tour.meal),
                    "main_image_url": tour.main_image.url if tour.main_image else None,
                    "price_per_person": price_per_person,
                    "booking_url": _booking_url_for_tour(tour),
                    "buy_link": _booking_url_for_tour(tour),
                    "common_description": _text_content(tour.common_description),
                    "target_description": _text_content(tour.target_description),
                    "answer_description": _text_content(tour.answer_description),
                    "meta": resolved_meta,
                }
            )

        return Response(
            {
                "meta": {
                    "user_id": user_id,
                    "requested": requested_meta,
                    "page": page,
                    "page_size": page_size,
                    "count": total,
                },
                "results": results,
            }
        )

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        request=FavoriteAddRequestSerializer,
        responses={201: OkEnvelopeSerializer},
    )
    def post(self, request, user_id: int):
        serializer = FavoriteAddRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tour_id = serializer.validated_data["tour_id"]
        try:
            self._check_access(request, user_id)
        except serializers.ValidationError:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        User = get_user_model()
        if not User.objects.filter(id=user_id).exists() or not Tour.objects.filter(id=tour_id).exists():
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        Favorite.objects.get_or_create(user_id=user_id, tour_id=tour_id)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class FavoriteTourAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH),
            OpenApiParameter("tour_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH),
        ],
        responses={200: OkEnvelopeSerializer},
    )
    def delete(self, request, user_id: int, tour_id: int):
        if not (request.user.is_staff or request.user.is_superuser) and request.user.id != user_id:
            return Response({"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        Favorite.objects.filter(user_id=user_id, tour_id=tour_id).delete()
        return Response({"ok": True})


class AISearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=QUERY_LIMIT)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=AI_MAX_LIMIT)


class AISearchMetaSerializer(serializers.Serializer):
    query = serializers.CharField()
    count = serializers.IntegerField()
    embedding_provider = serializers.CharField()
    embedding_model = serializers.CharField(allow_blank=True)
    embedding_dim = serializers.IntegerField()
    reranker_provider = serializers.CharField(allow_blank=True, required=False)
    reranker_model = serializers.CharField(allow_blank=True, required=False)
    detected_filters = serializers.DictField(required=False)
    missing_embeddings = serializers.IntegerField(required=False)


class AISearchResultSerializer(serializers.Serializer):
    # Same core fields as /api/tours/ + expanded tour details
    id = serializers.IntegerField()
    request_url = serializers.CharField(allow_blank=True)
    base_link = serializers.CharField(allow_blank=True, allow_null=True)

    hotel_slug = serializers.CharField()
    hotel_name = serializers.CharField()
    hotel_rating = serializers.CharField(allow_blank=True)

    room = serializers.CharField(allow_blank=True)
    placement = serializers.CharField(allow_blank=True)
    trip_dates = serializers.CharField(allow_blank=True)
    departure_from = serializers.DateField(allow_null=True)
    departure_to = serializers.DateField(allow_null=True)
    nights = serializers.IntegerField(allow_null=True)

    # Pricing
    price_total = serializers.IntegerField(allow_null=True)
    price_text = serializers.CharField(allow_blank=True)
    price_per_person = serializers.IntegerField(allow_null=True)

    meal = serializers.CharField(allow_blank=True, allow_null=True)
    meal_extension = serializers.CharField(allow_blank=True)

    main_image_url = serializers.CharField(allow_blank=True, allow_null=True)
    booking_url = serializers.CharField(allow_blank=True, allow_null=True)
    buy_link = serializers.CharField(allow_blank=True, allow_null=True)

    common_description = serializers.CharField(allow_blank=True)
    target_description = serializers.CharField(allow_blank=True)
    answer_description = serializers.CharField(allow_blank=True)

    amenities = serializers.ListField(child=serializers.CharField(), required=False)

    meta = serializers.DictField()
    score = serializers.FloatField()


class AISearchEnvelopeSerializer(serializers.Serializer):
    meta = AISearchMetaSerializer()
    results = AISearchResultSerializer(many=True)


class AISearchAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AISearchEnvelopeSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_search"

    @extend_schema(
        tags=["ai"],
        summary="AI semantic search (pgvector)",
        description=(
            "Принимает произвольный текст, строит эмбеддинг и ищет похожие туры по cosine distance в pgvector. "
            "Возвращает туры в том же формате, что и поиск, + поле score."
        ),
        request=AISearchRequestSerializer,
        responses=AISearchEnvelopeSerializer,
        examples=[
            OpenApiExample(
                "Request example",
                value={"query": "Абхазия, отель для детей, завтрак"},
                request_only=True,
            ),
            OpenApiExample(
                "Response example",
                value={
                    "meta": {"query": "Абхазия, отель для детей, завтрак", "count": 1},
                    "results": [
                        {
                            "id": 123,
                            "request_url": "https://anextour.ru/tours/abkhazia/...&TOWNFROM=moskva",
                            "base_link": "https://anextour.ru/tours/abkhazia/a-v-sokol-family-29767",
                            "hotel_slug": "a-v-sokol-family-29767",
                            "hotel_name": "A. V. Sokol Family.",
                            "hotel_rating": "",
                            "room": "Standart",
                            "placement": "",
                            "trip_dates": "28 мар - 30 мар",
                            "price_total": 21635,
                            "price_text": "21 635 ₽",
                            "price_per_person": 21635,
                            "meal": "BB",
                            "meal_extension": "Завтрак",
                            "main_image_url": "https://files.anextour.ru/...",
                            "booking_url": "https://anextour.ru/booking/...",
                            "buy_link": "https://anextour.ru/booking/...",
                            "common_description": "",
                            "target_description": "",
                            "answer_description": "",
                            "amenities": ["wifi", "balcony"],
                            "meta": {
                                "townfrom": "Москва",
                                "country_slug": "Абхазия",
                                "townfrom_value": "moskva",
                                "country_value": "abkhazia",
                                "departure_from": "2026-03-21",
                                "departure_to": "2026-03-28",
                                "nights_min": 1,
                                "nights_max": 8,
                                "child": 0,
                                "adult": 1,
                                "rest_type": None,
                                "hotel_type": "Для детей",
                                "hotel_category": 2,
                                "meal": "BB",
                            },
                            "score": 0.87,
                        }
                    ],
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        req = AISearchRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        query = (req.validated_data["query"] or "").strip()
        limit = req.validated_data.get("limit") or AI_DEFAULT_LIMIT

        if not query:
            return Response({"error": "empty_query"}, status=status.HTTP_400_BAD_REQUEST)

        embedder = get_embedder()
        try:
            qvec = embedder.embed_texts([query])[0]
        except Exception:
            return Response({"error": "embedding_failed"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        detected_filters = _detect_query_filters(query)

        qs = (
            Tour.objects.exclude(embedding__isnull=True)
            .annotate(distance=CosineDistance("embedding", qvec))
            .select_related("common_description", "target_description", "answer_description", "main_image")
            .prefetch_related("amenities")
        )
        if country_slug := detected_filters.get("country_slug"):
            qs = qs.filter(country_slug__iexact=country_slug)
        if townfrom := detected_filters.get("townfrom"):
            qs = qs.filter(townfrom__iexact=townfrom)
        if meal := detected_filters.get("meal"):
            qs = qs.filter(meal__iexact=meal)

        qs = qs.order_by("distance", "id")

        candidates = list(qs[:AI_CANDIDATE_LIMIT])
        reranker = get_reranker()
        reranker_provider = ""
        reranker_model = ""
        reranked_scores: dict[int, float] = {}
        if reranker is not None and candidates:
            try:
                ranked = reranker.rerank(query, candidates, _tour_ai_text)
                candidates = [row.item for row in ranked]
                reranked_scores = {row.item.id: row.score for row in ranked}
                reranker_provider = reranker.provider
                reranker_model = reranker.model_name
            except Exception:
                reranker_provider = "unavailable"
                reranker_model = getattr(reranker, "model_name", "")

        tours = candidates[:limit]
        results = []
        for t in tours:
            distance = float(getattr(t, "distance", 0.0) or 0.0)
            score = max(0.0, 1.0 - distance)
            if t.id in reranked_scores:
                score = reranked_scores[t.id]
            price_per_person = int(t.price_value // max(t.adult, 1)) if t.price_value is not None else None
            results.append(
                {
                    "id": t.id,
                    "request_url": t.request_url or "",
                    "base_link": t.base_link,
                    "hotel_slug": _hotel_name_from_base_link(t.base_link),
                    "hotel_name": t.hotel_name or _hotel_name_from_base_link(t.base_link),
                    "hotel_rating": t.hotel_rating or "",
                    "room": t.room or "",
                    "placement": t.placement or "",
                    "trip_dates": t.trip_dates or "",
                    "departure_from": t.checkin_beg.isoformat() if t.checkin_beg else None,
                    "departure_to": t.checkin_end.isoformat() if t.checkin_end else None,
                    "nights": t.nights,
                    "price_total": t.price_value,
                    "price_text": t.price_text or "",
                    "hotel_type": t.hotel_type or None,
                    "meal": t.meal or None,
                    "meal_extension": _meal_extension(t.meal),
                    "main_image_url": t.main_image.url if t.main_image else None,
                    "price_per_person": price_per_person,
                    "booking_url": _booking_url_for_tour(t),
                    "buy_link": _booking_url_for_tour(t),
                    "common_description": _text_content(t.common_description),
                    "target_description": _text_content(t.target_description),
                    "answer_description": _text_content(t.answer_description),
                    "amenities": [a.slug for a in t.amenities.all()],
                    "meta": {
                        "townfrom": (t.townfrom_ru or "").strip()
                        or _label_from_value(t.townfrom or "", TOWNFROM_SLUG_TO_RU),
                        "country_slug": (t.country_ru or "").strip()
                        or _label_from_value(t.country_slug or "", COUNTRY_SLUG_TO_RU),
                        "townfrom_value": (t.townfrom or "").strip(),
                        "country_value": (t.country_slug or "").strip(),
                        "departure_from": t.checkin_beg.isoformat() if t.checkin_beg else None,
                        "departure_to": t.checkin_end.isoformat() if t.checkin_end else None,
                        "nights_min": t.night_min if t.night_min is not None else t.nights,
                        "nights_max": t.night_max if t.night_max is not None else t.nights,
                        "child": t.child,
                        "adult": t.adult,
                        "rest_type": t.rest_type or None,
                        "hotel_type": t.hotel_type or None,
                        "hotel_category": t.hotel_category,
                        "meal": t.meal or None,
                    },
                    "score": score,
                }
            )

        embedding_model = ""
        if embedder.provider == "openai":
            embedding_model = (os.environ.get("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small").strip()
        elif embedder.provider in ("st", "sentence_transformers", "sentence-transformers"):
            embedding_model = (
                os.environ.get("ST_EMBEDDING_MODEL")
                or os.environ.get("HF_EMBEDDING_MODEL")
                or "intfloat/multilingual-e5-base"
            ).strip()

        return Response(
            {
                "meta": {
                    "query": query,
                    "count": len(results),
                    "embedding_provider": embedder.provider,
                    "embedding_model": embedding_model,
                    "embedding_dim": embedder.dim,
                    "reranker_provider": reranker_provider,
                    "reranker_model": reranker_model,
                    "detected_filters": detected_filters,
                    "missing_embeddings": Tour.objects.filter(embedding__isnull=True).count(),
                },
                "results": results,
            }
        )
