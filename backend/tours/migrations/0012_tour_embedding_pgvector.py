from django.db import migrations
from pgvector.django import VectorField


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0011_normalize_hotel_type_labels"),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;", reverse_sql=""),
        migrations.AddField(
            model_name="tour",
            name="embedding",
            field=VectorField(blank=True, dimensions=1536, null=True),
        ),
    ]

