from django.db import migrations, models


def populate_usuario_clientes(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    through_model = Usuario.clientes.through
    batch = []
    for usuario in Usuario.objects.exclude(cliente_id__isnull=True).values("id", "cliente_id"):
        batch.append(
            through_model(
                usuario_id=usuario["id"],
                cliente_id=usuario["cliente_id"],
            )
        )
    if batch:
        through_model.objects.bulk_create(batch, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_usuario_seguimento"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="clientes",
            field=models.ManyToManyField(blank=True, related_name="usuarios_permitidos", to="core.cliente"),
        ),
        migrations.RunPython(populate_usuario_clientes, migrations.RunPython.noop),
    ]
