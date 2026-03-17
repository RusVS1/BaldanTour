from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.parsed_tours.models import ParsedAvailableTour


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    tour = models.ForeignKey(ParsedAvailableTour, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "tour"], name="uniq_favorite_user_tour"),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="fav_user_created_idx"),
            models.Index(fields=["tour"], name="fav_tour_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.tour_id}"

