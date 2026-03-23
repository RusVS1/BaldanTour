from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):
    Tour = apps.get_model("tours", "Tour")

    Tour.objects.filter(hotel_type__iregex=r"(с\\s*детьми|для\\s*детей|дет)").update(
        hotel_type="Для детей"
    )
    Tour.objects.filter(
        hotel_type__iregex=r"(для\\s*взрослых|взросл|adults\\s*only|adult\\s*only)"
    ).update(hotel_type="Для взрослых")


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0010_drop_hotel_stars_use_hotel_category"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

