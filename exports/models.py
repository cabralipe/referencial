"""Modelos relacionados a exportações."""

from __future__ import annotations

from django.db import models

from core.mixins import TenantModel


class ExportJob(TenantModel):
    class AlvoTipo(models.TextChoices):
        TEXTO_UNICO = "texto_unico", "Texto Único"
        QUADRO = "quadro", "Quadro"

    class Formato(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"

    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Em execução"
        DONE = "done", "Concluído"
        ERROR = "error", "Erro"

    alvo_tipo = models.CharField(max_length=20, choices=AlvoTipo.choices)
    alvo_id = models.CharField(max_length=36)
    formato = models.CharField(max_length=10, choices=Formato.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    url_resultado = models.URLField(blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
