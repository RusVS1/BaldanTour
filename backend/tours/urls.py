from django.urls import path

from . import views

urlpatterns = [
    path("", views.tour_search, name="tour_search"),
    path("favorites/add/<int:tour_id>/", views.favorite_add, name="favorite_add"),
    path("favorites/remove/<int:tour_id>/", views.favorite_remove, name="favorite_remove"),
]

