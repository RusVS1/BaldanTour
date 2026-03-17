from django.urls import path

from apps.favorites.views import FavoritesCreateView, FavoritesDeleteView, FavoritesListView

urlpatterns = [
    path("", FavoritesListView.as_view(), name="favorites-list"),
    path("add", FavoritesCreateView.as_view(), name="favorites-add"),
    path("<int:tour_id>", FavoritesDeleteView.as_view(), name="favorites-delete"),
]

