from django.contrib import admin

from .models import Tour


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ('id', 'country_slug', 'townfrom', 'adult', 'child', 'price_value', 'checkin_beg')
    search_fields = ('country_slug', 'townfrom', 'room', 'meal', 'booking_link')
    list_filter = ('country_slug', 'townfrom', 'adult', 'child')
