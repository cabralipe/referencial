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
            name="Midia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("url", models.URLField()),
                ("legenda", models.CharField(blank=True, max_length=255)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="midias", to="core.cliente")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="midias_enviadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="BlocoTexto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("titulo", models.CharField(max_length=255)),
                ("conteudo_html", models.TextField()),
                ("tags", models.JSONField(blank=True, default=list)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="blocotextos", to="core.cliente")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blocos_criados", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("titulo",)},
        ),
        migrations.AddIndex(
            model_name="midia",
            index=models.Index(fields=["cliente", "created_at"], name="library_m_cliente_03a20a_idx"),
        ),
        migrations.AddIndex(
            model_name="blocotexto",
            index=models.Index(fields=["cliente", "titulo"], name="library_bl_cliente_33706f_idx"),
        ),
    ]
