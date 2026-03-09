from django.urls import path

from .views import TourDetailView, TourListView, TourSemanticSearchView

urlpatterns = [
    path('', TourListView.as_view(), name='tour-list'),
    path('search/', TourSemanticSearchView.as_view(), name='tour-search'),
    path('<int:pk>/', TourDetailView.as_view(), name='tour-detail'),
]
