from django.urls import path

from . import api
from .fx_api import RubFxRatesAPI

urlpatterns = [
    path("tours/", api.TourSearchAPI.as_view(), name="api_tour_search"),
    path("filters/rest-type/", api.FilterRestTypeAPI.as_view(), name="api_filter_rest_type"),
    path("filters/hotel-category/", api.FilterHotelCategoryAPI.as_view(), name="api_filter_hotel_category"),
    path("filters/hotel-type/", api.FilterHotelTypeAPI.as_view(), name="api_filter_hotel_type"),
    path("filters/meal/", api.FilterMealAPI.as_view(), name="api_filter_meal"),
    path("filters/townfrom/", api.FilterTownFromAPI.as_view(), name="api_filter_townfrom"),
    path("filters/country/", api.FilterCountryAPI.as_view(), name="api_filter_country"),
    path("favorites/<int:user_id>/", api.FavoriteToursAPI.as_view(), name="api_favorite_tours"),
    path("favorites/<int:user_id>/<int:tour_id>/", api.FavoriteTourAPI.as_view(), name="api_favorite_tour"),
    path("fx/rub/", RubFxRatesAPI.as_view(), name="api_fx_rub"),
]
