from django.db import models


class ParsedCountry(models.Model):
    slug = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.slug


class ParsedAvailableTour(models.Model):
    country = models.ForeignKey(ParsedCountry, on_delete=models.CASCADE, related_name="tours")

    # Uniqueness across re-imports; computed from key fields.
    source_hash = models.CharField(max_length=64, unique=True)

    base_link = models.TextField(blank=True, default="")
    request_url = models.TextField(blank=True, default="")

    townfrom = models.CharField(max_length=128, blank=True, default="")
    adult = models.IntegerField(null=True, blank=True)
    child = models.IntegerField(null=True, blank=True)
    night_min = models.IntegerField(null=True, blank=True)
    night_max = models.IntegerField(null=True, blank=True)

    # CSV uses YYYYMMDD; importer converts to DateField.
    checkin_beg = models.DateField(null=True, blank=True)
    checkin_end = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True, default="")
    functions = models.TextField(blank=True, default="")
    trip_dates = models.TextField(blank=True, default="")

    nights = models.CharField(max_length=64, blank=True, default="")
    room = models.CharField(max_length=255, blank=True, default="")
    meal = models.CharField(max_length=255, blank=True, default="")
    placement = models.CharField(max_length=255, blank=True, default="")

    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    booking_link = models.TextField(blank=True, default="")

    raw_text = models.TextField(blank=True, default="")

    # Deterministic embedding vector (list[float]); see import command.
    embedding = models.JSONField(null=True, blank=True)
    embedding_version = models.CharField(max_length=255, blank=True, default="")

    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["country", "checkin_beg"], name="parsed_tour_country_82c9f9_idx"),
            models.Index(fields=["country", "price"], name="parsed_tour_country_d2d02a_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.country.slug}: {self.townfrom} {self.checkin_beg} {self.price}"
