from __future__ import annotations

import hashlib
import re

from django.db import migrations


_INFRA_RE = re.compile(r"\bинфраструктура\b", flags=re.IGNORECASE)
_RULES_RE = re.compile(r"правила\s+размещения\s+в\s+отелях", flags=re.IGNORECASE)


def _extract_answer(target: str) -> str:
    target = (target or "").strip()
    if not target:
        return ""
    m = _INFRA_RE.search(target)
    if not m:
        extracted = target
    else:
        extracted = target[: m.start()].strip()
    return _RULES_RE.sub("", extracted).strip()


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
        Tour.objects.update(asnwer_description=None)
        return

    existing = dict(
        TourText.objects.filter(sha256__in=list(need_hashes.keys())).values_list("sha256", "id")
    )
    missing = [h for h in need_hashes.keys() if h not in existing]
    if missing:
        TourText.objects.bulk_create(
            [TourText(sha256=h, content=need_hashes[h]) for h in missing],
            ignore_conflicts=True,
        )
        existing = dict(
            TourText.objects.filter(sha256__in=list(need_hashes.keys())).values_list("sha256", "id")
        )

    for tour_id, h in tour_to_hash.items():
        text_id = existing.get(h)
        if text_id:
            Tour.objects.filter(id=tour_id).update(asnwer_description_id=text_id)


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0007_tour_asnwer_description"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

