from django.urls import path

from . import api
from .fx_api import RubFxRatesAPI

urlpatterns = [
    path("health/", api.HealthAPI.as_view(), name="api_health"),
    path("tours/", api.TourSearchAPI.as_view(), name="api_tour_search"),
    path("ai/search/", api.AISearchAPI.as_view(), name="api_ai_search"),
    path("filters/rest-type/", api.FilterRestTypeAPI.as_view(), name="api_filter_rest_type"),
    path("filters/hotel-category/", api.FilterHotelCategoryAPI.as_view(), name="api_filter_hotel_category"),
    path("filters/hotel-type/", api.FilterHotelTypeAPI.as_view(), name="api_filter_hotel_type"),
    path("filters/meal/", api.FilterMealAPI.as_view(), name="api_filter_meal"),
    path("filters/townfrom/", api.FilterTownFromAPI.as_view(), name="api_filter_townfrom"),
    path("filters/country/", api.FilterCountryAPI.as_view(), name="api_filter_country"),
    path("favorites/<int:user_id>/", api.FavoriteToursAPI.as_view(), name="api_favorite_tours"),
    path(
        "favorites/<int:user_id>/filters/rest-type/",
        api.FavoriteFilterRestTypeAPI.as_view(),
        name="api_favorite_filter_rest_type",
    ),
    path(
        "favorites/<int:user_id>/filters/hotel-category/",
        api.FavoriteFilterHotelCategoryAPI.as_view(),
        name="api_favorite_filter_hotel_category",
    ),
    path(
        "favorites/<int:user_id>/filters/hotel-type/",
        api.FavoriteFilterHotelTypeAPI.as_view(),
        name="api_favorite_filter_hotel_type",
    ),
    path(
        "favorites/<int:user_id>/filters/meal/",
        api.FavoriteFilterMealAPI.as_view(),
        name="api_favorite_filter_meal",
    ),
    path(
        "favorites/<int:user_id>/filters/townfrom/",
        api.FavoriteFilterTownFromAPI.as_view(),
        name="api_favorite_filter_townfrom",
    ),
    path(
        "favorites/<int:user_id>/filters/country/",
        api.FavoriteFilterCountryAPI.as_view(),
        name="api_favorite_filter_country",
    ),
    path("favorites/<int:user_id>/<int:tour_id>/", api.FavoriteTourAPI.as_view(), name="api_favorite_tour"),
    path("fx/rub/", RubFxRatesAPI.as_view(), name="api_fx_rub"),
]
