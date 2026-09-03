import ava.models.certificate
from django.db import migrations, models


def corrigir_titulo_padrao_verso(apps, schema_editor):
    ConfigCertificado = apps.get_model("ava", "ConfigCertificado")
    ConfigCertificado.objects.filter(verso_titulo="Conteudo programatico").update(
        verso_titulo="Conteúdo programático"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ava", "0017_configcertificado_alinhamentos"),
    ]

    operations = [
        migrations.RunPython(corrigir_titulo_padrao_verso, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="configcertificado",
            options={
                "verbose_name": "Configuração de Certificado",
                "verbose_name_plural": "Configurações de Certificados",
            },
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="titulo",
            field=models.CharField(default="Certificado", max_length=180, verbose_name="Título impresso"),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="subtitulo",
            field=models.TextField(
                blank=True,
                default="Certificamos que {{aluno_nome}} concluiu {{curso_nome}}.",
                verbose_name="Subtítulo impresso",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="subtitulo_alinhamento",
            field=models.CharField(
                choices=[
                    ("left", "Alinhado à esquerda"),
                    ("center", "Centralizado"),
                    ("right", "Alinhado à direita"),
                    ("justify", "Justificado"),
                ],
                default="center",
                max_length=10,
                verbose_name="Alinhamento do subtítulo",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="template_html",
            field=models.TextField(
                blank=True,
                help_text="Opcional. Variáveis permitidas: {{aluno_nome}}, {{curso_nome}}, {{carga_horaria}}, {{data_emissao}}, etc.",
                verbose_name="Template HTML",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="carga_horaria_impressa",
            field=models.PositiveIntegerField(
                default=0,
                help_text="0 para usar a carga horária original do curso/trilha.",
                verbose_name="Carga horária impressa",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="campos_variaveis",
            field=models.JSONField(
                blank=True,
                default=ava.models.certificate.default_certificate_variables,
                help_text="Lista dos campos do usuário/curso que serão exibidos no certificado.",
                verbose_name="Campos variáveis impressos",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="fundo",
            field=models.ImageField(
                blank=True,
                help_text="Imagem de fundo opcional. Se não enviada, o tema padrão será usado.",
                null=True,
                upload_to=ava.models.certificate.certificado_fundo_upload_path,
                verbose_name="Fundo do certificado",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="verso_ativo",
            field=models.BooleanField(
                default=False,
                help_text="Quando ativo, o PDF terá uma segunda página configurável.",
                verbose_name="Incluir verso (segunda página)",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="verso_titulo",
            field=models.CharField(
                blank=True,
                default="Conteúdo programático",
                max_length=180,
                verbose_name="Título do verso",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="verso_template_html",
            field=models.TextField(
                blank=True,
                help_text="Aceita HTML e as mesmas variáveis da frente, como {{aluno_nome}}, {{curso_nome}}, {{carga_horaria}} e {{codigo_validacao}}.",
                verbose_name="Conteúdo do verso (HTML)",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="verso_alinhamento",
            field=models.CharField(
                choices=[
                    ("left", "Alinhado à esquerda"),
                    ("center", "Centralizado"),
                    ("right", "Alinhado à direita"),
                    ("justify", "Justificado"),
                ],
                default="left",
                max_length=10,
                verbose_name="Alinhamento do conteúdo do verso",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="verso_fundo",
            field=models.ImageField(
                blank=True,
                help_text="Imagem de fundo opcional para a segunda página.",
                null=True,
                upload_to=ava.models.certificate.certificado_fundo_upload_path,
                verbose_name="Fundo do verso",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="tema_padrao",
            field=models.CharField(
                choices=[
                    ("classico", "Clássico"),
                    ("moderno", "Moderno"),
                    ("institucional", "Institucional"),
                ],
                default="classico",
                max_length=30,
                verbose_name="Tema padrão",
            ),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="texto_x",
            field=models.PositiveSmallIntegerField(default=50, verbose_name="Posição horizontal do texto (%)"),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="texto_y",
            field=models.PositiveSmallIntegerField(default=42, verbose_name="Posição vertical do texto (%)"),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="titulo_tamanho",
            field=models.PositiveSmallIntegerField(default=42, verbose_name="Tamanho do título"),
        ),
        migrations.AlterField(
            model_name="configcertificado",
            name="quantidade_assinaturas",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="Define os espaços proporcionais; cadastre imagens nas assinaturas abaixo quando houver PNG.",
                verbose_name="Quantidade de assinaturas",
            ),
        ),
        migrations.AlterField(
            model_name="assinaturacertificado",
            name="imagem",
            field=models.ImageField(
                blank=True,
                help_text="Opcional. Sem imagem, o sistema mantém apenas o campo para assinatura.",
                null=True,
                upload_to=ava.models.certificate.certificado_assinatura_upload_path,
                verbose_name="Imagem PNG da assinatura",
            ),
        ),
        migrations.AlterField(
            model_name="assinaturacertificado",
            name="x",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="0 usa distribuição automática.",
                verbose_name="Posição horizontal (%)",
            ),
        ),
        migrations.AlterField(
            model_name="assinaturacertificado",
            name="y",
            field=models.PositiveSmallIntegerField(default=78, verbose_name="Posição vertical (%)"),
        ),
        migrations.AlterField(
            model_name="certificado",
            name="codigo_validacao",
            field=models.CharField(blank=True, max_length=64, unique=True, verbose_name="Código único de validação"),
        ),
        migrations.AlterField(
            model_name="certificado",
            name="data_emissao",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Data de emissão"),
        ),
        migrations.AlterField(
            model_name="certificado",
            name="liberado_em",
            field=models.DateTimeField(
                blank=True,
                help_text="Em branco mantém o certificado oculto para o cursista.",
                null=True,
                verbose_name="Liberado no AVA em",
            ),
        ),
        migrations.AlterField(
            model_name="certificado",
            name="carga_horaria",
            field=models.PositiveIntegerField(default=0, verbose_name="Carga horária"),
        ),
    ]
