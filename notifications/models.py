"""Modelos de notificações in-app."""

from __future__ import annotations

from django.conf import settings
from django.db import models

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
        return f"Notificação {self.tipo} -> {self.usuario_id}"
