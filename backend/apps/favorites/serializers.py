from __future__ import annotations

from rest_framework import serializers

from apps.api.serializers import ParsedAvailableTourSerializer
from apps.favorites.models import Favorite


class FavoriteCreateSerializer(serializers.Serializer):
    tour_id = serializers.IntegerField(min_value=1)


class FavoriteSerializer(serializers.ModelSerializer):
    tour = ParsedAvailableTourSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "tour", "created_at")

