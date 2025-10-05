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
            name="Comentario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("alvo_tipo", models.CharField(choices=[("resposta", "Resposta"), ("texto_unico", "Texto Único"), ("quadro", "Quadro")], max_length=20)),
                ("alvo_id", models.CharField(max_length=36)),
                ("anchor_json", models.JSONField(default=dict)),
                ("conteudo_html", models.TextField()),
                ("resolvido", models.BooleanField(default=False)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="comentarios", to="core.cliente")),
                ("autor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comentarios", to=settings.AUTH_USER_MODEL)),
                ("mentions", models.ManyToManyField(blank=True, related_name="comentarios_mencionado", to=settings.AUTH_USER_MODEL)),
                ("resolvido_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="comentarios_resolvidos", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.AddIndex(
            model_name="comentario",
            index=models.Index(fields=["cliente", "alvo_tipo", "alvo_id", "resolvido"], name="comments_co_client_5c71c2_idx"),
        ),
    ]
