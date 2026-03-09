from rest_framework import serializers

from .models import Tour


class TourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tour
        fields = [
            'id',
            'country_slug',
            'base_link',
            'request_url',
            'townfrom',
            'adult',
            'child',
            'night_min',
            'night_max',
            'checkin_beg',
            'checkin_end',
            'description',
            'functions',
            'trip_dates',
            'nights',
            'room',
            'meal',
            'placement',
            'price',
            'price_value',
            'booking_link',
            'raw_text',
            'created_at',
            'updated_at',
        ]
