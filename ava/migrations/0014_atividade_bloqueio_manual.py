from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ava", "0013_certificado_builder_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="atividade",
            name="acesso_bloqueado",
            field=models.BooleanField(
                default=False,
                help_text="Quando marcado, alunos nao conseguem abrir ou responder esta atividade.",
                verbose_name="Acesso bloqueado?",
            ),
        ),
        migrations.AddField(
            model_name="atividade",
            name="mensagem_bloqueio",
            field=models.TextField(
                blank=True,
                help_text="Mensagem exibida ao aluno. Se vazio, o aviso padrao de atividade bloqueada sera usado.",
                verbose_name="Mensagem de bloqueio",
            ),
        ),
    ]
