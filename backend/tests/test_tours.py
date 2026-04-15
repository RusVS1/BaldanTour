# backend/tests/test_tours.py
import pytest
from rest_framework import status

# Обязательные параметры для TourSearchAPI
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

@pytest.mark.django_db
class TestTourSearch:
    def test_search_missing_params(self, api_client):
        """Поиск без обязательных параметров"""
        response = api_client.get("/api/tours/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "missing_required_params"
        assert "townfrom" in response.data["missing"]

    def test_search_with_all_params(self, api_client, sample_tours):
        """Поиск с полным набором параметров"""
        response = api_client.get("/api/tours/", REQUIRED_PARAMS)
        assert response.status_code == status.HTTP_200_OK
        assert "meta" in response.data
        assert "results" in response.data
        assert response.data["meta"]["count"] >= 0

    def test_search_country_filter_abkhazia(self, api_client, sample_tours):
        """Фильтрация по стране: Абхазия"""
        params = {**REQUIRED_PARAMS, "country_slug": "abkhazia"}
        response = api_client.get("/api/tours/", params)
        
        assert response.status_code == status.HTTP_200_OK
        for tour in response.data["results"]:
            assert tour["meta"]["country_value"] == "abkhazia"

    def test_search_country_filter_belarus(self, api_client, sample_tours):
        """Фильтрация по стране: Беларусь"""
        params = {**REQUIRED_PARAMS, "country_slug": "belarus"}
        response = api_client.get("/api/tours/", params)
        
        assert response.status_code == status.HTTP_200_OK
        for tour in response.data["results"]:
            assert tour["meta"]["country_value"] == "belarus"

    def test_search_price_range(self, api_client, sample_tours):
        """Фильтрация по цене"""
        params = {**REQUIRED_PARAMS, "price_min": 35000, "price_max": 70000}
        response = api_client.get("/api/tours/", params)
        
        assert response.status_code == status.HTTP_200_OK
        for tour in response.data["results"]:
            price = tour["price_per_person"] or 0
            assert 35000 <= price <= 70000, f"Тур {tour['id']} вне диапазона: {price}"

    def test_search_nights_filter(self, api_client, sample_tours):
        """Фильтрация по количеству ночей"""
        params = {**REQUIRED_PARAMS, "nights_min": 6, "nights_max": 8}
        response = api_client.get("/api/tours/", params)
        
        assert response.status_code == status.HTTP_200_OK
        # Проверяем, что все туры в диапазоне (если есть результаты)
        if response.data["results"]:
            for tour in response.data["results"]:
                # nights может быть в мета или в данных тура
                meta = tour.get("meta", {})
                nights = meta.get("nights_min") or meta.get("nights_max")
                if nights:
                    assert 6 <= nights <= 8

    def test_search_meal_filter(self, api_client, sample_tours):
        """Фильтрация по типу питания"""
        params = {**REQUIRED_PARAMS, "meal": "BB"}
        response = api_client.get("/api/tours/", params)
        
        assert response.status_code == status.HTTP_200_OK
        for tour in response.data["results"]:
            assert tour["meal"] == "BB" or tour["meal"] is None

@pytest.mark.django_db
class TestTourSorting:
    def test_sort_price_asc(self, api_client, sample_tours):
        """Сортировка по цене (возрастание)"""
        params = {**REQUIRED_PARAMS, "sort": "price_asc"}
        response = api_client.get("/api/tours/", params)
        
        prices = [t["price_per_person"] or 0 for t in response.data["results"]]
        assert prices == sorted(prices), "Сортировка по возрастанию нарушена"

    def test_sort_price_desc(self, api_client, sample_tours):
        """Сортировка по цене (убывание)"""
        params = {**REQUIRED_PARAMS, "sort": "price_desc"}
        response = api_client.get("/api/tours/", params)
        
        prices = [t["price_per_person"] or 0 for t in response.data["results"]]
        assert prices == sorted(prices, reverse=True), "Сортировка по убыванию нарушена"

@pytest.mark.django_db
class TestTourValidation:
    def test_invalid_price_negative(self, api_client):
        """Отрицательная цена — должна возвращать 400 или игнорировать"""
        params = {**REQUIRED_PARAMS, "price_min": -100}
        response = api_client.get("/api/tours/", params)
        # Допустимо: 200 с фильтрацией или 400 с ошибкой валидации
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_invalid_date_format(self, api_client):
        """Некорректный формат даты"""
        params = {**REQUIRED_PARAMS, "departure_from": "not-a-date"}
        response = api_client.get("/api/tours/", params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_country_slug_vs_label(self, api_client, sample_tours):
        """Поиск по slug и по русскому названию страны"""
        # По slug
        resp1 = api_client.get("/api/tours/", {**REQUIRED_PARAMS, "country_slug": "abkhazia"})
        # По русскому названию
        resp2 = api_client.get("/api/tours/", {**REQUIRED_PARAMS, "country_slug": "Абхазия"})
        
        assert resp1.status_code == resp2.status_code == status.HTTP_200_OK
        # Количество результатов должно совпадать
        assert resp1.data["meta"]["count"] == resp2.data["meta"]["count"]