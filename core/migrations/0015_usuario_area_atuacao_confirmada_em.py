from django.db import migrations, models
from django.utils import timezone


GENERIC_SLUGS = {
    "diretor",
    "coordenador-pedagogico",
    "professor",
    "professor-geral",
}


def _marcar_usuarios_ja_especificados(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    TipoUsuarioCadastro = apps.get_model("core", "TipoUsuarioCadastro")

    tipos_especificos_ids = list(
        TipoUsuarioCadastro.objects.filter(ativo=True, is_deleted=False)
        .exclude(slug__in=GENERIC_SLUGS)
        .values_list("id", flat=True)
    )
    if not tipos_especificos_ids:
        return

    Usuario.objects.filter(
        tipo_cadastro_id__in=tipos_especificos_ids,
        area_atuacao_confirmada_em__isnull=True,
    ).update(area_atuacao_confirmada_em=timezone.now())


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_tipousuariocadastro_usuario_tipo_cadastro"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="area_atuacao_confirmada_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(_marcar_usuarios_ja_especificados, migrations.RunPython.noop),
    ]
