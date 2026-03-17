from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parsed_tours", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parsedavailabletour",
            name="embedding_version",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]

