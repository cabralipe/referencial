import ava.models.certificate
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ava", "0015_documentoacompanhamento_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="configcertificado",
            name="verso_ativo",
            field=models.BooleanField(
                default=False,
                help_text="Quando ativo, o PDF tera uma segunda pagina configuravel.",
                verbose_name="Incluir verso (segunda pagina)",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="verso_fundo",
            field=models.ImageField(
                blank=True,
                help_text="Imagem de fundo opcional para a segunda pagina.",
                null=True,
                upload_to=ava.models.certificate.certificado_fundo_upload_path,
                verbose_name="Fundo do verso",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="verso_template_html",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Aceita HTML e as mesmas variaveis da frente, como {{aluno_nome}}, "
                    "{{curso_nome}}, {{carga_horaria}} e {{codigo_validacao}}."
                ),
                verbose_name="Conteudo do verso (HTML)",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="verso_titulo",
            field=models.CharField(
                blank=True,
                default="Conteudo programatico",
                max_length=180,
                verbose_name="Titulo do verso",
            ),
        ),
    ]
