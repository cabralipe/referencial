"""Modelos de comentários em linha."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class Comentario(TenantModel):
    class AlvoTipo(models.TextChoices):
        RESPOSTA = "resposta", "Resposta"
        TEXTO_UNICO = "texto_unico", "Texto Único"
        QUADRO = "quadro", "Quadro"
        PPP = "ppp", "PPP"

    alvo_tipo = models.CharField(max_length=20, choices=AlvoTipo.choices)
    alvo_id = models.CharField(max_length=36)
    anchor_json = models.JSONField(default=dict)
    conteudo_html = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comentarios",
    )
    resolvido = models.BooleanField(default=False)
    resolvido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comentarios_resolvidos",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resposta_html = models.TextField(blank=True, default="")
    respondido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comentarios_respondidos",
    )
    respondido_em = models.DateTimeField(null=True, blank=True)
    mentions = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="comentarios_mencionado", blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "alvo_tipo", "alvo_id", "resolvido"]),
        ]
        ordering = ("created_at",)

    @property
    def etag(self) -> str:
        return f"W/\"comentario-{self.pk}-v{int(self.updated_at.timestamp())}\""

    def __str__(self) -> str:  # pragma: no cover
        return f"Comentário {self.alvo_tipo}#{self.alvo_id}"
