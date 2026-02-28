from django.db import models

from core.mixins import TenantModel


class ReferencialHabilidade(TenantModel):
    codigo = models.CharField(max_length=80)
    descricao = models.TextField()
    componente_curricular = models.CharField(max_length=150, blank=True)
    etapa_modalidade = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ("codigo",)
        unique_together = ("cliente", "codigo")

