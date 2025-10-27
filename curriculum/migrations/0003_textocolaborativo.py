from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0002_alter_gt_options_and_more"),
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TextoColaborativo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("titulo", models.CharField(max_length=255)),
                ("conteudo_html", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "autor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="textos_colaborativos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="textocolaborativos",
                        to="core.cliente",
                    ),
                ),
                (
                    "gt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="textos_colaborativos",
                        to="curriculum.gt",
                    ),
                ),
            ],
            options={
                "ordering": ("-updated_at",),
                "indexes": [models.Index(fields=["cliente", "gt"], name="textocolab_cliente_gt_idx")],
            },
        ),
    ]
