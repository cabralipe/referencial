from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "alvo_tipo",
                    models.CharField(
                        choices=[("texto_unico", "Texto Único"), ("quadro", "Quadro")],
                        max_length=20,
                    ),
                ),
                ("alvo_id", models.CharField(max_length=36)),
                (
                    "formato",
                    models.CharField(
                        choices=[("pdf", "PDF"), ("docx", "DOCX")],
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Na fila"),
                            ("running", "Em execução"),
                            ("done", "Concluído"),
                            ("error", "Erro"),
                        ],
                        default="queued",
                        max_length=10,
                    ),
                ),
                ("url_resultado", models.URLField(blank=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="exportjobs",
                        to="core.cliente",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
