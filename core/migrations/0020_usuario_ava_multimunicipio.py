from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0019_cliente_popup_eixos_ativo"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="ava_multimunicipio",
            field=models.BooleanField(
                default=False,
                help_text="Disponível para redatores. Quando ativo, limita a Gestão AVA aos municípios selecionados abaixo.",
                verbose_name="Permitir gestão de múltiplos municípios no AVA",
            ),
        ),
        migrations.AddField(
            model_name="usuario",
            name="ava_clientes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Municípios cujos AVAs este redator poderá visualizar e gerenciar.",
                related_name="redatores_ava_permitidos",
                to="core.cliente",
                verbose_name="Municípios permitidos na Gestão AVA",
            ),
        ),
    ]
