"""Modelos para formulários dinâmicos."""

from __future__ import annotations

from django.db import models

from core.mixins import TenantModel


class FormularioDinamico(TenantModel):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("cliente", "nome")
        ordering = ("nome",)

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class CampoDinamico(TenantModel):
    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto"
        SELECT = "select", "Seleção"
        UPLOAD = "upload", "Upload"
        INTEIRO = "inteiro", "Inteiro"
        DECIMAL = "decimal", "Decimal"
        BOOL = "bool", "Booleano"

    formulario = models.ForeignKey(
        FormularioDinamico,
        on_delete=models.CASCADE,
        related_name="campos",
    )
    chave = models.SlugField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    config_json = models.JSONField(default=dict, blank=True)
    obrigatorio = models.BooleanField(default=False)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("formulario", "chave")
        ordering = ("ordem",)


class RespostaCampoDinamico(TenantModel):
    class OwnerType(models.TextChoices):
        RESPOSTA = "resposta", "Resposta"
        TEXTO_UNICO = "texto_unico", "Texto Único"
        QUADRO = "quadro", "Quadro"
        GT = "gt", "GT"
        CURSO_PLANO = "curso_plano", "Curso Plano"

    formulario = models.ForeignKey(
        FormularioDinamico,
        on_delete=models.CASCADE,
        related_name="respostas_campo",
    )
    campo = models.ForeignKey(
        CampoDinamico,
        on_delete=models.CASCADE,
        related_name="respostas",
    )
    valor_texto = models.TextField(blank=True)
    valor_num = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_bool = models.BooleanField(null=True, blank=True)
    url_arquivo = models.URLField(blank=True)
    owner_type = models.CharField(max_length=20, choices=OwnerType.choices)
    owner_id = models.CharField(max_length=36)

    class Meta:
        unique_together = ("campo", "owner_type", "owner_id")
