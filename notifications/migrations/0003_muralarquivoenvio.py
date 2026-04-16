from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import notifications.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_merge_20260410_0001"),
        ("curriculum", "0011_ppp"),
        ("notifications", "0002_rename_notificac_client_4468a1_idx_notificatio_cliente_708015_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MuralArquivoEnvio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("mural_id", models.CharField(max_length=64)),
                ("arquivo", models.FileField(upload_to=notifications.models.mural_envio_upload_to)),
                ("nome_original", models.CharField(blank=True, max_length=255)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="core.cliente")),
                ("gt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mural_envios_arquivo", to="curriculum.gt")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mural_envios_arquivo", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-updated_at",),
            },
        ),
        migrations.AddIndex(
            model_name="muralarquivoenvio",
            index=models.Index(fields=["cliente", "mural_id", "updated_at"], name="notificatio_cliente_4d63d2_idx"),
        ),
        migrations.AddIndex(
            model_name="muralarquivoenvio",
            index=models.Index(fields=["cliente", "usuario", "updated_at"], name="notificatio_cliente_0c86fb_idx"),
        ),
        migrations.AddConstraint(
            model_name="muralarquivoenvio",
            constraint=models.UniqueConstraint(fields=("cliente", "mural_id", "usuario", "gt"), name="uniq_mural_envio_por_usuario_gt"),
        ),
    ]
