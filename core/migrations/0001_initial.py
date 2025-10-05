# Generated manually to define tabelas iniciais do app core
from __future__ import annotations

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import core.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=255)),
                (
                    "slug",
                    models.SlugField(
                        unique=True,
                        validators=[django.core.validators.RegexValidator(r"^[a-z0-9-]+$")],
                    ),
                ),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={"ordering": ("nome",)},
        ),
        migrations.CreateModel(
            name="ClienteConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("chave", models.CharField(max_length=100)),
                ("valor_texto", models.TextField()),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="clienteconfigs",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuração de Cliente",
                "verbose_name_plural": "Configurações de Clientes",
            },
        ),
        migrations.CreateModel(
            name="ClienteFeatureFlag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("flag", models.CharField(max_length=100)),
                ("ativo", models.BooleanField(default=False)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="clientefeatureflags",
                        to="core.cliente",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ClienteTema",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("logo_url", models.URLField(blank=True)),
                ("cor_primaria", models.CharField(default="#004aad", max_length=7)),
                ("cor_secundaria", models.CharField(default="#00b4d8", max_length=7)),
                ("rodape_html", models.TextField(blank=True)),
                ("cabecalho_html", models.TextField(blank=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="clientetemas",
                        to="core.cliente",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("usuario_id", models.IntegerField(blank=True, null=True)),
                ("entidade", models.CharField(max_length=150)),
                ("entidade_id", models.CharField(max_length=255)),
                ("acao", models.CharField(max_length=100)),
                ("diff_json", models.JSONField(default=dict)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="auditlogs",
                        to="core.cliente",
                    ),
                ),
            ],
            options={"ordering": ("-timestamp",)},
        ),
        migrations.CreateModel(
            name="Usuario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, unique=True, verbose_name="E-mail"),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("is_staff", models.BooleanField(default=False, verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("nome", models.CharField(max_length=255)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("super_admin", "Super Admin"),
                            ("admin_cliente", "Admin do Cliente"),
                            ("articulador", "Articulador"),
                            ("membro_gt", "Membro GT"),
                            ("leitor", "Leitor"),
                        ],
                        default="leitor",
                        max_length=20,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="usuarios",
                        to="core.cliente",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "Usuário",
                "verbose_name_plural": "Usuários",
                "ordering": ("email",),
            },
            managers=[
                ("objects", core.models.UsuarioManager()),
            ],
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["cliente", "entidade", "entidade_id"], name="core_audit_cliente_37c01d_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["timestamp"], name="core_audit_timestamp_3a7540_idx"),
        ),
        migrations.AlterUniqueTogether(name="clienteconfig", unique_together={("cliente", "chave")}),
        migrations.AlterUniqueTogether(name="clientefeatureflag", unique_together={("cliente", "flag")}),
        migrations.AlterUniqueTogether(name="clientetema", unique_together={("cliente", "cor_primaria", "cor_secundaria")}),
    ]
