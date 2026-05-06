"""Modelos de notificacoes in-app."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.mixins import TenantModel


class Notificacao(TenantModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    tipo = models.CharField(max_length=50)
    payload_json = models.JSONField(default=dict)
    lida = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "usuario", "lida", "created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return f"Notificacao {self.tipo} -> {self.usuario_id}"


def mural_envio_upload_to(instance: "MuralArquivoEnvio", filename: str) -> str:
    original_name = Path(filename or "arquivo").stem or "arquivo"
    extension = Path(filename or "").suffix
    safe_name = slugify(original_name) or "arquivo"
    return f"mural/envios/cliente_{instance.cliente_id}/{safe_name}-{uuid4().hex}{extension}"


class MuralArquivoEnvio(TenantModel):
    mural_id = models.CharField(max_length=64)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mural_envios_arquivo",
    )
    gt = models.ForeignKey(
        "curriculum.GT",
        on_delete=models.CASCADE,
        related_name="mural_envios_arquivo",
    )
    arquivo = models.FileField(upload_to=mural_envio_upload_to)
    nome_original = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=["cliente", "mural_id", "updated_at"]),
            models.Index(fields=["cliente", "usuario", "updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "mural_id", "usuario", "gt"],
                name="uniq_mural_envio_por_usuario_gt",
            )
        ]

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.arquivo and not self.nome_original:
            self.nome_original = Path(self.arquivo.name).name
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"Envio mural {self.mural_id} -> {self.usuario_id}"


class MuralDownloadRegistro(TenantModel):
    mural_id = models.CharField(max_length=64)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mural_downloads",
    )
    anexo_index = models.PositiveIntegerField(default=0)
    anexo_titulo = models.CharField(max_length=255, blank=True)
    anexo_url = models.URLField(max_length=1000, blank=True)

    class Meta:
        verbose_name = "Registro de download do mural"
        verbose_name_plural = "Registros de downloads do mural"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["cliente", "mural_id", "created_at"]),
            models.Index(fields=["cliente", "usuario", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Download mural {self.mural_id} -> {self.usuario_id}"
