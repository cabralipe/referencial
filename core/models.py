"""Modelos centrais de multi-cliente e autenticação."""

from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from .mixins import TenantModel, TimeStampedModel


class Cliente(TimeStampedModel):
    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, validators=[RegexValidator(r"^[a-z0-9-]+$")])
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self) -> str:  # pragma: no cover - legibilidade no admin
        return self.nome


class ClienteConfig(TenantModel):
    chave = models.CharField(max_length=100)
    valor_texto = models.TextField()

    class Meta:
        unique_together = ("cliente", "chave")
        verbose_name = "Configuração de Cliente"
        verbose_name_plural = "Configurações de Clientes"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.cliente}::{self.chave}"


class ClienteFeatureFlag(TenantModel):
    flag = models.CharField(max_length=100)
    ativo = models.BooleanField(default=False)

    class Meta:
        unique_together = ("cliente", "flag")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.cliente}::{self.flag}={self.ativo}"


class ClienteTema(TenantModel):
    logo_url = models.URLField(blank=True)
    cor_primaria = models.CharField(max_length=7, default="#004aad")
    cor_secundaria = models.CharField(max_length=7, default="#00b4d8")
    meb_avatar_url = models.URLField(blank=True)
    rodape_html = models.TextField(blank=True)
    cabecalho_html = models.TextField(blank=True)

    class Meta:
        unique_together = ("cliente", "cor_primaria", "cor_secundaria")


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    REQUIRED_ESCOLA_ROLES = {
        "diretor",
        "coordenador_pedagogico",
        "professor",
    }

    def _create_user(self, email: str, password: Optional[str], **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório")
        email = self.normalize_email(email)
        tipo_cadastro = extra_fields.get("tipo_cadastro")
        tipo_cadastro_id = extra_fields.get("tipo_cadastro_id")
        if tipo_cadastro is None and tipo_cadastro_id:
            tipo_model = self.model._meta.get_field("tipo_cadastro").remote_field.model
            tipo_cadastro = tipo_model.raw_objects.filter(pk=tipo_cadastro_id, ativo=True, is_deleted=False).first()
        if tipo_cadastro is not None:
            extra_fields.setdefault("cliente_id", getattr(tipo_cadastro, "cliente_id", None))
            extra_fields.setdefault("seguimento", getattr(tipo_cadastro, "seguimento", "") or "")
            extra_fields["role"] = getattr(tipo_cadastro, "role_interno", extra_fields.get("role"))
        user = self.model(email=email, **extra_fields)
        role = extra_fields.get("role") or Usuario.Role.LEITOR
        if role != Usuario.Role.SUPER_ADMIN and not user.cliente_id:
            raise ValueError("Usuários não super_admin devem possuir cliente")
        if role == Usuario.Role.SUPER_ADMIN and user.cliente_id:
            raise ValueError("Super admin não pode possuir cliente")
        if role in self.REQUIRED_ESCOLA_ROLES and not user.escola_id:
            raise ValueError("Diretor, Coordenador Pedagógico e Professor devem possuir escola")
        if role == Usuario.Role.SUPER_ADMIN and user.escola_id:
            raise ValueError("Super admin não pode possuir escola")
        escola_cliente_id = None
        if user.escola_id:
            escola = extra_fields.get("escola")
            if escola is not None:
                escola_cliente_id = getattr(escola, "cliente_id", None)
            else:
                from curriculum.models import Escola

                escola_cliente_id = (
                    Escola.raw_objects.filter(pk=user.escola_id).values_list("cliente_id", flat=True).first()
                )
        if user.escola_id and user.cliente_id and escola_cliente_id and escola_cliente_id != user.cliente_id:
            raise ValueError("Escola deve pertencer ao mesmo cliente do usuário")
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: Optional[str] = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", Usuario.Role.LEITOR)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: Optional[str], **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Usuario.Role.SUPER_ADMIN)
        extra_fields.setdefault("cliente", None)
        extra_fields.setdefault("escola", None)
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN_CLIENTE = "admin_cliente", "Admin do Cliente"
        DIRETOR = "diretor", "Diretor"
        COORDENADOR_PEDAGOGICO = "coordenador_pedagogico", "Coordenador Pedagógico"
        PROFESSOR = "professor", "Professor"
        ARTICULADOR = "articulador", "Redator"
        REVISOR = "revisor", "Revisor"
        MEMBRO_GT = "membro_gt", "Membro GT"
        LEITOR = "leitor", "Leitor"

    class Seguimento(models.TextChoices):
        PROFISSIONAL_APOIO = "profissional_apoio", "Profissional de Apoio"
        PROFESSOR_ANOS_INICIAIS = "professor_anos_iniciais", "Professor - Anos Iniciais"
        PROFESSOR_ANOS_FINAIS = "professor_anos_finais", "Professor - Anos Finais"
        PROFESSOR_EJA = "professor_eja", "Professor - EJA"

    ESCOLA_REQUIRED_ROLES = {
        Role.DIRETOR,
        Role.COORDENADOR_PEDAGOGICO,
        Role.PROFESSOR,
    }

    username = None
    email = models.EmailField("E-mail", unique=True)
    nome = models.CharField(max_length=255)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    escola = models.ForeignKey(
        "curriculum.Escola",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    tipo_cadastro = models.ForeignKey(
        "core.TipoUsuarioCadastro",
        on_delete=models.SET_NULL,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.LEITOR)
    seguimento = models.CharField(max_length=40, choices=Seguimento.choices, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["nome"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ("email",)

    def __str__(self) -> str:  # pragma: no cover
        return self.email

    def _sync_from_tipo_cadastro(self) -> None:
        if not self.tipo_cadastro_id:
            return
        tipo_cadastro = self.tipo_cadastro
        self.role = tipo_cadastro.role_interno
        self.seguimento = tipo_cadastro.seguimento or ""
        if not self.cliente_id:
            self.cliente_id = tipo_cadastro.cliente_id

    def clean(self):  # type: ignore[override]
        self._sync_from_tipo_cadastro()
        super().clean()
        if self.tipo_cadastro_id and self.tipo_cadastro.cliente_id != self.cliente_id:
            raise ValidationError({"tipo_cadastro": "O tipo de usuário deve pertencer ao mesmo cliente do usuário."})
        if self.role != self.Role.SUPER_ADMIN and not self.cliente_id:
            raise ValidationError({"cliente": "Usuários não super_admin devem possuir cliente."})
        if self.role in self.ESCOLA_REQUIRED_ROLES and not self.escola_id:
            raise ValidationError({"escola": "Diretor, Coordenador Pedagógico e Professor devem possuir escola."})
        if self.role == self.Role.SUPER_ADMIN:
            if self.cliente_id:
                raise ValidationError({"cliente": "Super admin não pode possuir cliente."})
            if self.escola_id:
                raise ValidationError({"escola": "Super admin não pode possuir escola."})
        escola_cliente_id = None
        if self.escola_id:
            from curriculum.models import Escola

            escola_cliente_id = Escola.raw_objects.filter(pk=self.escola_id).values_list("cliente_id", flat=True).first()
        if self.escola_id and self.cliente_id and escola_cliente_id and escola_cliente_id != self.cliente_id:
            raise ValidationError({"escola": "Escola deve pertencer ao mesmo cliente do usuário."})

    def save(self, *args, **kwargs):  # type: ignore[override]
        self._sync_from_tipo_cadastro()
        update_fields = kwargs.get("update_fields")
        if update_fields and self.tipo_cadastro_id:
            update_fields = set(update_fields)
            update_fields.update({"role", "seguimento", "cliente"})
            kwargs["update_fields"] = list(update_fields)
        super().save(*args, **kwargs)

    @property
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN


class TipoUsuarioCadastro(TenantModel):
    class AcessoPPP(models.TextChoices):
        EDITAR = "editar", "Pode editar"
        VISUALIZAR = "visualizar", "Apenas visualizar"

    ROLE_CHOICES = (
        (Usuario.Role.DIRETOR, "Diretor"),
        (Usuario.Role.COORDENADOR_PEDAGOGICO, "Coordenador Pedagógico"),
        (Usuario.Role.PROFESSOR, "Professor"),
    )

    nome = models.CharField(max_length=120)
    slug = models.SlugField()
    role_interno = models.CharField(max_length=30, choices=ROLE_CHOICES)
    seguimento = models.CharField(
        max_length=40,
        choices=Usuario.Seguimento.choices,
        blank=True,
        default="",
        help_text="Opcional. Use apenas para mapear tipos de professor aos seguimentos legados do AVA.",
    )
    acesso_ppp = models.CharField(max_length=20, choices=AcessoPPP.choices, default=AcessoPPP.VISUALIZAR)
    exibir_no_cadastro = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    ordem_exibicao = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("ordem_exibicao", "nome")
        unique_together = ("cliente", "slug")
        verbose_name = "Tipo de Usuário de Cadastro"
        verbose_name_plural = "Tipos de Usuário de Cadastro"

    def __str__(self) -> str:  # pragma: no cover
        return self.nome

    def clean(self):  # type: ignore[override]
        super().clean()
        if self.seguimento and self.role_interno != Usuario.Role.PROFESSOR:
            raise ValidationError({"seguimento": "Apenas tipos com papel interno de professor podem usar seguimento."})


class AuditLog(TenantModel):
    usuario_id = models.IntegerField(null=True, blank=True)
    entidade = models.CharField(max_length=150)
    entidade_id = models.CharField(max_length=255)
    acao = models.CharField(max_length=100)
    diff_json = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "entidade", "entidade_id"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ("-timestamp",)


class ThrottleBlock(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="throttle_blocks",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="throttle_blocks",
    )
    scope = models.CharField(max_length=100)
    ident = models.CharField(max_length=255, blank=True)
    cache_key = models.CharField(max_length=255, unique=True)
    wait_seconds = models.IntegerField(default=0)
    blocked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "blocked_until"]),
            models.Index(fields=["blocked_until"]),
        ]
        ordering = ("-blocked_until", "-created_at")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.scope}:{self.ident or 'anon'}"


class ScoreEntry(TenantModel):
    """Registra pontos de gamificação por usuário."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="score_entries",
    )
    origem_tipo = models.CharField(max_length=50)
    origem_id = models.CharField(max_length=64, blank=True)
    tarefa_id = models.IntegerField(null=True, blank=True)
    pontos = models.IntegerField(default=0)
    descricao = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "usuario", "created_at"]),
            models.Index(fields=["cliente", "origem_tipo", "origem_id"]),
        ]
        verbose_name = "Score"
        verbose_name_plural = "Scores"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.usuario_id} +{self.pontos} ({self.origem_tipo})"


class UserSessionLog(TimeStampedModel):
    usuario = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_logs",
    )
    cliente = models.ForeignKey(
        "core.Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_logs",
    )
    session_key = models.CharField(max_length=64, unique=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    user_agent = models.TextField(blank=True)
    device = models.CharField(max_length=100, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "last_seen_at"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        usuario = getattr(self.usuario, "email", "desconhecido")
        return f"Sessão {self.session_key} ({usuario})"
