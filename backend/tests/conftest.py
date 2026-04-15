# backend/tests/conftest.py
import pytest
import json
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tours.models import Tour, TourImage, TourText, Amenity

User = get_user_model()

@pytest.fixture
def api_client():
    """Базовый API клиент"""
    return APIClient()

@pytest.fixture
def authenticated_client(api_client):
    """Клиент с авторизованным пользователем"""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPass123!"
    )
    api_client.force_login(user)
    api_client.test_user = user
    return api_client

@pytest.fixture
def another_user():
    """Второй пользователь для тестов безопасности"""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="OtherPass123!"
    )

@pytest.fixture
def tour_data():
    """Базовые данные для создания тура"""
    return {
        "country_slug": "abkhazia",
        "country_ru": "Абхазия",
        "townfrom": "moskva",
        "townfrom_ru": "Москва",
        "adult": 2,
        "child": 0,
        "nights": 7,
        "night_min": 5,
        "night_max": 10,
        "checkin_beg": "2026-03-01",
        "checkin_end": "2026-03-31",
        "hotel_name": "Test Hotel",
        "price_value": 50000,
        "price_text": "50 000 ₽",
        "meal": "BB",
        "room": "Standard",
        "request_url": "https://example.com/tour/1",
    }

@pytest.fixture
def create_tour(tour_data):
    """Фабрика для создания туров"""
    def _create(**overrides):
        data = {**tour_data, **overrides}
        return Tour.objects.create(**data)
    return _create

@pytest.fixture
def sample_tours(create_tour):
    """Набор тестовых туров для фильтрации"""
    return [
        create_tour(country_slug="abkhazia", price_value=30000, nights=5, meal="BB"),
        create_tour(country_slug="abkhazia", price_value=60000, nights=7, meal="HB"),
        create_tour(country_slug="belarus", price_value=40000, nights=6, meal="BB"),
        create_tour(country_slug="belarus", price_value=80000, nights=10, meal="AI"),
    ]

REQUIRED_PARAMS = {
    "townfrom": "moskva",
    "country_slug": "abkhazia",
    "departure_from": "2026-03-01",
    "departure_to": "2026-03-31",
    "nights_min": 5,
    "nights_max": 10,
    "child": 0,
    "adult": 2,
}
