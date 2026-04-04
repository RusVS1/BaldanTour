# backend/tests/test_security.py
import pytest
from .conftest import REQUIRED_PARAMS
from rest_framework import status

@pytest.mark.django_db
class TestInputValidation:
    def test_sql_injection_attempt(self, api_client):
        """Попытка SQL-инъекции в параметрах"""
        params = {**REQUIRED_PARAMS, "country_slug": "abkhazia' OR '1'='1"}
        response = api_client.get("/api/tours/", params)
        # Не должно падать с 500
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_xss_in_query(self, api_client):
        """Попытка XSS в поисковом запросе"""
        params = {**REQUIRED_PARAMS, "townfrom": "<script>alert(1)</script>"}
        response = api_client.get("/api/tours/", params)
        # Не должно падать с 500
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_extreme_pagination(self, api_client):
        """Экстремальные значения пагинации"""
        params = {**REQUIRED_PARAMS, "page": 999999, "page_size": 1000}
        response = api_client.get("/api/tours/", params)
        # Должен вернуть 200 с пустым results или ограничить page_size
        assert response.status_code == status.HTTP_200_OK
        assert response.data["meta"]["page_size"] <= 500  # Ограничение в коде

    def test_negative_adult_child(self, api_client):
        """Отрицательные значения adult/child"""
        params = {**REQUIRED_PARAMS, "adult": -1, "child": -5}
        response = api_client.get("/api/tours/", params)
        # Должен вернуть 400 (валидация) или 200 с игнорированием
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]

@pytest.mark.django_db
class TestRateLimiting:
    def test_many_requests(self, api_client):
        """Базовая проверка: 10 запросов подряд не ломают сервер"""
        for _ in range(10):
            response = api_client.get("/api/filters/country/")
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
        # Примечание: настоящий rate limiting настраивается отдельно