from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0008_area"),
    ]

    operations = [
        migrations.AddField(
            model_name="area",
            name="descricao_html",
            field=models.TextField(blank=True),
        ),
    ]
