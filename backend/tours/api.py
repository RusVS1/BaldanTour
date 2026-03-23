from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema
from pgvector.django import CosineDistance
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .embeddings import get_embedder
from .models import Favorite, Tour

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
    return date.fromisoformat(value)


def _parse_int(value: str | None) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    return int(value)


def _hotel_name_from_base_link(base_link: str | None) -> str:
    if not base_link:
        return ""
    path = urlparse(base_link).path.strip("/")
    return path.split("/")[-1] if path else ""


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
    hotel_slug = serializers.CharField()
    hotel_name = serializers.CharField()
    hotel_rating = serializers.CharField(allow_blank=True)
    hotel_type = serializers.CharField(allow_blank=True, allow_null=True)
    meal = serializers.CharField(allow_blank=True, allow_null=True)
    meal_extension = serializers.CharField(allow_blank=True)
    main_image_url = serializers.CharField(allow_blank=True, allow_null=True)
    price_per_person = serializers.IntegerField(allow_null=True)
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


class TourSearchAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TourSearchEnvelopeSerializer

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

        sort = (params.get("sort") or "price_asc").strip()
        if sort not in self.SORT_MAP:
            sort = "price_asc"

        page = max(int(params.get("page") or 1), 1)
        page_size = int(params.get("page_size") or 50)
        page_size = min(max(page_size, 1), 500)

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
                    "hotel_slug": _hotel_name_from_base_link(tour.base_link),
                    "hotel_name": tour.hotel_name or _hotel_name_from_base_link(tour.base_link),
                    "hotel_rating": tour.hotel_rating or "",
                    "hotel_type": tour.hotel_type or None,
                    "meal": tour.meal or None,
                    "meal_extension": _meal_extension(tour.meal),
                    "main_image_url": tour.main_image.url if tour.main_image else None,
                    "price_per_person": price_per_person,
                    "buy_link": tour.booking_link,
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
        values = (
            Tour.objects.exclude(meal="")
            .order_by("meal")
            .values_list("meal", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": v, "value": v} for v in values]})


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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

        values = (
            Tour.objects.filter(favorites__user_id=user_id)
            .exclude(meal="")
            .order_by("meal")
            .values_list("meal", flat=True)
            .distinct()
        )
        return Response({"values": [{"label": v, "value": v} for v in values]})


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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

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
            OpenApiParameter("townfrom", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("country_slug", OpenApiTypes.STR, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("departure_from", OpenApiTypes.DATE, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("departure_to", OpenApiTypes.DATE, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("nights_min", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("nights_max", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("child", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter("adult", OpenApiTypes.INT, required=False, location=OpenApiParameter.QUERY),
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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

        params = request.query_params

        townfrom_in = (params.get("townfrom") or "").strip() or None
        country_in = (params.get("country_slug") or params.get("country") or "").strip() or None

        departure_from = _parse_date(params.get("departure_from") or params.get("checkin_from"))
        departure_to = _parse_date(params.get("departure_to") or params.get("checkin_to"))

        nights_min = _parse_int(params.get("nights_min"))
        nights_max = _parse_int(params.get("nights_max"))
        child = _parse_int(params.get("child"))
        adult = _parse_int(params.get("adult"))

        rest_type = (params.get("rest_type") or "").strip() or None
        hotel_type = (params.get("hotel_type") or "").strip() or None
        meal = (params.get("meal") or "").strip() or None

        hotel_category = None
        if (params.get("hotel_category") or "").strip():
            hotel_category = _parse_int(params.get("hotel_category"))

        sort = (params.get("sort") or "price_asc").strip()
        if sort not in TourSearchAPI.SORT_MAP:
            sort = "price_asc"

        page = max(int(params.get("page") or 1), 1)
        page_size = int(params.get("page_size") or 50)
        page_size = min(max(page_size, 1), 500)

        townfrom_value = _value_from_label(townfrom_in or "", TOWNFROM_SLUG_TO_RU) if townfrom_in else None
        country_value = _value_from_label(country_in or "", COUNTRY_SLUG_TO_RU) if country_in else None
        townfrom_label = _label_from_value(townfrom_in or "", TOWNFROM_SLUG_TO_RU) if townfrom_in else None
        country_label = _label_from_value(country_in or "", COUNTRY_SLUG_TO_RU) if country_in else None

        qs = Tour.objects.filter(favorites__user_id=user_id)

        if townfrom_in:
            qs = qs.filter(Q(townfrom__iexact=townfrom_value) | Q(townfrom_ru__iexact=townfrom_label))
        if country_in:
            qs = qs.filter(Q(country_slug__iexact=country_value) | Q(country_ru__iexact=country_label))
        if adult is not None:
            qs = qs.filter(adult=adult)
        if child is not None:
            qs = qs.filter(child=child)
        if nights_min is not None:
            qs = qs.filter(nights__gte=nights_min)
        if nights_max is not None:
            qs = qs.filter(nights__lte=nights_max)
        if departure_to is not None:
            qs = qs.filter(checkin_beg__lte=departure_to)
        if departure_from is not None:
            qs = qs.filter(checkin_end__gte=departure_from)

        if rest_type:
            qs = qs.filter(rest_type__iexact=rest_type)
        if hotel_type:
            qs = qs.filter(hotel_type__iexact=hotel_type)
        if hotel_category is not None:
            qs = qs.filter(hotel_category=hotel_category)
        if meal:
            qs = qs.filter(meal__iexact=meal)

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
            "departure_from": departure_from.isoformat() if departure_from else None,
            "departure_to": departure_to.isoformat() if departure_to else None,
            "nights_min": nights_min,
            "nights_max": nights_max,
            "child": child,
            "adult": adult,
            "rest_type": rest_type,
            "hotel_type": hotel_type,
            "hotel_category": hotel_category,
            "meal": meal,
            "sort": sort,
        }

        results = []
        for tour in tours:
            resolved_meta = dict(requested_meta)
            if resolved_meta["townfrom"] is None:
                resolved_meta["townfrom"] = (tour.townfrom_ru or "").strip() or _label_from_value(tour.townfrom or "", TOWNFROM_SLUG_TO_RU)
                resolved_meta["townfrom_value"] = (tour.townfrom or "").strip() or None
            if resolved_meta["country_slug"] is None:
                resolved_meta["country_slug"] = (tour.country_ru or "").strip() or _label_from_value(tour.country_slug or "", COUNTRY_SLUG_TO_RU)
                resolved_meta["country_value"] = (tour.country_slug or "").strip() or None
            if resolved_meta["departure_from"] is None and tour.checkin_beg:
                resolved_meta["departure_from"] = tour.checkin_beg.isoformat()
            if resolved_meta["departure_to"] is None and tour.checkin_end:
                resolved_meta["departure_to"] = tour.checkin_end.isoformat()
            if resolved_meta["nights_min"] is None and tour.nights is not None:
                resolved_meta["nights_min"] = tour.nights
            if resolved_meta["nights_max"] is None and tour.nights is not None:
                resolved_meta["nights_max"] = tour.nights
            if resolved_meta["child"] is None:
                resolved_meta["child"] = tour.child
            if resolved_meta["adult"] is None:
                resolved_meta["adult"] = tour.adult
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
                    "hotel_slug": _hotel_name_from_base_link(tour.base_link),
                    "hotel_name": tour.hotel_name or _hotel_name_from_base_link(tour.base_link),
                    "hotel_rating": tour.hotel_rating or "",
                    "hotel_type": tour.hotel_type or None,
                    "meal": tour.meal or None,
                    "meal_extension": _meal_extension(tour.meal),
                    "main_image_url": tour.main_image.url if tour.main_image else None,
                    "price_per_person": price_per_person,
                    "buy_link": tour.booking_link,
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
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

        User = get_user_model()
        User.objects.get(id=user_id)
        Tour.objects.get(id=tour_id)
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
    query = serializers.CharField()
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)


class AISearchMetaSerializer(serializers.Serializer):
    query = serializers.CharField()
    limit = serializers.IntegerField()
    count = serializers.IntegerField()
    embedding_provider = serializers.CharField()
    embedding_model = serializers.CharField(allow_blank=True)
    embedding_dim = serializers.IntegerField()


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

    # Pricing
    price_total = serializers.IntegerField(allow_null=True)
    price_text = serializers.CharField(allow_blank=True)
    price_per_person = serializers.IntegerField(allow_null=True)

    meal = serializers.CharField(allow_blank=True, allow_null=True)
    meal_extension = serializers.CharField(allow_blank=True)

    main_image_url = serializers.CharField(allow_blank=True, allow_null=True)
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
                value={"query": "Абхазия, отель для детей, завтрак", "limit": 5},
                request_only=True,
            ),
            OpenApiExample(
                "Response example",
                value={
                    "meta": {"query": "Абхазия, отель для детей, завтрак", "limit": 5, "count": 1},
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
        limit = int(req.validated_data.get("limit") or 50)

        if not query:
            return Response({"error": "empty_query"}, status=status.HTTP_400_BAD_REQUEST)

        embedder = get_embedder()
        try:
            qvec = embedder.embed_texts([query])[0]
        except Exception as e:
            return Response({"error": "embedding_failed", "details": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        qs = (
            Tour.objects.exclude(embedding__isnull=True)
            .annotate(distance=CosineDistance("embedding", qvec))
            .order_by("distance", "id")
            .select_related("common_description", "target_description", "answer_description", "main_image")
            .prefetch_related("amenities")
        )

        tours = list(qs[:limit])
        results = []
        for t in tours:
            distance = float(getattr(t, "distance", 0.0) or 0.0)
            score = max(0.0, 1.0 - distance)
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
                    "price_total": t.price_value,
                    "price_text": t.price_text or "",
                    "hotel_type": t.hotel_type or None,
                    "meal": t.meal or None,
                    "meal_extension": _meal_extension(t.meal),
                    "main_image_url": t.main_image.url if t.main_image else None,
                    "price_per_person": price_per_person,
                    "buy_link": t.booking_link,
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

        return Response(
            {
                "meta": {
                    "query": query,
                    "limit": limit,
                    "count": len(results),
                    "embedding_provider": embedder.provider,
                    "embedding_model": embedding_model,
                    "embedding_dim": embedder.dim,
                },
                "results": results,
            }
        )
