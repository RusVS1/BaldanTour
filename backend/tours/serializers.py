from rest_framework import serializers

from .models import Amenity, Tour


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["slug", "name"]


class TourSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)

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
            "price_text",
            "price_value",
            "booking_link",
            "raw_text",
            "amenities",
        ]
