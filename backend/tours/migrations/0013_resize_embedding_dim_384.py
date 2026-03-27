from django.db import migrations
from pgvector.django import VectorField


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0012_tour_embedding_pgvector"),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;", reverse_sql=""),
        migrations.RemoveField(model_name="tour", name="embedding"),
        migrations.AddField(
            model_name="tour",
            name="embedding",
            field=VectorField(blank=True, dimensions=384, null=True),
        ),
    ]

