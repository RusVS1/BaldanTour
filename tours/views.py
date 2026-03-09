from __future__ import annotations

from django.db.models import Q
from pgvector.django import CosineDistance
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .embeddings import encode_text
from .models import Tour
from .serializers import TourSerializer


def to_int(value: str | None) -> int | None:
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


class TourListView(generics.ListAPIView):
    serializer_class = TourSerializer

    def get_queryset(self):
        qs = Tour.objects.all().order_by('id')
        p = self.request.query_params

        country_slug = p.get('country_slug')
        townfrom = p.get('townfrom')
        meal = p.get('meal')
        room = p.get('room')
        min_price = to_int(p.get('min_price'))
        max_price = to_int(p.get('max_price'))
        adult = to_int(p.get('adult'))
        child = to_int(p.get('child'))
        night_from = to_int(p.get('night_from'))
        night_to = to_int(p.get('night_to'))
        checkin_beg = p.get('checkin_beg')

        if country_slug:
            qs = qs.filter(country_slug=country_slug)
        if townfrom:
            qs = qs.filter(townfrom=townfrom)
        if meal:
            qs = qs.filter(meal__icontains=meal)
        if room:
            qs = qs.filter(room__icontains=room)
        if adult is not None:
            qs = qs.filter(adult=adult)
        if child is not None:
            qs = qs.filter(child=child)
        if checkin_beg:
            qs = qs.filter(checkin_beg=checkin_beg)
        if min_price is not None:
            qs = qs.filter(price_value__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price_value__lte=max_price)
        if night_from is not None:
            qs = qs.filter(night_min__gte=night_from)
        if night_to is not None:
            qs = qs.filter(night_max__lte=night_to)

        search_text = p.get('q')
        if search_text:
            qs = qs.filter(
                Q(country_slug__icontains=search_text)
                | Q(townfrom__icontains=search_text)
                | Q(description__icontains=search_text)
                | Q(room__icontains=search_text)
                | Q(meal__icontains=search_text)
                | Q(functions__icontains=search_text)
                | Q(raw_text__icontains=search_text)
            )

        return qs


class TourDetailView(generics.RetrieveAPIView):
    queryset = Tour.objects.all()
    serializer_class = TourSerializer


class TourSemanticSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('query', '').strip()
        limit = to_int(request.query_params.get('limit')) or 20
        limit = max(1, min(100, limit))

        if not query:
            return Response({'count': 0, 'results': []})

        query_vec = encode_text(query)
        qs = (
            Tour.objects.exclude(embedding=None)
            .annotate(distance=CosineDistance('embedding', query_vec))
            .order_by('distance')[:limit]
        )

        data = TourSerializer(qs, many=True).data
        return Response({'count': len(data), 'results': data})
