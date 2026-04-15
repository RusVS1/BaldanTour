# backend/tests/test_ai_search.py
import pytest
from rest_framework import status


class DummyEmbedder:
    provider = "dummy"
    dim = 768

    def embed_texts(self, texts):
        return [[1.0] + [0.0] * 767 for _ in texts]


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

    def test_ai_search_children_route_excludes_adults_only(self, api_client, create_tour, monkeypatch):
        """Запрос для детей не должен возвращать туры для взрослых"""
        monkeypatch.setattr("tours.api.get_embedder", lambda: DummyEmbedder())
        monkeypatch.setattr("tours.api.get_reranker", lambda: None)
        embedding = [1.0] + [0.0] * 767

        child_tour = create_tour(
            hotel_name="Kids Hotel",
            hotel_type="Для детей",
            embedding=embedding,
            request_url="https://example.com/tour/kids",
        )
        adult_tour = create_tour(
            hotel_name="Adults Hotel",
            hotel_type="Для взрослых",
            embedding=embedding,
            request_url="https://example.com/tour/adults",
        )

        response = api_client.post("/api/ai/search/", {"query": "отдых для детей", "limit": 10}, format="json")

        assert response.status_code == status.HTTP_200_OK
        result_ids = {item["id"] for item in response.data["results"]}
        assert child_tour.id in result_ids
        assert adult_tour.id not in result_ids
        assert response.data["meta"]["detected_filters"]["hotel_type"] == "Для детей"

    def test_ai_search_adults_route_excludes_children_hotels(self, api_client, create_tour, monkeypatch):
        """Запрос для взрослых не должен возвращать детские/семейные туры"""
        monkeypatch.setattr("tours.api.get_embedder", lambda: DummyEmbedder())
        monkeypatch.setattr("tours.api.get_reranker", lambda: None)
        embedding = [1.0] + [0.0] * 767

        child_tour = create_tour(
            hotel_name="Kids Hotel",
            hotel_type="Для детей",
            embedding=embedding,
            request_url="https://example.com/tour/kids",
        )
        adult_tour = create_tour(
            hotel_name="Adults Hotel",
            hotel_type="Для взрослых",
            embedding=embedding,
            request_url="https://example.com/tour/adults",
        )

        response = api_client.post("/api/ai/search/", {"query": "отдых для взрослых без детей", "limit": 10}, format="json")

        assert response.status_code == status.HTTP_200_OK
        result_ids = {item["id"] for item in response.data["results"]}
        assert adult_tour.id in result_ids
        assert child_tour.id not in result_ids
        assert response.data["meta"]["detected_filters"]["hotel_type"] == "Для взрослых"

    def test_ai_search_hotel_category_excludes_other_star_counts(self, api_client, create_tour, monkeypatch):
        """Запрос по звездам должен строго фильтровать hotel_category"""
        monkeypatch.setattr("tours.api.get_embedder", lambda: DummyEmbedder())
        monkeypatch.setattr("tours.api.get_reranker", lambda: None)
        embedding = [1.0] + [0.0] * 767

        five_star_tour = create_tour(
            hotel_name="Five Star Hotel",
            hotel_category=5,
            embedding=embedding,
            request_url="https://example.com/tour/five-star",
        )
        four_star_tour = create_tour(
            hotel_name="Four Star Hotel",
            hotel_category=4,
            embedding=embedding,
            request_url="https://example.com/tour/four-star",
        )

        response = api_client.post("/api/ai/search/", {"query": "отель 5 звезд", "limit": 10}, format="json")

        assert response.status_code == status.HTTP_200_OK
        result_ids = {item["id"] for item in response.data["results"]}
        assert five_star_tour.id in result_ids
        assert four_star_tour.id not in result_ids
        assert response.data["meta"]["detected_filters"]["hotel_category"] == 5
