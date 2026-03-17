from django.urls import path

from apps.api.views import ApiHealthView, CountriesView, SemanticTourSearchView, TourDetailView, ToursView

urlpatterns = [
    path("health", ApiHealthView.as_view(), name="api-health"),
    path("countries", CountriesView.as_view(), name="countries"),
    path("tours", ToursView.as_view(), name="tours"),
    path("tours/semantic-search", SemanticTourSearchView.as_view(), name="tours-semantic-search"),
    path("tours/<int:pk>", TourDetailView.as_view(), name="tour-detail"),
]
