import django_filters
from django.db.models import Q

from .models import Tour


class TourFilter(django_filters.FilterSet):
    country_slug = django_filters.CharFilter(field_name="country_slug", lookup_expr="iexact")
    townfrom = django_filters.CharFilter(field_name="townfrom", lookup_expr="iexact")

    request_url = django_filters.CharFilter(field_name="request_url", lookup_expr="icontains")
    base_link = django_filters.CharFilter(field_name="base_link", lookup_expr="icontains")
    booking_link = django_filters.CharFilter(field_name="booking_link", lookup_expr="icontains")

    room = django_filters.CharFilter(field_name="room", lookup_expr="icontains")
    meal = django_filters.CharFilter(field_name="meal", lookup_expr="icontains")
    meal_exact = django_filters.CharFilter(field_name="meal", lookup_expr="iexact")
    placement = django_filters.CharFilter(field_name="placement", lookup_expr="icontains")

    rest_type = django_filters.CharFilter(method="filter_rest_type")
    hotel_type = django_filters.CharFilter(method="filter_hotel_type")

    hotel_category = django_filters.NumberFilter(field_name="hotel_category")
    hotel_category_min = django_filters.NumberFilter(
        field_name="hotel_category", lookup_expr="gte"
    )
    hotel_category_max = django_filters.NumberFilter(
        field_name="hotel_category", lookup_expr="lte"
    )

    trip_dates = django_filters.CharFilter(field_name="trip_dates", lookup_expr="icontains")
    raw_text = django_filters.CharFilter(field_name="raw_text", lookup_expr="icontains")

    price_min = django_filters.NumberFilter(field_name="price_value", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price_value", lookup_expr="lte")

    checkin_from = django_filters.DateFilter(field_name="checkin_beg", lookup_expr="gte")
    checkin_to = django_filters.DateFilter(field_name="checkin_end", lookup_expr="lte")

    nights_min = django_filters.NumberFilter(field_name="nights", lookup_expr="gte")
    nights_max = django_filters.NumberFilter(field_name="nights", lookup_expr="lte")

    night_min_gte = django_filters.NumberFilter(field_name="night_min", lookup_expr="gte")
    night_min_lte = django_filters.NumberFilter(field_name="night_min", lookup_expr="lte")
    night_max_gte = django_filters.NumberFilter(field_name="night_max", lookup_expr="gte")
    night_max_lte = django_filters.NumberFilter(field_name="night_max", lookup_expr="lte")

    adult_min = django_filters.NumberFilter(field_name="adult", lookup_expr="gte")
    adult_max = django_filters.NumberFilter(field_name="adult", lookup_expr="lte")
    child_min = django_filters.NumberFilter(field_name="child", lookup_expr="gte")
    child_max = django_filters.NumberFilter(field_name="child", lookup_expr="lte")

    amenities = django_filters.CharFilter(method="filter_amenities_all")
    amenities_any = django_filters.CharFilter(method="filter_amenities_any")

    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = Tour
        fields = [
            "id",
            "country_slug",
            "base_link",
            "request_url",
            "townfrom",
            "adult",
            "child",
            "night_min",
            "night_max",
            "checkin_beg",
            "checkin_end",
            "trip_dates",
            "nights",
            "room",
            "meal",
            "placement",
            "hotel_category",
            "price_value",
            "booking_link",
            "raw_text",
        ]

    def _split(self, value: str) -> list[str]:
        return [v.strip() for v in value.split(",") if v.strip()]

    def filter_amenities_all(self, queryset, name, value):
        slugs = self._split(value)
        for slug in slugs:
            queryset = queryset.filter(amenities__slug=slug)
        return queryset.distinct()

    def filter_amenities_any(self, queryset, name, value):
        slugs = self._split(value)
        if not slugs:
            return queryset
        return queryset.filter(amenities__slug__in=slugs).distinct()

    def filter_q(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(room__icontains=value)
            | Q(placement__icontains=value)
            | Q(meal__icontains=value)
            | Q(raw_text__icontains=value)
            | Q(common_description__content__icontains=value)
            | Q(target_description__content__icontains=value)
            | Q(answer_description__content__icontains=value)
        )

    def filter_rest_type(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(rest_type__iexact=value)
            | Q(raw_text__icontains=value)
            | Q(common_description__content__icontains=value)
            | Q(target_description__content__icontains=value)
            | Q(answer_description__content__icontains=value)
        )

    def filter_hotel_type(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(hotel_type__iexact=value)
            | Q(placement__icontains=value)
            | Q(room__icontains=value)
            | Q(raw_text__icontains=value)
        )
