from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Tour(models.Model):
    unique_key = models.CharField(max_length=64, unique=True)
    country_slug = models.CharField(max_length=120, db_index=True)
    base_link = models.TextField(blank=True)
    request_url = models.TextField(blank=True)
    townfrom = models.CharField(max_length=120, db_index=True)
    adult = models.PositiveSmallIntegerField(default=1, db_index=True)
    child = models.PositiveSmallIntegerField(default=0, db_index=True)
    night_min = models.PositiveSmallIntegerField(default=1, db_index=True)
    night_max = models.PositiveSmallIntegerField(default=1, db_index=True)
    checkin_beg = models.CharField(max_length=8, blank=True, db_index=True)
    checkin_end = models.CharField(max_length=8, blank=True)
    description = models.TextField(blank=True)
    functions = models.TextField(blank=True)
    trip_dates = models.CharField(max_length=80, blank=True)
    nights = models.CharField(max_length=20, blank=True)
    room = models.CharField(max_length=255, blank=True)
    meal = models.CharField(max_length=80, blank=True, db_index=True)
    placement = models.CharField(max_length=255, blank=True)
    price = models.CharField(max_length=80, blank=True)
    price_value = models.BigIntegerField(null=True, blank=True, db_index=True)
    booking_link = models.TextField(blank=True)
    raw_text = models.TextField(blank=True)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name='tour_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
            models.Index(fields=['country_slug', 'townfrom']),
            models.Index(fields=['adult', 'child']),
            models.Index(fields=['night_min', 'night_max']),
        ]

    def __str__(self) -> str:
        return f'{self.country_slug} | {self.townfrom} | {self.price}'
