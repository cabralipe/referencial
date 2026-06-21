from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_eixo_usuario_eixos"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="popup_eixos_ativo",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Quando ativo, exibe o popup obrigatório de seleção de eixos ao "
                    "entrar no catálogo do AVA para usuários que ainda não escolheram "
                    "seus eixos."
                ),
                verbose_name="Exibir popup de seleção de eixos no AVA",
            ),
        ),
    ]
