from django.db import transaction
from ava.models import Curso, MatriculaCurso, TrilhaFormativa, MatriculaTrilha
from ava.services.access_control import course_eixo_block_message, user_can_access_course_by_eixo


class InscricaoService:
    """
    Serviço responsável por matricular alunos em cursos e trilhas.
    """

    @staticmethod
    @transaction.atomic
    def matricular_aluno_curso(aluno, curso: Curso, autor_matricula=None):
        if not user_can_access_course_by_eixo(aluno, curso):
            raise ValueError(course_eixo_block_message(curso))

        matricula, created = MatriculaCurso.objects.get_or_create(
            curso=curso,
            aluno=aluno,
            defaults={
                "cliente_id": curso.cliente_id,
                "matriculado_por": autor_matricula,
            },
        )

        if not created and matricula.status in [
            MatriculaCurso.Status.SUSPENSA,
            MatriculaCurso.Status.CANCELADA,
            MatriculaCurso.Status.CONCLUIDA,
        ]:
            matricula.status = MatriculaCurso.Status.ATIVA
            matricula.data_conclusao = None
            if not matricula.cliente_id:
                matricula.cliente_id = curso.cliente_id
            if autor_matricula and not matricula.matriculado_por_id:
                matricula.matriculado_por = autor_matricula
            matricula.save(update_fields=["status", "data_conclusao", "cliente", "matriculado_por"])

        return matricula, created

    @staticmethod
    @transaction.atomic
    def matricular_aluno_trilha(aluno, trilha: TrilhaFormativa, matricular_cursos=True):
        matricula, created = MatriculaTrilha.objects.get_or_create(
            trilha=trilha,
            aluno=aluno,
            defaults={"cliente_id": trilha.cliente_id},
        )

        if not created and matricula.status != MatriculaTrilha.Status.ATIVA:
            matricula.status = MatriculaTrilha.Status.ATIVA
            matricula.data_conclusao = None
            if not matricula.cliente_id:
                matricula.cliente_id = trilha.cliente_id
            matricula.save(update_fields=["status", "data_conclusao", "cliente"])

        if matricular_cursos:
            for curso in trilha.cursos.filter(is_aberto=True):
                if not user_can_access_course_by_eixo(aluno, curso):
                    continue
                InscricaoService.matricular_aluno_curso(aluno, curso)

        return matricula, created
