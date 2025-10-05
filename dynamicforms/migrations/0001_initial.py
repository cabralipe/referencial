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
            name="FormularioDinamico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("nome", models.CharField(max_length=150)),
                ("descricao", models.TextField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="formularios_dinamicos",
                        to="core.cliente",
                    ),
                ),
            ],
            options={"ordering": ("nome",)},
        ),
        migrations.CreateModel(
            name="CampoDinamico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("chave", models.SlugField()),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("texto", "Texto"),
                            ("select", "Seleção"),
                            ("upload", "Upload"),
                            ("inteiro", "Inteiro"),
                            ("decimal", "Decimal"),
                            ("bool", "Booleano"),
                        ],
                        max_length=20,
                    ),
                ),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("obrigatorio", models.BooleanField(default=False)),
                ("ordem", models.PositiveIntegerField(default=0)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="campos_dinamicos",
                        to="core.cliente",
                    ),
                ),
                (
                    "formulario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campos",
                        to="dynamicforms.formulariodinamico",
                    ),
                ),
            ],
            options={"ordering": ("ordem",)},
        ),
        migrations.CreateModel(
            name="RespostaCampoDinamico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("valor_texto", models.TextField(blank=True)),
                ("valor_num", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("valor_bool", models.BooleanField(blank=True, null=True)),
                ("url_arquivo", models.URLField(blank=True)),
                (
                    "owner_type",
                    models.CharField(
                        choices=[
                            ("resposta", "Resposta"),
                            ("texto_unico", "Texto Único"),
                            ("quadro", "Quadro"),
                        ],
                        max_length=20,
                    ),
                ),
                ("owner_id", models.CharField(max_length=36)),
                (
                    "campo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respostas",
                        to="dynamicforms.campodinamico",
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respostas_dinamicas",
                        to="core.cliente",
                    ),
                ),
                (
                    "formulario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respostas_campo",
                        to="dynamicforms.formulariodinamico",
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(name="formulariodinamico", unique_together={("cliente", "nome")}),
        migrations.AlterUniqueTogether(name="campodinamico", unique_together={("formulario", "chave")}),
        migrations.AlterUniqueTogether(name="respostacampodinamico", unique_together={("campo", "owner_type", "owner_id")}),
    ]
