from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Quadro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("template", models.CharField(max_length=120)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quadros",
                        to="core.cliente",
                    ),
                ),
                (
                    "gt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quadros",
                        to="curriculum.gt",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CelulaQuadro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("linha", models.PositiveIntegerField()),
                ("coluna", models.PositiveIntegerField()),
                ("valor_html", models.TextField(blank=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="celulaquadros",
                        to="core.cliente",
                    ),
                ),
                (
                    "quadro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="celulas",
                        to="workshop.quadro",
                    ),
                ),
            ],
            options={"ordering": ("linha", "coluna")},
        ),
        migrations.AlterUniqueTogether(name="quadro", unique_together={("cliente", "gt", "template")}),
        migrations.AlterUniqueTogether(name="celulaquadro", unique_together={("quadro", "linha", "coluna")}),
    ]
