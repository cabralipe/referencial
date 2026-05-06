from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_muralarquivoenvio"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MuralDownloadRegistro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("mural_id", models.CharField(max_length=64)),
                ("anexo_index", models.PositiveIntegerField(default=0)),
                ("anexo_titulo", models.CharField(blank=True, max_length=255)),
                ("anexo_url", models.URLField(blank=True, max_length=1000)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(class)ss",
                        to="core.cliente",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mural_downloads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro de download do mural",
                "verbose_name_plural": "Registros de downloads do mural",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="muraldownloadregistro",
            index=models.Index(fields=["cliente", "mural_id", "created_at"], name="notificatio_cliente_02716b_idx"),
        ),
        migrations.AddIndex(
            model_name="muraldownloadregistro",
            index=models.Index(fields=["cliente", "usuario", "created_at"], name="notificatio_cliente_2d2101_idx"),
        ),
    ]
