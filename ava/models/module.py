from django.core.exceptions import ValidationError
from django.db import models
from core.mixins import TenantModel
from .course import Curso

class CursoModulo(TenantModel):
    cliente = models.ForeignKey(
        "core.Cliente",
        on_delete=models.PROTECT,
        related_name="ava_cursomodulos",
    )

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="modulos")
    titulo = models.CharField("Título", max_length=255)
    descricao = models.TextField("Descrição", blank=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    is_active = models.BooleanField("Público/Disponível?", default=True)
    
    pre_requisito_modulo = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="modulos_dependentes", verbose_name="Módulo Pré-requisito")
    data_liberacao_programada = models.DateTimeField("Data de liberação programada", null=True, blank=True)
    eixos = models.ManyToManyField(
        "core.Eixo",
        related_name="ava_modulos",
        blank=True,
        verbose_name="Eixos",
        help_text="Se informado, restringe este modulo por eixo sem bloquear o curso inteiro.",
    )
    eixos_restricao_roles = models.JSONField(
        "Perfis afetados pela restricao de eixos",
        default=list,
        blank=True,
        help_text="Se vazio, a restricao vale para todos os perfis nao administradores.",
    )

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
        ordering = ["curso", "ordem"]
        unique_together = ["curso", "ordem"]

    def __str__(self):
        return f"{self.curso.titulo} - {self.titulo}"

    def clean(self):
        super().clean()
        if not self.pre_requisito_modulo_id:
            return
        if self.pk and self.pre_requisito_modulo_id == self.pk:
            raise ValidationError({"pre_requisito_modulo": "O modulo nao pode depender dele mesmo."})
        if self.pre_requisito_modulo.curso_id != self.curso_id:
            raise ValidationError(
                {"pre_requisito_modulo": "O modulo pre-requisito precisa pertencer ao mesmo curso."}
            )
