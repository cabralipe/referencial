# Generated manually for the unified Diário de Bordo attendance flow.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ava", "0023_registroseminario_repassefrequencia")]

    operations = [
        migrations.AddField(
            model_name="diariobordo", name="escolas",
            field=models.ManyToManyField(blank=True, related_name="diarios_bordo_compartilhados", to="curriculum.escola", verbose_name="Escolas atendidas"),
        ),
        migrations.AddField(
            model_name="diariobordo", name="modo_frequencia",
            field=models.CharField(choices=[("presencial", "Lista presencial"), ("link", "Link e QR Code")], default="presencial", max_length=20, verbose_name="Como registrar a frequência"),
        ),
        migrations.AddField(
            model_name="encontrocurso", name="diario",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="encontro_frequencia", to="ava.diariobordo"),
        ),
        migrations.CreateModel(
            name="PresencaLinkDispositivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("dispositivo_hash", models.CharField(max_length=64)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="core.cliente")),
                ("encontro", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dispositivos_confirmados", to="ava.encontrocurso")),
            ],
        ),
        migrations.AddConstraint(
            model_name="presencalinkdispositivo",
            constraint=models.UniqueConstraint(fields=("encontro", "dispositivo_hash"), name="ava_presenca_link_dispositivo"),
        ),
    ]
