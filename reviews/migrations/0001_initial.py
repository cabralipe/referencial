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
            name="Revisao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("alvo_tipo", models.CharField(choices=[("resposta", "Resposta"), ("texto_unico", "Texto Único"), ("quadro", "Quadro")], max_length=20)),
                ("alvo_id", models.CharField(max_length=36)),
                ("status", models.CharField(choices=[("rascunho", "Rascunho"), ("em_revisao", "Em revisão"), ("aprovado", "Aprovado"), ("reprovado", "Reprovado")], default="rascunho", max_length=20)),
                ("parecer_html", models.TextField(blank=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="revisaos", to="core.cliente")),
                ("revisor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="revisoes_revisor", to=settings.AUTH_USER_MODEL)),
                ("solicitante", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="revisoes_solicitadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.AddIndex(
            model_name="revisao",
            index=models.Index(fields=["cliente", "alvo_tipo", "alvo_id", "status"], name="reviews_rev_client_61a71c_idx"),
        ),
    ]
