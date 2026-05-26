# Generated migration for FormularioInscricao and InscricaoPublica models

from __future__ import annotations

import consultas.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consultas', '0004_manifestacaopublica_cpf_optional'),
        ('core', '0004_usersessionlog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FormularioInscricao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('titulo', models.CharField(default='Audiência Pública do Referencial Curricular', max_length=255)),
                ('subtitulo', models.CharField(blank=True, default='Ficha de Inscrição', max_length=255)),
                ('descricao', models.TextField(blank=True)),
                ('token_acesso', models.CharField(default=consultas.models._token, max_length=32, unique=True)),
                ('ativo', models.BooleanField(default=True)),
                ('opcoes_area_atuacao', models.JSONField(blank=True, default=list)),
                ('opcoes_representacao', models.JSONField(blank=True, default=list)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='%(class)ss', to='core.cliente')),
                ('criado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='formularios_inscricao_criados',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='InscricaoPublica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('nome_completo', models.CharField(max_length=255)),
                ('instituicao_comunidade', models.CharField(blank=True, max_length=255)),
                ('telefone', models.CharField(blank=True, max_length=30)),
                ('email', models.EmailField(blank=True)),
                ('areas_atuacao', models.JSONField(blank=True, default=list)),
                ('area_atuacao_outro', models.CharField(blank=True, max_length=255)),
                ('representacoes', models.JSONField(blank=True, default=list)),
                ('representacao_outro', models.CharField(blank=True, max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='%(class)ss', to='core.cliente')),
                ('formulario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='inscricoes',
                    to='consultas.formularioinscricao',
                )),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='inscricaopublica',
            index=models.Index(fields=['cliente', 'formulario'], name='consultas_i_cliente_form_idx'),
        ),
        migrations.AddIndex(
            model_name='inscricaopublica',
            index=models.Index(fields=['created_at'], name='consultas_i_created_at_idx'),
        ),
    ]
