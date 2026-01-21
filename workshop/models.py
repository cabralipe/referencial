"""Modelos de oficinas e quadros."""

from __future__ import annotations

from django.db import models

from core.mixins import TenantModel
from curriculum.models import Area, GT


class Quadro(TenantModel):
    gt = models.ForeignKey(GT, on_delete=models.CASCADE, related_name="quadros")
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="quadros")
    template = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cliente", "gt", "template")

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.pk:
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields:
                update_fields = set(update_fields)
                update_fields.update({"version", "updated_at"})
                kwargs["update_fields"] = list(update_fields)
        else:
            self.version = 1
        super().save(*args, **kwargs)


class CelulaQuadro(TenantModel):
    quadro = models.ForeignKey(Quadro, on_delete=models.CASCADE, related_name="celulas")
    linha = models.PositiveIntegerField()
    coluna = models.PositiveIntegerField()
    valor_html = models.TextField(blank=True)

    class Meta:
        unique_together = ("quadro", "linha", "coluna")
        ordering = ("linha", "coluna")


class QuadroLinha(TenantModel):
    quadro = models.ForeignKey(Quadro, on_delete=models.CASCADE, related_name="linhas")
    linha = models.PositiveIntegerField()
    nome = models.CharField(max_length=255)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("quadro", "linha")
        ordering = ("ordem", "linha")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.quadro_id} - L{self.linha}: {self.nome}"


class QuadroColuna(TenantModel):
    quadro = models.ForeignKey(Quadro, on_delete=models.CASCADE, related_name="colunas")
    coluna = models.PositiveIntegerField()
    nome = models.CharField(max_length=255)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("quadro", "coluna")
        ordering = ("ordem", "coluna")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.quadro_id} - C{self.coluna}: {self.nome}"
