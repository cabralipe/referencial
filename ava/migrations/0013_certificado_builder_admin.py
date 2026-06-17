# Generated manually for certificate builder admin.

import ava.models.certificate
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ava", "0012_atividade_eixos_atividade_eixos_restricao_roles"),
        ("core", "0018_eixo_usuario_eixos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="configcertificado",
            name="campos_variaveis",
            field=models.JSONField(
                blank=True,
                default=ava.models.certificate.default_certificate_variables,
                help_text="Lista dos campos do usuario/curso que serao exibidos no certificado.",
                verbose_name="Campos variaveis impressos",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="cor_texto",
            field=models.CharField(default="#1f2937", max_length=7, verbose_name="Cor do texto"),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="fundo",
            field=models.ImageField(
                blank=True,
                help_text="Imagem de fundo opcional. Se nao enviada, o tema padrao sera usado.",
                null=True,
                upload_to=ava.models.certificate.certificado_fundo_upload_path,
                verbose_name="Fundo do certificado",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="quantidade_assinaturas",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="Define os espacos proporcionais; cadastre imagens nas assinaturas abaixo quando houver PNG.",
                verbose_name="Quantidade de assinaturas",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="subtitulo",
            field=models.CharField(
                blank=True,
                default="Certificamos que {{aluno_nome}} concluiu {{curso_nome}}.",
                max_length=255,
                verbose_name="Subtitulo impresso",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="tema_padrao",
            field=models.CharField(
                choices=[
                    ("classico", "Classico"),
                    ("moderno", "Moderno"),
                    ("institucional", "Institucional"),
                ],
                default="classico",
                max_length=30,
                verbose_name="Tema padrao",
            ),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="texto_largura",
            field=models.PositiveSmallIntegerField(default=72, verbose_name="Largura do bloco de texto (%)"),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="texto_tamanho",
            field=models.PositiveSmallIntegerField(default=18, verbose_name="Tamanho do texto"),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="texto_x",
            field=models.PositiveSmallIntegerField(default=50, verbose_name="Posicao horizontal do texto (%)"),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="texto_y",
            field=models.PositiveSmallIntegerField(default=42, verbose_name="Posicao vertical do texto (%)"),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="titulo",
            field=models.CharField(default="Certificado", max_length=180, verbose_name="Titulo impresso"),
        ),
        migrations.AddField(
            model_name="configcertificado",
            name="titulo_tamanho",
            field=models.PositiveSmallIntegerField(default=42, verbose_name="Tamanho do titulo"),
        ),
        migrations.AddField(
            model_name="certificado",
            name="config",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="certificados",
                to="ava.configcertificado",
            ),
        ),
        migrations.AddField(
            model_name="certificado",
            name="emitido_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="certificados_emitidos_ava",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="certificado",
            name="liberado_em",
            field=models.DateTimeField(
                blank=True,
                help_text="Em branco mantem o certificado oculto para o cursista.",
                null=True,
                verbose_name="Liberado no AVA em",
            ),
        ),
        migrations.CreateModel(
            name="AssinaturaCertificado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("titulo", models.CharField(blank=True, max_length=150, verbose_name="Nome/assinatura")),
                ("cargo", models.CharField(blank=True, max_length=150, verbose_name="Cargo")),
                (
                    "imagem",
                    models.ImageField(
                        blank=True,
                        help_text="Opcional. Sem imagem, o sistema mantem apenas o campo para assinatura.",
                        null=True,
                        upload_to=ava.models.certificate.certificado_assinatura_upload_path,
                        verbose_name="Imagem PNG da assinatura",
                    ),
                ),
                ("ordem", models.PositiveSmallIntegerField(default=1, verbose_name="Ordem")),
                (
                    "x",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="0 usa distribuicao automatica.",
                        verbose_name="Posicao horizontal (%)",
                    ),
                ),
                ("y", models.PositiveSmallIntegerField(default=78, verbose_name="Posicao vertical (%)")),
                ("largura", models.PositiveSmallIntegerField(default=22, verbose_name="Largura (%)")),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assinaturacertificados",
                        to="core.cliente",
                    ),
                ),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assinaturas",
                        to="ava.configcertificado",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assinatura de Certificado",
                "verbose_name_plural": "Assinaturas de Certificado",
                "ordering": ["ordem", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="certificado",
            index=models.Index(fields=["cliente", "liberado_em"], name="ava_certifi_cliente_0b62e4_idx"),
        ),
        migrations.AddIndex(
            model_name="assinaturacertificado",
            index=models.Index(fields=["cliente", "config", "ordem"], name="ava_assinat_cliente_1b5d3b_idx"),
        ),
    ]
