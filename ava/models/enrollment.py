from django.db import models
from django.conf import settings
from core.mixins import TenantModel
from .course import Curso, TrilhaFormativa

class MatriculaCurso(TenantModel):
    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        SUSPENSA = "suspensa", "Suspensa"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="matriculas")
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cursos_matriculados")
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.ATIVA)
    data_matricula = models.DateTimeField("Data da Matrícula", auto_now_add=True)
    data_conclusao = models.DateTimeField("Data de Conclusão", null=True, blank=True)

    # Cache de progresso total para consultas rápidas
    progresso_percentual = models.PositiveIntegerField("Progresso Total (%)", default=0)
    nota_final_obtida = models.DecimalField("Nota Final", max_digits=5, decimal_places=2, default=0.0)
    
    matriculado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="matriculas_realizadas")

    class Meta:
        verbose_name = "Matrícula no Curso"
        verbose_name_plural = "Matrículas nos Cursos"
        unique_together = ["curso", "aluno"]
        indexes = [
            models.Index(fields=["cliente", "aluno", "curso"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        aluno_nome = self.aluno.get_full_name() or getattr(self.aluno, "nome", "") or self.aluno.email
        return f"{aluno_nome} em {self.curso.titulo}"

class MatriculaTrilha(TenantModel):
    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        CONCLUIDA = "concluida", "Concluída"

    trilha = models.ForeignKey(TrilhaFormativa, on_delete=models.CASCADE, related_name="matriculas")
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trilhas_matriculadas")
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.ATIVA)
    data_matricula = models.DateTimeField("Data da Matrícula", auto_now_add=True)
    data_conclusao = models.DateTimeField("Data de Conclusão", null=True, blank=True)

    # Cache de progresso
    progresso_percentual = models.PositiveIntegerField("Progresso na Trilha (%)", default=0)

    class Meta:
        verbose_name = "Matrícula na Trilha"
        verbose_name_plural = "Matrículas nas Trilhas"
        unique_together = ["trilha", "aluno"]
        indexes = [
            models.Index(fields=["cliente", "aluno", "trilha"]),
        ]

    def __str__(self):
        aluno_nome = self.aluno.get_full_name() or getattr(self.aluno, "nome", "") or self.aluno.email
        return f"{aluno_nome} na {self.trilha.nome}"

class AutorizacaoCurso(TenantModel):
    """
    Representa privilégios elevados como 'Gestor', 'Tutor', 'Coordenador', 'Revisor' dentro de um curso específico.
    Se a aplicação tiver turmas futuramente, as permissões devem ser revisadas.
    """
    class Papel(models.TextChoices):
        GESTOR = "gestor", "Gestor/Coordenador"
        TUTOR = "tutor", "Tutor/Autor"
        AVALIADOR = "avaliador", "Avaliador"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="autorizacoes")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="autorizacoes_ava")
    papel = models.CharField("Papel de Gestão", max_length=30, choices=Papel.choices, default=Papel.TUTOR)

    class Meta:
        verbose_name = "Autorização de Curso"
        verbose_name_plural = "Autorizações de Cursos"
        unique_together = ["curso", "usuario", "papel"]

    def __str__(self):
        usuario_nome = self.usuario.get_full_name() or getattr(self.usuario, "nome", "") or self.usuario.email
        return f"{usuario_nome} como {self.get_papel_display()} em {self.curso.titulo}"
