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
            name="Notificacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("tipo", models.CharField(max_length=50)),
                ("payload_json", models.JSONField(default=dict)),
                ("lida", models.BooleanField(default=False)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notificacaos", to="core.cliente")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notificacoes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="notificacao",
            index=models.Index(fields=["cliente", "usuario", "lida", "created_at"], name="notificac_client_4468a1_idx"),
        ),
    ]
