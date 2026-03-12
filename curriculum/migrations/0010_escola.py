from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0009_area_descricao_html"),
    ]

    operations = [
        migrations.CreateModel(
            name="Escola",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("nome", models.CharField(max_length=255)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Escola",
                "verbose_name_plural": "Escolas",
                "ordering": ("nome",),
                "unique_together": {("cliente", "nome")},
            },
        ),
    ]
