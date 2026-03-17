from rest_framework import serializers

from apps.parsed_tours.models import ParsedAvailableTour, ParsedCountry


class ParsedCountrySerializer(serializers.ModelSerializer):
    tours_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ParsedCountry
        fields = ("id", "slug", "tours_count")


class ParsedAvailableTourSerializer(serializers.ModelSerializer):
    country_slug = serializers.CharField(source="country.slug", read_only=True)

    class Meta:
        model = ParsedAvailableTour
        fields = (
            "id",
            "country_slug",
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


class SemanticSearchRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)
    country = serializers.CharField(max_length=64, required=False, allow_blank=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50, default=5)


class SemanticSearchItemSerializer(serializers.Serializer):
    score = serializers.FloatField()
    tour = ParsedAvailableTourSerializer()


class SemanticSearchResponseSerializer(serializers.Serializer):
    model = serializers.CharField()
    results = SemanticSearchItemSerializer(many=True)
