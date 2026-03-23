from __future__ import annotations

import hashlib
import re

from django.db import migrations, models


_INFRA_RE = re.compile(r"\bинфраструктура\b", flags=re.IGNORECASE)


def _extract_answer(target: str) -> str:
    target = (target or "").strip()
    if not target:
        return ""
    m = _INFRA_RE.search(target)
    if not m:
        return target
    return target[: m.start()].strip()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def forwards(apps, schema_editor):
    Tour = apps.get_model("tours", "Tour")
    TourText = apps.get_model("tours", "TourText")

    tours = (
        Tour.objects.select_related("target_description")
        .filter(target_description__isnull=False)
        .only("id", "target_description")
    )

    # 1) prepare texts to create
    need_hashes: dict[str, str] = {}
    tour_to_hash: dict[int, str] = {}
    for tour in tours.iterator():
        content = getattr(getattr(tour, "target_description", None), "content", "") or ""
        extracted = _extract_answer(content)
        if not extracted:
            continue
        h = _sha256(extracted)
        tour_to_hash[tour.id] = h
        if h not in need_hashes:
            need_hashes[h] = extracted

    if not need_hashes:
        return

    existing = dict(TourText.objects.filter(sha256__in=list(need_hashes.keys())).values_list("sha256", "id"))
    missing = [h for h in need_hashes.keys() if h not in existing]
    if missing:
        TourText.objects.bulk_create(
            [TourText(sha256=h, content=need_hashes[h]) for h in missing],
            ignore_conflicts=True,
        )
        existing = dict(
            TourText.objects.filter(sha256__in=list(need_hashes.keys())).values_list("sha256", "id")
        )

    # 2) assign FK
    to_update = []
    for tour_id, h in tour_to_hash.items():
        text_id = existing.get(h)
        if text_id:
            to_update.append((tour_id, text_id))

    if to_update:
        # bulk update via queryset
        for tour_id, text_id in to_update:
            Tour.objects.filter(id=tour_id).update(asnwer_description_id=text_id)


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0006_tourimage_country_ru_townfrom_ru_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tour",
            name="asnwer_description",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="answer_for",
                to="tours.tourtext",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

