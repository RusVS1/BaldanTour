from django.urls import path

from . import api
from .fx_api import RubFxRatesAPI

urlpatterns = [
    path("tours/", api.TourListAPI.as_view(), name="api_tour_list"),
    path("tours/<int:pk>/", api.TourDetailAPI.as_view(), name="api_tour_detail"),
    path("favorites/", api.FavoriteListAPI.as_view(), name="api_favorites"),
    path("favorites/<int:tour_id>/", api.FavoriteToggleAPI.as_view(), name="api_favorite_toggle"),
    path("fx/rub/", RubFxRatesAPI.as_view(), name="api_fx_rub"),
]
