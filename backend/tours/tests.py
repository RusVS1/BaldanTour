from types import SimpleNamespace

from django.test import SimpleTestCase

from .api import _booking_url_for_tour, _detect_query_filters, _parse_int


class SearchValidationTests(SimpleTestCase):
    def test_invalid_int_returns_none(self):
        self.assertIsNone(_parse_int("abc"))

    def test_detects_common_ai_query_filters(self):
        filters = _detect_query_filters("Семейный отдых в Турции из Москвы, всё включено")
        self.assertEqual(filters["country_slug"], "turkey")
        self.assertEqual(filters["townfrom"], "moskva")
        self.assertEqual(filters["meal"], "AI")

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
