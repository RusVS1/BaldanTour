from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Favorite, Tour


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
    return (tour.description or "").strip() or (tour.raw_text or "").strip()


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
    hotel_name = serializers.CharField()
    price_per_person = serializers.IntegerField(allow_null=True)
    buy_link = serializers.CharField(allow_blank=True, allow_null=True)
    description = serializers.CharField(allow_blank=True)
    meta = serializers.DictField()


class TourSearchMetaRequestedSerializer(serializers.Serializer):
    townfrom = serializers.CharField()
    country_slug = serializers.CharField()
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

        townfrom = (params.get("townfrom") or "").strip()
        country_slug = (params.get("country_slug") or params.get("country") or "").strip()

        departure_from = _parse_date(params.get("departure_from") or params.get("checkin_from"))
        departure_to = _parse_date(params.get("departure_to") or params.get("checkin_to"))

        nights_min = _parse_int(params.get("nights_min"))
        nights_max = _parse_int(params.get("nights_max"))
        child = _parse_int(params.get("child"))
        adult = _parse_int(params.get("adult"))

        missing = []
        if not townfrom:
            missing.append("townfrom")
        if not country_slug:
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
            townfrom=townfrom,
            country_slug=country_slug,
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
        qs = qs.filter(townfrom__iexact=townfrom, country_slug__iexact=country_slug)
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

        total = qs.count()
        offset = (page - 1) * page_size
        tours = list(qs[offset : offset + page_size])

        requested_meta = {
            "townfrom": townfrom,
            "country_slug": country_slug,
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
                    "hotel_name": _hotel_name_from_base_link(tour.base_link),
                    "price_per_person": price_per_person,
                    "buy_link": tour.booking_link,
                    "description": _description_for_tour(tour),
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
    serializer_class = ValuesStringEnvelopeSerializer

    @extend_schema(responses=ValuesStringEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(rest_type="")
            .order_by("rest_type")
            .values_list("rest_type", flat=True)
            .distinct()
        )
        return Response({"values": list(values)})


class FilterHotelTypeAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesStringEnvelopeSerializer

    @extend_schema(responses=ValuesStringEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(hotel_type="")
            .order_by("hotel_type")
            .values_list("hotel_type", flat=True)
            .distinct()
        )
        return Response({"values": list(values)})


class FilterMealAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesStringEnvelopeSerializer

    @extend_schema(responses=ValuesStringEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(meal="")
            .order_by("meal")
            .values_list("meal", flat=True)
            .distinct()
        )
        return Response({"values": list(values)})


class FilterTownFromAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesStringEnvelopeSerializer

    @extend_schema(responses=ValuesStringEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(townfrom="")
            .order_by("townfrom")
            .values_list("townfrom", flat=True)
            .distinct()
        )
        return Response({"values": list(values)})


class FilterCountryAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesStringEnvelopeSerializer

    @extend_schema(responses=ValuesStringEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(country_slug="")
            .order_by("country_slug")
            .values_list("country_slug", flat=True)
            .distinct()
        )
        return Response({"values": list(values)})


class FilterHotelCategoryAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ValuesIntEnvelopeSerializer

    @extend_schema(responses=ValuesIntEnvelopeSerializer)
    def get(self, request):
        values = (
            Tour.objects.exclude(hotel_category__isnull=True)
            .order_by("hotel_category")
            .values_list("hotel_category", flat=True)
            .distinct()
        )
        return Response({"values": list(values)})


class FavoriteAddRequestSerializer(serializers.Serializer):
    tour_id = serializers.IntegerField()


class FavoriteMetaSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    count = serializers.IntegerField()


class FavoriteEnvelopeSerializer(serializers.Serializer):
    meta = FavoriteMetaSerializer()
    results = TourSearchResponseSerializer(many=True)


class FavoriteToursAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FavoriteEnvelopeSerializer

    def _check_access(self, request, user_id: int) -> None:
        if request.user.is_staff or request.user.is_superuser:
            return
        if request.user.id != user_id:
            raise serializers.ValidationError("Forbidden.")

    @extend_schema(
        parameters=[OpenApiParameter("user_id", OpenApiTypes.INT, required=True, location=OpenApiParameter.PATH)],
        responses=FavoriteEnvelopeSerializer,
    )
    def get(self, request, user_id: int):
        try:
            self._check_access(request, user_id)
        except serializers.ValidationError as e:
            return Response({"error": "forbidden", "details": str(e)}, status=status.HTTP_403_FORBIDDEN)

        tours = Tour.objects.filter(favorites__user_id=user_id).order_by("price_value", "id")
        results = [
            {
                "id": t.id,
                "hotel_name": _hotel_name_from_base_link(t.base_link),
                "price_per_person": int(t.price_value // max(t.adult, 1)) if t.price_value is not None else None,
                "buy_link": t.booking_link,
                "description": _description_for_tour(t),
                "meta": {
                    "rest_type": t.rest_type or None,
                    "hotel_type": t.hotel_type or None,
                    "hotel_category": t.hotel_category,
                    "meal": t.meal or None,
                },
            }
            for t in tours
        ]
        return Response({"meta": {"user_id": user_id, "count": len(results)}, "results": results})

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
