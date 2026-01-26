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


class ReviewerAssignment(TenantModel):
    class ScopeType(models.TextChoices):
        TRAIL = "trail", "Trilha"
        ETAPA = "etapa", "Etapa"
        COMPONENTE = "componente", "Componente"
        PPP = "ppp", "PPP"

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviewer_assignments",
    )
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices)
    scope_id = models.CharField(max_length=64)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "reviewer", "scope_type", "scope_id"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.reviewer_id} -> {self.scope_type}:{self.scope_id}"


class ReviewDecision(TenantModel):
    class ActorRole(models.TextChoices):
        REVIEWER = "reviewer", "Revisor"
        REDACTOR = "redactor", "Redator"

    class DecisionType(models.TextChoices):
        RECOMMEND_APPROVE = "recommend_approve", "Recomendar validação"
        RECOMMEND_RETURN = "recommend_return", "Recomendar devolução"
        RECOMMEND_MINOR = "recommend_minor", "Recomendar ajustes menores"
        IN_PROGRESS = "in_progress", "Em andamento"

    target_type = models.CharField(max_length=20, choices=Revisao.AlvoTipo.choices)
    target_id = models.CharField(max_length=36)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_decisions",
    )
    actor_role = models.CharField(max_length=20, choices=ActorRole.choices)
    decision_type = models.CharField(max_length=30, choices=DecisionType.choices)
    checklist = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "target_type", "target_id"]),
            models.Index(fields=["cliente", "actor_role", "created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.actor_role}:{self.decision_type} {self.target_type}#{self.target_id}"
