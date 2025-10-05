"""Modelos de oficinas e quadros."""

from __future__ import annotations

from django.db import models

from core.mixins import TenantModel
from curriculum.models import GT


class Quadro(TenantModel):
    gt = models.ForeignKey(GT, on_delete=models.CASCADE, related_name="quadros")
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
