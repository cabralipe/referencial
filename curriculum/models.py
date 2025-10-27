"""Modelos do domínio de currículo."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class GT(TenantModel):
    nome = models.CharField(max_length=255)
    etapa = models.CharField(max_length=120)
    membros = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="grupos_trabalho",
        blank=True,
    )

    class Meta:
        verbose_name = "Grupo de Trabalho"
        verbose_name_plural = "Grupos de Trabalho"
        ordering = ("nome",)

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class Tarefa(TenantModel):
    class Tipo(models.TextChoices):
        PERGUNTAS = "PERGUNTAS", "Perguntas"
        OFICINA = "OFICINA", "Oficina"

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_REVISAO = "em_revisao", "Em revisão"
        CONCLUIDA = "concluida", "Concluída"

    ordem = models.PositiveIntegerField()
    etapa = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)

    class Meta:
        ordering = ("ordem",)
        unique_together = ("cliente", "ordem", "tipo")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tipo}-{self.ordem}"


class Pergunta(TenantModel):
    tarefa = models.ForeignKey(
        Tarefa,
        on_delete=models.CASCADE,
        related_name="perguntas",
    )
    ordem = models.PositiveIntegerField()
    texto = models.TextField()
    permite_upload = models.BooleanField(default=False)
    obrigatoria = models.BooleanField(default=True)

    class Meta:
        ordering = ("ordem",)
        unique_together = ("tarefa", "ordem")


class Resposta(TenantModel):
    gt = models.ForeignKey(GT, on_delete=models.CASCADE, related_name="respostas")
    pergunta = models.ForeignKey(
        Pergunta,
        on_delete=models.CASCADE,
        related_name="respostas",
    )
    conteudo_html = models.TextField(blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respostas",
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cliente", "gt", "pergunta")
        indexes = [
            models.Index(fields=["cliente", "gt", "pergunta"]),
        ]

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

    @property
    def etag(self) -> str:
        return f"W/\"resposta-{self.pk}-v{self.version}\""


class Anexo(TenantModel):
    resposta = models.ForeignKey(
        Resposta,
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    url = models.URLField()
    legenda = models.CharField(max_length=255, blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("ordem",)


class TextoUnico(TenantModel):
    gt = models.ForeignKey(GT, on_delete=models.CASCADE, related_name="textos_unicos")
    tarefa = models.ForeignKey(
        Tarefa,
        on_delete=models.CASCADE,
        related_name="textos_unicos",
    )
    conteudo_html = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="textos_unicos",
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cliente", "gt", "tarefa")
        indexes = [
            models.Index(fields=["cliente", "gt", "tarefa"]),
        ]

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

    @property
    def etag(self) -> str:
        return f"W/\"texto-unico-{self.pk}-v{self.version}\""


class TextoColaborativo(TenantModel):
    gt = models.ForeignKey(GT, on_delete=models.CASCADE, related_name="textos_colaborativos")
    titulo = models.CharField(max_length=255)
    conteudo_html = models.TextField(blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="textos_colaborativos",
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=["cliente", "gt"]),
        ]

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

    def __str__(self) -> str:  # pragma: no cover
        return self.titulo

    @property
    def etag(self) -> str:
        return f"W/\"texto-colaborativo-{self.pk}-v{self.version}\""
