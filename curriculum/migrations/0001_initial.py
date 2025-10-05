from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GT",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("nome", models.CharField(max_length=255)),
                ("etapa", models.CharField(max_length=120)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gts",
                        to="core.cliente",
                    ),
                ),
            ],
            options={"ordering": ("nome",)},
        ),
        migrations.CreateModel(
            name="Tarefa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("ordem", models.PositiveIntegerField()),
                ("etapa", models.CharField(blank=True, max_length=120)),
                (
                    "tipo",
                    models.CharField(
                        choices=[("PERGUNTAS", "Perguntas"), ("OFICINA", "Oficina")],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("rascunho", "Rascunho"),
                            ("em_revisao", "Em revisão"),
                            ("concluida", "Concluída"),
                        ],
                        default="rascunho",
                        max_length=20,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tarefas",
                        to="core.cliente",
                    ),
                ),
            ],
            options={"ordering": ("ordem",)},
        ),
        migrations.CreateModel(
            name="Pergunta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("ordem", models.PositiveIntegerField()),
                ("texto", models.TextField()),
                ("permite_upload", models.BooleanField(default=False)),
                ("obrigatoria", models.BooleanField(default=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="perguntas",
                        to="core.cliente",
                    ),
                ),
                (
                    "tarefa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perguntas",
                        to="curriculum.tarefa",
                    ),
                ),
            ],
            options={"ordering": ("ordem",)},
        ),
        migrations.CreateModel(
            name="TextoUnico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("conteudo_html", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="textos_unicos",
                        to="core.cliente",
                    ),
                ),
                (
                    "gt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="textos_unicos",
                        to="curriculum.gt",
                    ),
                ),
                (
                    "responsavel",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="textos_unicos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tarefa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="textos_unicos",
                        to="curriculum.tarefa",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Resposta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("conteudo_html", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "autor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="respostas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respostas",
                        to="core.cliente",
                    ),
                ),
                (
                    "gt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respostas",
                        to="curriculum.gt",
                    ),
                ),
                (
                    "pergunta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respostas",
                        to="curriculum.pergunta",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Anexo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("url", models.URLField()),
                ("legenda", models.CharField(blank=True, max_length=255)),
                ("ordem", models.PositiveIntegerField(default=0)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="anexos",
                        to="core.cliente",
                    ),
                ),
                (
                    "resposta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="anexos",
                        to="curriculum.resposta",
                    ),
                ),
            ],
            options={"ordering": ("ordem",)},
        ),
        migrations.AddField(
            model_name="gt",
            name="membros",
            field=models.ManyToManyField(blank=True, related_name="grupos_trabalho", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name="resposta",
            index=models.Index(fields=["cliente", "gt", "pergunta"], name="curr_res_client_8be6f8_idx"),
        ),
        migrations.AddIndex(
            model_name="textounico",
            index=models.Index(fields=["cliente", "gt", "tarefa"], name="curr_text_cliente_3baf05_idx"),
        ),
        migrations.AlterUniqueTogether(name="tarefa", unique_together={("cliente", "ordem", "tipo")}),
        migrations.AlterUniqueTogether(name="pergunta", unique_together={("tarefa", "ordem")}),
        migrations.AlterUniqueTogether(name="resposta", unique_together={("cliente", "gt", "pergunta")}),
        migrations.AlterUniqueTogether(name="textounico", unique_together={("cliente", "gt", "tarefa")}),
    ]
