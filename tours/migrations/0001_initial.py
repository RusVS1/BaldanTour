from django.conf import settings
from django.db import migrations, models
import pgvector.django.indexes
import pgvector.django.vector


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL('CREATE EXTENSION IF NOT EXISTS vector;', reverse_sql='DROP EXTENSION IF EXISTS vector;'),
        migrations.CreateModel(
            name='Tour',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_key', models.CharField(max_length=64, unique=True)),
                ('country_slug', models.CharField(db_index=True, max_length=120)),
                ('base_link', models.TextField(blank=True)),
                ('request_url', models.TextField(blank=True)),
                ('townfrom', models.CharField(db_index=True, max_length=120)),
                ('adult', models.PositiveSmallIntegerField(db_index=True, default=1)),
                ('child', models.PositiveSmallIntegerField(db_index=True, default=0)),
                ('night_min', models.PositiveSmallIntegerField(db_index=True, default=1)),
                ('night_max', models.PositiveSmallIntegerField(db_index=True, default=1)),
                ('checkin_beg', models.CharField(blank=True, db_index=True, max_length=8)),
                ('checkin_end', models.CharField(blank=True, max_length=8)),
                ('description', models.TextField(blank=True)),
                ('functions', models.TextField(blank=True)),
                ('trip_dates', models.CharField(blank=True, max_length=80)),
                ('nights', models.CharField(blank=True, max_length=20)),
                ('room', models.CharField(blank=True, max_length=255)),
                ('meal', models.CharField(blank=True, db_index=True, max_length=80)),
                ('placement', models.CharField(blank=True, max_length=255)),
                ('price', models.CharField(blank=True, max_length=80)),
                ('price_value', models.BigIntegerField(blank=True, db_index=True, null=True)),
                ('booking_link', models.TextField(blank=True)),
                ('raw_text', models.TextField(blank=True)),
                ('embedding', pgvector.django.vector.VectorField(blank=True, dimensions=settings.EMBEDDING_DIM, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'indexes': [
                    pgvector.django.indexes.HnswIndex(
                        ef_construction=64,
                        fields=['embedding'],
                        m=16,
                        name='tour_embedding_hnsw_idx',
                        opclasses=['vector_cosine_ops'],
                    ),
                    models.Index(fields=['country_slug', 'townfrom'], name='tours_tour_country_2af164_idx'),
                    models.Index(fields=['adult', 'child'], name='tours_tour_adult_98f1f1_idx'),
                    models.Index(fields=['night_min', 'night_max'], name='tours_tour_night_mi_6d884a_idx'),
                ]
            },
        ),
    ]
