"""Modelos da biblioteca reutilizável de mídia e blocos."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class Midia(TenantModel):
    url = models.URLField()
    legenda = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="midias_enviadas",
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return self.url


class BlocoTexto(TenantModel):
    titulo = models.CharField(max_length=255)
    conteudo_html = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocos_criados",
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "titulo"]),
        ]
        ordering = ("titulo",)

    def __str__(self) -> str:  # pragma: no cover
        return self.titulo

    @property
    def etag(self) -> str:
        return f"W/\"blocotexto-{self.pk}-v{int(self.updated_at.timestamp())}\""
