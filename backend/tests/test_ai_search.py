# backend/tests/test_ai_search.py
import pytest
from rest_framework import status

@pytest.mark.django_db
class TestAISearch:
    def test_ai_search_post_method(self, api_client):
        """AI-поиск принимает POST запросы"""
        response = api_client.post("/api/ai/search/", {
            "query": "спокойный отдых у моря"
        }, format="json")
        
        # Может вернуть 200 (если есть векторы) или 503 (если нет embedder)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]
        
        if response.status_code == status.HTTP_200_OK:
            assert "meta" in response.data
            assert "results" in response.data
            assert response.data["meta"]["query"] == "спокойный отдых у моря"

    def test_ai_search_empty_query(self, api_client):
        """Пустой запрос — ошибка валидации"""
        response = api_client.post("/api/ai/search/", {"query": ""}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert any(key in response.data for key in ["error", "detail", "non_field_errors", "query"])

    def test_ai_search_get_not_allowed(self, api_client):
        """GET-запрос к AI-поиску должен возвращать 405"""
        response = api_client.get("/api/ai/search/?query=test")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_ai_search_response_structure(self, api_client, sample_tours):
        """Проверка структуры ответа (если векторы есть)"""
        response = api_client.post("/api/ai/search/", {
            "query": "Абхазия отель для детей"
        }, format="json")
        
        if response.status_code == status.HTTP_200_OK:
            for result in response.data["results"]:
                assert "id" in result
                assert "hotel_name" in result
                assert "price_per_person" in result
                assert "score" in result  # Уникальное поле для AI-поиска
                assert 0.0 <= result["score"] <= 1.0