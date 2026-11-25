from django.db import migrations, models


def preencher_estrategias(apps, schema_editor):
    """Completa as salas já existentes sem modificar qualquer redação anterior."""
    Sala = apps.get_model("ava", "SalaGT")
    Linha = apps.get_model("ava", "LinhaPlanoEducacao")
    quantidades = (13, 24, 16, 16, 26, 15, 20, 25, 24, 31, 25, 15, 14, 18, 16, 14, 28, 12, 20)
    banco = schema_editor.connection.alias
    for numero, quantidade in enumerate(quantidades, 1):
        salas = Sala.objects.using(banco).filter(
            gt__isnull=True, is_deleted=False, objetivo__codigo=f"PNE-{numero:02}",
        )
        for sala in salas.iterator():
            principal = Linha.objects.using(banco).filter(
                sala_id=sala.pk, tipo="objetivo", codigo=str(numero), is_deleted=False,
            ).first()
            if principal is None:
                continue
            Linha.objects.using(banco).bulk_create([
                Linha(cliente_id=sala.cliente_id, sala_id=sala.pk,
                      objetivo_relacionado_id=principal.pk, tipo="estrategia",
                      codigo=f"{numero}.{indice}", ordem=indice, texto="")
                for indice in range(1, quantidade + 1)
            ], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("ava", "0026_plano_educacao_colaborativo")]
    operations = [
        migrations.RemoveConstraint(model_name="linhaplanoeducacao", name="uniq_linha_plano_codigo"),
        migrations.AddConstraint(
            model_name="linhaplanoeducacao",
            constraint=models.UniqueConstraint(fields=("sala", "tipo", "codigo"), name="uniq_linha_plano_tipo_codigo"),
        ),
        migrations.AlterField(
            model_name="linhaplanoeducacao", name="tipo",
            field=models.CharField(max_length=10, choices=[("objetivo", "Objetivo"), ("meta", "Meta"), ("estrategia", "Estratégia"), ("indicador", "Indicador")]),
        ),
        migrations.RunPython(preencher_estrategias, migrations.RunPython.noop),
    ]
