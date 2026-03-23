from django.contrib import admin

from .models import Amenity, Favorite, Tour


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ("id", "country_slug", "townfrom", "nights", "meal", "hotel_category", "price_value")
    list_filter = ("country_slug", "townfrom", "meal", "hotel_category")
    search_fields = ("request_url", "base_link", "raw_text", "room", "placement")
    autocomplete_fields = ("amenities",)


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    search_fields = ("slug", "name")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "tour", "created_at")
    search_fields = ("user__username", "tour__request_url")
