from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("consultas", "0007_formularioinscricao_imagem_hero"),
    ]

    operations = [
        migrations.AddField(
            model_name="formularioinscricao",
            name="campos_config",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Configuração dos campos do formulário. "
                    "Formato: [{chave, label, tipo, obrigatorio, ordem, ativo, padrao, opcoes}]"
                ),
            ),
        ),
        migrations.AddField(
            model_name="inscricaopublica",
            name="dados_extras",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Respostas dos campos customizados.",
            ),
        ),
    ]
