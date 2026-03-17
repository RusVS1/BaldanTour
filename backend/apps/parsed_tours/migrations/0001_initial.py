from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ParsedCountry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ParsedAvailableTour",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_hash", models.CharField(max_length=64, unique=True)),
                ("base_link", models.TextField(blank=True, default="")),
                ("request_url", models.TextField(blank=True, default="")),
                ("townfrom", models.CharField(blank=True, default="", max_length=128)),
                ("adult", models.IntegerField(blank=True, null=True)),
                ("child", models.IntegerField(blank=True, null=True)),
                ("night_min", models.IntegerField(blank=True, null=True)),
                ("night_max", models.IntegerField(blank=True, null=True)),
                ("checkin_beg", models.DateField(blank=True, null=True)),
                ("checkin_end", models.DateField(blank=True, null=True)),
                ("description", models.TextField(blank=True, default="")),
                ("functions", models.TextField(blank=True, default="")),
                ("trip_dates", models.TextField(blank=True, default="")),
                ("nights", models.CharField(blank=True, default="", max_length=64)),
                ("room", models.CharField(blank=True, default="", max_length=255)),
                ("meal", models.CharField(blank=True, default="", max_length=255)),
                ("placement", models.CharField(blank=True, default="", max_length=255)),
                ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("booking_link", models.TextField(blank=True, default="")),
                ("raw_text", models.TextField(blank=True, default="")),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("embedding_version", models.CharField(blank=True, default="", max_length=32)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                (
                    "country",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tours",
                        to="parsed_tours.parsedcountry",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["country", "checkin_beg"], name="parsed_tour_country_82c9f9_idx"),
                    models.Index(fields=["country", "price"], name="parsed_tour_country_d2d02a_idx"),
                ],
            },
        ),
    ]

