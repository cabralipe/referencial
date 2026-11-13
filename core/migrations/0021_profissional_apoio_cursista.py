from django.db import migrations


def corrigir_profissionais_de_apoio(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    TipoUsuarioCadastro = apps.get_model("core", "TipoUsuarioCadastro")
    tipo_ids = TipoUsuarioCadastro.objects.filter(
        seguimento="profissional_apoio"
    ).values_list("id", flat=True)
    TipoUsuarioCadastro.objects.filter(id__in=tipo_ids).update(role_interno="leitor")
    Usuario.objects.filter(seguimento="profissional_apoio").update(role="leitor")
    Usuario.objects.filter(tipo_cadastro_id__in=tipo_ids).update(
        role="leitor", seguimento="profissional_apoio"
    )


def reverter_profissionais_de_apoio(apps, schema_editor):
    # Não restaura papel de professor automaticamente: isso reabriria acessos indevidos.
    pass


class Migration(migrations.Migration):
    dependencies = [("core", "0020_usuario_ava_multimunicipio")]

    operations = [migrations.RunPython(corrigir_profissionais_de_apoio, reverter_profissionais_de_apoio)]
