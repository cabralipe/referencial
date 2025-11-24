"""Modelos centrais de multi-cliente e autenticação."""

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import AbstractUser, BaseUserManager
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

    def _create_user(self, email: str, password: Optional[str], **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if extra_fields.get("role") != Usuario.Role.SUPER_ADMIN and not user.cliente_id:
            raise ValueError("Usuários não super_admin devem possuir cliente")
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
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN_CLIENTE = "admin_cliente", "Admin do Cliente"
        ARTICULADOR = "articulador", "Articulador"
        MEMBRO_GT = "membro_gt", "Membro GT"
        LEITOR = "leitor", "Leitor"

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
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LEITOR)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["nome"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ("email",)

    def __str__(self) -> str:  # pragma: no cover
        return self.email

    @property
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN


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

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "last_seen_at"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        usuario = getattr(self.usuario, "email", "desconhecido")
        return f"Sessão {self.session_key} ({usuario})"
