from django.db import migrations
from pgvector.django import VectorField


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0013_resize_embedding_dim_384"),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;", reverse_sql=""),
        migrations.RemoveField(model_name="tour", name="embedding"),
        migrations.AddField(
            model_name="tour",
            name="embedding",
            field=VectorField(blank=True, dimensions=768, null=True),
        ),
    ]

