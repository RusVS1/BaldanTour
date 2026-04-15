from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .api import _booking_url_for_tour, _detect_query_filters, _parse_int
from .models import Tour


class DummyEmbedder:
    provider = "dummy"
    dim = 768

    def embed_texts(self, texts):
        return [[1.0] + [0.0] * 767 for _ in texts]


class SearchValidationTests(SimpleTestCase):
    def test_invalid_int_returns_none(self):
        self.assertIsNone(_parse_int("abc"))

    def test_detects_common_ai_query_filters(self):
        filters = _detect_query_filters("Семейный отдых в Турции из Москвы, всё включено")
        self.assertEqual(filters["country_slug"], "turkey")
        self.assertEqual(filters["townfrom"], "moskva")
        self.assertEqual(filters["meal"], "AI")
        self.assertEqual(filters["hotel_type"], "Для детей")

    def test_detects_children_ai_route(self):
        filters = _detect_query_filters("Подбери спокойный отдых для детей у моря")
        self.assertEqual(filters["hotel_type"], "Для детей")

    def test_detects_adults_ai_route_without_party_count_false_positive(self):
        filters = _detect_query_filters("Отдых для взрослых без детей")
        self.assertEqual(filters["hotel_type"], "Для взрослых")

        party_filters = _detect_query_filters("Турция 2 взрослых и 1 ребенок")
        self.assertNotEqual(party_filters.get("hotel_type"), "Для взрослых")

    def test_detects_hotel_category_from_ai_query(self):
        self.assertEqual(_detect_query_filters("отель 5 звезд для детей")["hotel_category"], 5)
        self.assertEqual(_detect_query_filters("пятизвездочный отель у моря")["hotel_category"], 5)
        self.assertEqual(_detect_query_filters("4* все включено")["hotel_category"], 4)

    def test_booking_url_does_not_fall_back_to_base_link(self):
        tour = SimpleNamespace(
            booking_link="https://anextour.ru/booking/example",
            base_link="https://anextour.ru/tours/turkey/hotel",
        )
        self.assertEqual(_booking_url_for_tour(tour), "https://anextour.ru/booking/example")

        tour_without_booking = SimpleNamespace(
            booking_link="",
            base_link="https://anextour.ru/tours/turkey/hotel",
        )
        self.assertIsNone(_booking_url_for_tour(tour_without_booking))


class AISearchAudienceFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.embedding = [1.0] + [0.0] * 767

    def create_tour(self, **overrides):
        data = {
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
            "request_url": "https://example.com/tour/default",
            "embedding": self.embedding,
        }
        data.update(overrides)
        return Tour.objects.create(**data)

    @patch("tours.api.get_reranker", return_value=None)
    @patch("tours.api.get_embedder", return_value=DummyEmbedder())
    def test_children_route_excludes_adults_only_hotels(self, *_):
        child_tour = self.create_tour(
            hotel_name="Kids Hotel",
            hotel_type="Для детей",
            request_url="https://example.com/tour/kids",
        )
        adult_tour = self.create_tour(
            hotel_name="Adults Hotel",
            hotel_type="Для взрослых",
            request_url="https://example.com/tour/adults",
        )

        response = self.client.post("/api/ai/search/", {"query": "отдых для детей", "limit": 10}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(child_tour.id, result_ids)
        self.assertNotIn(adult_tour.id, result_ids)
        self.assertEqual(response.data["meta"]["detected_filters"]["hotel_type"], "Для детей")

    @patch("tours.api.get_reranker", return_value=None)
    @patch("tours.api.get_embedder", return_value=DummyEmbedder())
    def test_adults_route_excludes_children_hotels(self, *_):
        child_tour = self.create_tour(
            hotel_name="Kids Hotel",
            hotel_type="Для детей",
            request_url="https://example.com/tour/kids",
        )
        adult_tour = self.create_tour(
            hotel_name="Adults Hotel",
            hotel_type="Для взрослых",
            request_url="https://example.com/tour/adults",
        )

        response = self.client.post(
            "/api/ai/search/",
            {"query": "отдых для взрослых без детей", "limit": 10},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(adult_tour.id, result_ids)
        self.assertNotIn(child_tour.id, result_ids)
        self.assertEqual(response.data["meta"]["detected_filters"]["hotel_type"], "Для взрослых")

    @patch("tours.api.get_reranker", return_value=None)
    @patch("tours.api.get_embedder", return_value=DummyEmbedder())
    def test_hotel_category_filter_excludes_other_star_counts(self, *_):
        five_star_tour = self.create_tour(
            hotel_name="Five Star Hotel",
            hotel_category=5,
            request_url="https://example.com/tour/five-star",
        )
        four_star_tour = self.create_tour(
            hotel_name="Four Star Hotel",
            hotel_category=4,
            request_url="https://example.com/tour/four-star",
        )

        response = self.client.post("/api/ai/search/", {"query": "отель 5 звезд", "limit": 10}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(five_star_tour.id, result_ids)
        self.assertNotIn(four_star_tour.id, result_ids)
        self.assertEqual(response.data["meta"]["detected_filters"]["hotel_category"], 5)
