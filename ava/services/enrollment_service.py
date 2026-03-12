from django.db import transaction
from ava.models import Curso, MatriculaCurso, TrilhaFormativa, MatriculaTrilha

class InscricaoService:
    """
    Serviço responsável por matricular alunos em cursos e trilhas.
    """

    @staticmethod
    @transaction.atomic
    def matricular_aluno_curso(aluno, curso: Curso, autor_matricula=None):
        matricula, created = MatriculaCurso.objects.get_or_create(
            curso=curso,
            aluno=aluno,
            defaults={"matriculado_por": autor_matricula}
        )

        if not created and matricula.status in [MatriculaCurso.Status.SUSPENSA, MatriculaCurso.Status.CANCELADA]:
            matricula.status = MatriculaCurso.Status.ATIVA
            matricula.save(update_fields=["status"])

        return matricula, created

    @staticmethod
    @transaction.atomic
    def matricular_aluno_trilha(aluno, trilha: TrilhaFormativa, matricular_cursos=True):
        matricula, created = MatriculaTrilha.objects.get_or_create(
            trilha=trilha,
            aluno=aluno
        )

        if not created and matricula.status != MatriculaTrilha.Status.ATIVA:
            matricula.status = MatriculaTrilha.Status.ATIVA
            matricula.save(update_fields=["status"])

        if matricular_cursos:
            for curso in trilha.cursos.filter(is_aberto=True): # Ou ignorar is_aberto na trilha
                InscricaoService.matricular_aluno_curso(aluno, curso)

        return matricula, created
