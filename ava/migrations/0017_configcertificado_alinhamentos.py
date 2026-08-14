from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ava", "0016_configcertificado_verso"),
    ]

    operations = [
        migrations.AlterField(
            model_name="configcertificado",
            name="subtitulo",
            field=models.TextField(
                blank=True,
                default="Certificamos que {{aluno_nome}} concluiu {{curso_nome}}.",
                verbose_name="Subtitulo impresso",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="subtitulo_alinhamento",
            field=models.CharField(
                choices=[
                    ("left", "Alinhado a esquerda"),
                    ("center", "Centralizado"),
                    ("right", "Alinhado a direita"),
                    ("justify", "Justificado"),
                ],
                default="center",
                max_length=10,
                verbose_name="Alinhamento do subtitulo",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="verso_alinhamento",
            field=models.CharField(
                choices=[
                    ("left", "Alinhado a esquerda"),
                    ("center", "Centralizado"),
                    ("right", "Alinhado a direita"),
                    ("justify", "Justificado"),
                ],
                default="left",
                max_length=10,
                verbose_name="Alinhamento do conteudo do verso",
            ),
        ),
    ]
