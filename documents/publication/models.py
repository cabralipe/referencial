from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class DocumentoPublicacao(TenantModel):
    documento = models.ForeignKey(
        "documents.DocumentoVersao",
        on_delete=models.CASCADE,
        related_name="publicacoes",
    )
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_publicados",
    )
    publicado_em = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ("-publicado_em",)
        indexes = [
            models.Index(fields=["cliente", "publicado_em"]),
        ]

