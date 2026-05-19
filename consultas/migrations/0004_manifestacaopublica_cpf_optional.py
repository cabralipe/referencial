from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("consultas", "0003_manifestacaopublica_area_atuacao_profissional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="manifestacaopublica",
            name="cpf",
            field=models.CharField(blank=True, default="", max_length=14),
        ),
    ]
