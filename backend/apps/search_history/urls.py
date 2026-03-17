from django.urls import path

from .views import SearchHistoryListCreateView

urlpatterns = [
    path('', SearchHistoryListCreateView.as_view(), name='search-history'),
]
