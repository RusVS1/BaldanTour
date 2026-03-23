from __future__ import annotations

from django.db import migrations
from django.db.models import F


def forwards(apps, schema_editor):
    Tour = apps.get_model("tours", "Tour")
    # hotel_category becomes the previous hotel_stars value (including NULLs).
    # This intentionally overwrites any previously inferred values.
    Tour.objects.update(hotel_category=F("hotel_stars"))


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0009_rename_asnwer_description_to_answer_description"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="tour",
            name="hotel_stars",
        ),
    ]
