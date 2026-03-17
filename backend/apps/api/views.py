from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.semantic import DEFAULT_MODEL_ID, embed_text, semantic_search_country_ids, semantic_search_ids
from apps.api.serializers import (
    ParsedAvailableTourSerializer,
    ParsedCountrySerializer,
    SemanticSearchItemSerializer,
    SemanticSearchRequestSerializer,
    SemanticSearchResponseSerializer,
)
from apps.parsed_tours.models import ParsedAvailableTour, ParsedCountry


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except Exception:
        return None


class CountriesView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ParsedCountrySerializer

    def get_queryset(self):
        return ParsedCountry.objects.annotate(tours_count=Count("tours")).order_by("slug")


class ToursView(generics.ListAPIView):
    """
    Базовая фильтрация на стороне бэкенда, чтобы фронтенд запрашивал только нужное.
    Query params:
      - country: slug страны
      - q: поиск по description/raw_text
      - date_from/date_to: YYYY-MM-DD по полю checkin_beg
      - price_min/price_max
      - townfrom
      - limit/offset: DRF LimitOffsetPagination
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = ParsedAvailableTourSerializer

    def get_queryset(self):
        qs = ParsedAvailableTour.objects.select_related("country").all().order_by("-checkin_beg", "id")

        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(country__slug=country)

        townfrom = self.request.query_params.get("townfrom")
        if townfrom:
            qs = qs.filter(townfrom__iexact=townfrom)

        q = self.request.query_params.get("q")
        if q:
            q = q.strip()
            qs = qs.filter(Q(description__icontains=q) | Q(raw_text__icontains=q))

        date_from = _parse_date(self.request.query_params.get("date_from"))
        if date_from:
            qs = qs.filter(checkin_beg__gte=date_from)

        date_to = _parse_date(self.request.query_params.get("date_to"))
        if date_to:
            qs = qs.filter(checkin_beg__lte=date_to)

        price_min = _parse_decimal(self.request.query_params.get("price_min"))
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)

        price_max = _parse_decimal(self.request.query_params.get("price_max"))
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)

        return qs


class TourDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ParsedAvailableTourSerializer
    queryset = ParsedAvailableTour.objects.select_related("country").all()


class ApiHealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, _request):
        countries = ParsedCountry.objects.count()
        tours = ParsedAvailableTour.objects.count()
        return Response({"status": "ok", "countries": countries, "tours": tours})


class SemanticTourSearchView(APIView):
    """
    POST /api/tours/semantic-search
    Body: { "text": "...", "country": "spain"?, "limit": 5? }
    Response: { "model": "...", "results": [{ "score": 0.73, "tour": {...} }, ...] }
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["tours"],
        request=SemanticSearchRequestSerializer,
        responses={200: SemanticSearchResponseSerializer},
        summary="Семантический поиск туров",
        description=(
            "Принимает текст, строит эмбеддинг, сравнивает с эмбеддингами туров по cosine similarity "
            "и возвращает top-N результатов."
        ),
    )
    def post(self, request):
        req = SemanticSearchRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        text = req.validated_data["text"]
        limit = int(req.validated_data.get("limit") or 5)
        country = (req.validated_data.get("country") or "").strip()

        qvec = embed_text(text, model_id=DEFAULT_MODEL_ID)
        if country:
            candidates = semantic_search_country_ids(
                qvec,
                country_slug=country,
                limit=limit,
                model_id=DEFAULT_MODEL_ID,
            )
        else:
            candidates = semantic_search_ids(qvec, limit=limit, model_id=DEFAULT_MODEL_ID, oversample=200)

        ids = [cid for cid, _score in candidates]
        tours = (
            ParsedAvailableTour.objects.select_related("country")
            .filter(id__in=ids)
            .only(
                "id",
                "country__slug",
                "townfrom",
                "adult",
                "child",
                "night_min",
                "night_max",
                "checkin_beg",
                "checkin_end",
                "nights",
                "room",
                "meal",
                "placement",
                "price",
                "booking_link",
                "request_url",
                "description",
                "raw_text",
                "embedding_version",
            )
        )
        by_id = {t.id: t for t in tours}

        results = []
        for tour_id, score in candidates:
            tour = by_id.get(tour_id)
            if tour is None:
                continue
            results.append({"score": score, "tour": ParsedAvailableTourSerializer(tour).data})
            if len(results) >= limit:
                break

        out = {"model": DEFAULT_MODEL_ID, "results": SemanticSearchItemSerializer(results, many=True).data}
        return Response(out)

