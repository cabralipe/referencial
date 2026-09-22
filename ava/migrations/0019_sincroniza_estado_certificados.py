"""Sincroniza o estado das migrações com os modelos de certificado.

Divergência preexistente: os modelos de certificado já refletiam estas
definições, mas nenhuma migração havia sido gerada. Isolar aqui evita
misturar a correção com as novidades do Diário de Bordo.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ava', '0018_corrigir_acentuacao_certificados'),
        ('core', '0020_usuario_ava_multimunicipio'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='assinaturacertificado',
            new_name='ava_assinat_cliente_e67762_idx',
            old_name='ava_assinat_cliente_1b5d3b_idx',
        ),
        migrations.RenameIndex(
            model_name='certificado',
            new_name='ava_certifi_cliente_218533_idx',
            old_name='ava_certifi_cliente_0b62e4_idx',
        ),
        migrations.AlterField(
            model_name='assinaturacertificado',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='%(class)ss', to='core.cliente'),
        ),
        migrations.AlterField(
            model_name='certificado',
            name='arquivo_pdf',
            field=models.FileField(blank=True, null=True, upload_to='ava/certificados/pdfs/', verbose_name='Arquivo PDF gerado'),
        ),
        migrations.AlterField(
            model_name='certificado',
            name='dados_impressos',
            field=models.JSONField(blank=True, default=dict, verbose_name='Dados impressos (snapshot)'),
        ),
        migrations.AlterField(
            model_name='certificado',
            name='nota_final',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Nota final no certificado'),
        ),
        migrations.AlterField(
            model_name='configcertificado',
            name='assinatura_digital_url',
            field=models.URLField(blank=True, verbose_name='URL da assinatura legada'),
        ),
    ]
