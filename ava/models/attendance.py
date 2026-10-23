import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class EncontroCurso(TenantModel):
    curso = models.ForeignKey(
        "ava.Curso", on_delete=models.CASCADE, related_name="encontros"
    )
    titulo = models.CharField("Título da aula/reunião", max_length=255)
    data_aula = models.DateField("Data da aula")
    realizado = models.BooleanField(
        "Encontro realizado (conta na frequência)", default=False
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    link_aberto = models.BooleanField("Link de presença aberto", default=False)
    link_expira_em = models.DateTimeField("Link válido até", null=True, blank=True)

    class Meta:
        ordering: ClassVar = ["-data_aula", "-id"]
        verbose_name = "Encontro do curso"

    def __str__(self):
        return f"{self.data_aula} · {self.titulo}"


class PresencaCurso(TenantModel):
    encontro = models.ForeignKey(
        EncontroCurso, on_delete=models.CASCADE, related_name="presencas"
    )
    matricula = models.ForeignKey(
        "ava.MatriculaCurso",
        on_delete=models.CASCADE,
        related_name="presencas_encontros",
    )
    presente = models.BooleanField(default=False)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    origem = models.CharField(
        max_length=10, choices=[("checklist", "Checklist"), ("link", "Link")]
    )

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["encontro", "matricula"], name="ava_presenca_encontro_matricula"
            )
        ]
