from django.db import models
from django.conf import settings
from core.mixins import TenantModel
from .course import Curso, TrilhaFormativa
from .module import CursoModulo
from .lesson import Aula, ConteudoAula
from .enrollment import MatriculaCurso

class ProgressoAula(TenantModel):
    matricula = models.ForeignKey(MatriculaCurso, on_delete=models.CASCADE, related_name="progressos_aulas")
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="progressos_alunos")
    is_concluida = models.BooleanField("Concluída?", default=False)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Progresso de Aula"
        verbose_name_plural = "Progressos de Aulas"
        unique_together = ["matricula", "aula"]
        indexes = [
            models.Index(fields=["cliente", "matricula", "aula"]),
        ]

    def __str__(self):
        return f"{self.matricula.aluno.username} em {self.aula.titulo} ({'OK' if self.is_concluida else 'PENDENTE'})"

class ProgressoConteudo(TenantModel):
    progresso_aula = models.ForeignKey(ProgressoAula, on_delete=models.CASCADE, related_name="conteudos_visualizados")
    conteudo = models.ForeignKey(ConteudoAula, on_delete=models.CASCADE, related_name="visualizacoes")
    is_visualizado = models.BooleanField("Visualizado/Concluído?", default=False)
    data_visualizacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Progresso de Conteúdo"
        verbose_name_plural = "Progressos de Conteúdos"
        unique_together = ["progresso_aula", "conteudo"]

    def __str__(self):
        return f"Item {self.conteudo.titulo} - {'OK' if self.is_visualizado else 'PENDENTE'}"

class ProgressoModulo(TenantModel):
    matricula = models.ForeignKey(MatriculaCurso, on_delete=models.CASCADE, related_name="progressos_modulos")
    modulo = models.ForeignKey(CursoModulo, on_delete=models.CASCADE, related_name="progressos_alunos")
    is_concluido = models.BooleanField("Concluído?", default=False)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    percentual = models.PositiveIntegerField("Progresso do Módulo (%)", default=0)

    class Meta:
        verbose_name = "Progresso de Módulo"
        verbose_name_plural = "Progressos de Módulos"
        unique_together = ["matricula", "modulo"]

    def __str__(self):
        return f"{self.matricula.aluno.username} no {self.modulo.titulo} ({self.percentual}%)"
