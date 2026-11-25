"""Células de texto da construção colaborativa do plano de educação."""

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class LinhaPlanoEducacao(TenantModel):
    sala = models.ForeignKey("ava.SalaGT", on_delete=models.CASCADE, related_name="linhas_plano")
    codigo = models.CharField(max_length=30)
    tipo = models.CharField(max_length=10, choices=[
        ("objetivo", "Objetivo"), ("meta", "Meta"),
        ("estrategia", "Estratégia"), ("indicador", "Indicador"),
    ])
    ordem = models.PositiveIntegerField()
    objetivo_relacionado = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="metas_plano")
    texto = models.TextField(blank=True, default="")
    revisao = models.PositiveIntegerField(default=0)
    editado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["ordem", "id"]
        constraints = [models.UniqueConstraint(fields=["sala", "tipo", "codigo"], name="uniq_linha_plano_tipo_codigo")]

    @property
    def rotulo(self):
        return f"{self.get_tipo_display()} {self.codigo}"
