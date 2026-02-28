from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class PlanoPublicado(TenantModel):
    class Visibilidade(models.TextChoices):
        MUNICIPAL = "municipal", "Municipal"
        INTERNO = "interno", "Interno"

    class CuradoriaStatus(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADO = "aprovado", "Aprovado"
        REJEITADO = "rejeitado", "Rejeitado"

    plano = models.ForeignKey("courses.PlanoAula", on_delete=models.CASCADE, related_name="publicacoes_banco")
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_publicados_banco",
    )
    data_publicacao = models.DateTimeField(auto_now_add=True)
    visibilidade = models.CharField(max_length=20, choices=Visibilidade.choices, default=Visibilidade.MUNICIPAL)
    status_curadoria = models.CharField(
        max_length=20,
        choices=CuradoriaStatus.choices,
        default=CuradoriaStatus.PENDENTE,
    )

    class Meta:
        ordering = ("-data_publicacao",)
        indexes = [
            models.Index(fields=["cliente", "status_curadoria", "visibilidade"]),
            models.Index(fields=["cliente", "data_publicacao"]),
        ]


class PlanoPublicadoComentario(TenantModel):
    plano_publicado = models.ForeignKey(
        PlanoPublicado,
        on_delete=models.CASCADE,
        related_name="comentarios",
    )
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comentarios_banco")
    comentario = models.TextField()

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["cliente", "plano_publicado"]),
        ]


class PlanoPublicadoAvaliacao(TenantModel):
    plano_publicado = models.ForeignKey(
        PlanoPublicado,
        on_delete=models.CASCADE,
        related_name="avaliacoes",
    )
    avaliador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avaliacoes_banco")
    nota = models.PositiveSmallIntegerField(default=1)
    comentario = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("plano_publicado", "avaliador")
        indexes = [
            models.Index(fields=["cliente", "plano_publicado"]),
        ]

