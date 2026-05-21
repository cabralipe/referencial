from django.db import models

from core.mixins import TenantModel


class PlanoMetaPPP(TenantModel):
    codigo = models.CharField(max_length=80)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    eixo = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ("codigo",)
        unique_together = ("cliente", "codigo")

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.codigo}] {self.titulo}"

