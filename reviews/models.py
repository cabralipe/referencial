"""Modelos relacionados a fluxos de revisão."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class Revisao(TenantModel):
    class AlvoTipo(models.TextChoices):
        RESPOSTA = "resposta", "Resposta"
        TEXTO_UNICO = "texto_unico", "Texto Único"
        QUADRO = "quadro", "Quadro"

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_REVISAO = "em_revisao", "Em revisão"
        APROVADO = "aprovado", "Aprovado"
        REPROVADO = "reprovado", "Reprovado"

    alvo_tipo = models.CharField(max_length=20, choices=AlvoTipo.choices)
    alvo_id = models.CharField(max_length=36)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    parecer_html = models.TextField(blank=True)
    revisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revisoes_revisor",
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revisoes_solicitadas",
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "alvo_tipo", "alvo_id", "status"]),
        ]
        ordering = ("-updated_at",)

    @property
    def etag(self) -> str:
        return f"W/\"revisao-{self.pk}-v{int(self.updated_at.timestamp())}\""

    def __str__(self) -> str:  # pragma: no cover
        return f"Revisão {self.alvo_tipo}#{self.alvo_id} ({self.status})"
