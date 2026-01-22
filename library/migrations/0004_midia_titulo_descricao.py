from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0003_biblioteca_gt_pergunta"),
    ]

    operations = [
        migrations.RenameField(
            model_name="midia",
            old_name="legenda",
            new_name="descricao",
        ),
        migrations.AddField(
            model_name="midia",
            name="titulo",
            field=models.CharField(blank=True, max_length=255, default=""),
            preserve_default=False,
        ),
    ]
