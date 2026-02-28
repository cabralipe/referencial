from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class DocumentoVersao(TenantModel):
    class Tipo(models.TextChoices):
        PPP = "ppp", "PPP"
        REFERENCIAL = "referencial", "Referencial"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=255)
    conteudo_html = models.TextField(blank=True)
    versao = models.PositiveIntegerField(default=1)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documento_versoes",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["cliente", "tipo", "versao"]),
        ]

