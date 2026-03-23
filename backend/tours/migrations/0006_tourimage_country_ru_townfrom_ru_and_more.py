from __future__ import annotations

import hashlib

from django.db import migrations, models


COUNTRY_SLUG_TO_RU = {
    "abkhazia": "Абхазия",
    "armenia": "Армения",
    "belarus": "Беларусь",
    "china": "Китай",
    "georgia": "Грузия",
    "maldives": "Мальдивы",
    "russia": "Россия",
    "spain": "Испания",
}

TOWNFROM_SLUG_TO_RU = {
    "moskva": "Москва",
    "moscow": "Москва",
    "kaliningrad": "Калининград",
    "spb": "Санкт-Петербург",
    "sankt-peterburg": "Санкт-Петербург",
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def forwards(apps, schema_editor):
    Tour = apps.get_model("tours", "Tour")
    TourImage = apps.get_model("tours", "TourImage")

    existing_images = dict(TourImage.objects.values_list("sha256", "id"))
    images_to_create = []

    tours_to_update = []
    for tour in Tour.objects.all().only(
        "id",
        "country_slug",
        "country_ru",
        "townfrom",
        "townfrom_ru",
        "main_image_url",
    ):
        if not (tour.country_ru or "").strip():
            tour.country_ru = COUNTRY_SLUG_TO_RU.get(tour.country_slug, tour.country_slug or "")
        if not (tour.townfrom_ru or "").strip():
            tour.townfrom_ru = TOWNFROM_SLUG_TO_RU.get(tour.townfrom, tour.townfrom or "")

        url = (getattr(tour, "main_image_url", None) or "").strip()
        img_hash = None
        if url:
            img_hash = _sha256(url)
            if img_hash not in existing_images:
                existing_images[img_hash] = None
                images_to_create.append(TourImage(sha256=img_hash, url=url))
        setattr(tour, "_img_hash", img_hash)
        tours_to_update.append(tour)

    if images_to_create:
        TourImage.objects.bulk_create(images_to_create, ignore_conflicts=True)
        existing_images = dict(TourImage.objects.values_list("sha256", "id"))

    for tour in tours_to_update:
        img_hash = getattr(tour, "_img_hash", None)
        if img_hash:
            tour.main_image_id = existing_images.get(img_hash)

    if tours_to_update:
        Tour.objects.bulk_update(tours_to_update, ["country_ru", "townfrom_ru", "main_image"])


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0005_tourtext_remove_tour_description_tour_hotel_name_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TourImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sha256", models.CharField(max_length=64, unique=True)),
                ("url", models.URLField(max_length=2000)),
            ],
        ),
        migrations.AddField(
            model_name="tour",
            name="country_ru",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name="tour",
            name="townfrom_ru",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name="tour",
            name="main_image",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="tours", to="tours.tourimage"),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="tour",
            name="main_image_url",
        ),
    ]
