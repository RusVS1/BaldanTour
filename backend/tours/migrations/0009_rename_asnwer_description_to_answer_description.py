from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0008_recompute_asnwer_description"),
    ]

    operations = [
        migrations.RenameField(
            model_name="tour",
            old_name="asnwer_description",
            new_name="answer_description",
        ),
    ]

