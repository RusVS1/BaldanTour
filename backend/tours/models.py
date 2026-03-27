from django.conf import settings
from django.db import models
from django.db.models import Q
from pgvector.django import VectorField


class TourText(models.Model):
    sha256 = models.CharField(max_length=64, unique=True)
    content = models.TextField()

    def __str__(self) -> str:
        return f"{self.sha256[:8]}…"

class TourImage(models.Model):
    sha256 = models.CharField(max_length=64, unique=True)
    url = models.URLField(max_length=2000)

    def __str__(self) -> str:
        return self.url


class Amenity(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return self.name


class Tour(models.Model):
    country_slug = models.CharField(max_length=64, db_index=True)
    country_ru = models.CharField(max_length=128, blank=True, db_index=True)

    base_link = models.URLField(max_length=2000, null=True, blank=True)
    request_url = models.URLField(max_length=2000, db_index=True)

    townfrom = models.CharField(max_length=128, blank=True, db_index=True)
    townfrom_ru = models.CharField(max_length=128, blank=True, db_index=True)
    adult = models.PositiveSmallIntegerField(default=1, db_index=True)
    child = models.PositiveSmallIntegerField(default=0, db_index=True)

    night_min = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    night_max = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    checkin_beg = models.DateField(null=True, blank=True, db_index=True)
    checkin_end = models.DateField(null=True, blank=True, db_index=True)

    hotel_name = models.CharField(max_length=255, blank=True, db_index=True)
    hotel_rating = models.CharField(max_length=32, blank=True)
    main_image = models.ForeignKey(
        TourImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="tours"
    )

    common_description = models.ForeignKey(
        TourText, null=True, blank=True, on_delete=models.SET_NULL, related_name="common_for"
    )
    target_description = models.ForeignKey(
        TourText, null=True, blank=True, on_delete=models.SET_NULL, related_name="target_for"
    )
    answer_description = models.ForeignKey(
        TourText, null=True, blank=True, on_delete=models.SET_NULL, related_name="answer_for"
    )

    trip_dates = models.TextField(blank=True)

    nights = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    room = models.CharField(max_length=255, blank=True, db_index=True)
    meal = models.CharField(max_length=128, blank=True, db_index=True)
    placement = models.CharField(max_length=255, blank=True, db_index=True)

    rest_type = models.CharField(max_length=32, blank=True, db_index=True)
    hotel_type = models.CharField(max_length=32, blank=True, db_index=True)
    hotel_category = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)

    price_text = models.CharField(max_length=64, blank=True)
    price_value = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    embedding = VectorField(dimensions=768, null=True, blank=True)

    booking_link = models.URLField(max_length=2000, null=True, blank=True)
    raw_text = models.TextField(blank=True)

    amenities = models.ManyToManyField(Amenity, related_name="tours", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price_value", "id"]
        indexes = [
            models.Index(fields=["price_value", "country_slug"]),
            models.Index(fields=["checkin_beg", "checkin_end"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["booking_link"],
                condition=Q(booking_link__isnull=False),
                name="uniq_tour_booking_link",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.country_slug} — {self.price_text or self.price_value or ''}".strip()


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "tour"], name="uniq_user_tour_fav")
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.tour_id}"
