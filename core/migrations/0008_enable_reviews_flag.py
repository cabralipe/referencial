from django.db import migrations


def enable_reviews_flag(apps, schema_editor):
    Cliente = apps.get_model("core", "Cliente")
    ClienteFeatureFlag = apps.get_model("core", "ClienteFeatureFlag")
    flags = [
        "ff.reviews.enabled",
        "ff.comments.enabled",
        "ff.notifications.enabled",
        "ff.diff.enabled",
        "ff.library.enabled",
    ]
    for cliente in Cliente.objects.all():
        for flag in flags:
            ClienteFeatureFlag.objects.update_or_create(
                cliente=cliente,
                flag=flag,
                defaults={"ativo": True},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_rename_core_scoree_cliente_usu_49f9df_idx_core_scoree_cliente_1cb5ea_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(enable_reviews_flag, migrations.RunPython.noop),
    ]
