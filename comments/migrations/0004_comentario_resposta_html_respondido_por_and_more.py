from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comments", "0003_alter_comentario_alvo_tipo"),
    ]

    operations = [
        migrations.AddField(
            model_name="comentario",
            name="resposta_html",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="comentario",
            name="respondido_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="comentario",
            name="respondido_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="comentarios_respondidos",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
