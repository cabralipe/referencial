from django.db.models import Q
from django.utils import timezone

from ava.models import (
    Atividade,
    Aula,
    ConteudoAula,
    MatriculaCurso,
    ProgressoAula,
    ProgressoConteudo,
    ProgressoModulo,
)


class ProgressoService:
    """
    Servico central de calculo e registro de progressos no AVA.
    """

    @staticmethod
    def marcar_conteudo_visualizado(aluno, conteudo_id: int):
        try:
            conteudo = ConteudoAula.objects.select_related("aula__modulo__curso").get(id=conteudo_id)
            matricula = MatriculaCurso.objects.get(curso=conteudo.aula.modulo.curso, aluno=aluno)
        except (ConteudoAula.DoesNotExist, MatriculaCurso.DoesNotExist):
            return False

        # Cria a arvore de progresso se nao existir.
        ProgressoService._garantir_progressos(matricula, conteudo.aula)

        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=conteudo.aula)
        prog_conteudo, _ = ProgressoConteudo.objects.get_or_create(
            progresso_aula=prog_aula,
            conteudo=conteudo,
        )

        if not prog_conteudo.is_visualizado:
            prog_conteudo.is_visualizado = True
            prog_conteudo.data_visualizacao = timezone.now()
            prog_conteudo.save(update_fields=["is_visualizado", "data_visualizacao"])

            # Recalcula aula, modulo e curso.
            ProgressoService.recalcular_aula(matricula, conteudo.aula)
            return True
        return False

    @staticmethod
    def _garantir_progressos(matricula, aula):
        ProgressoModulo.objects.get_or_create(
            matricula=matricula,
            modulo=aula.modulo,
            defaults={"cliente_id": matricula.cliente_id},
        )
        ProgressoAula.objects.get_or_create(
            matricula=matricula,
            aula=aula,
            defaults={"cliente_id": matricula.cliente_id},
        )

    @staticmethod
    def sincronizar_matricula(matricula: MatriculaCurso):
        """
        Recalcula a matrícula contra a estrutura atual do curso.

        Isso cobre cenários em que módulos, aulas ou conteúdos obrigatórios
        foram adicionados após o aluno já ter concluído o curso.
        """
        modulos = list(
            matricula.curso.modulos.filter(is_active=True)
            .prefetch_related("aulas")
            .order_by("ordem", "id")
        )

        for modulo in modulos:
            ProgressoModulo.objects.get_or_create(
                matricula=matricula,
                modulo=modulo,
                defaults={"cliente_id": matricula.cliente_id},
            )
            aulas = list(modulo.aulas.filter(is_active=True).order_by("ordem", "id"))
            for aula in aulas:
                ProgressoService._garantir_progressos(matricula, aula)
                ProgressoService.recalcular_aula(matricula, aula)
            ProgressoService.recalcular_modulo(matricula, modulo)

        ProgressoService.recalcular_curso(matricula)
        matricula.refresh_from_db(fields=["status", "progresso_percentual", "data_conclusao"])
        return matricula

    @staticmethod
    def recalcular_aula(matricula: MatriculaCurso, aula: Aula):
        """
        Verifica se a aula foi concluida baseado nos conteudos obrigatorios
        e atividades obrigatorias validas.
        """
        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=aula)

        qt_conteudos = ConteudoAula.objects.filter(aula=aula, is_obrigatorio=True).count()
        qt_visualizados = ProgressoConteudo.objects.filter(
            progresso_aula=prog_aula,
            conteudo__is_obrigatorio=True,
            is_visualizado=True,
        ).count()

        # Para ENVIO_ARQUIVO, so conta se houver arquivo anexado.
        atividades_obrigatorias = Atividade.objects.filter(aula=aula, is_obrigatoria=True)
        qt_atividades = atividades_obrigatorias.count()
        qt_tentativas = (
            atividades_obrigatorias.filter(
                tentativas__aluno=matricula.aluno,
                tentativas__status__in=["enviada", "corrigida"],
            )
            .filter(
                ~Q(tipo=Atividade.Tipo.ENVIO_ARQUIVO)
                | (
                    Q(tipo=Atividade.Tipo.ENVIO_ARQUIVO)
                    & Q(tentativas__arquivo_enviado__isnull=False)
                    & ~Q(tentativas__arquivo_enviado="")
                )
            )
            .distinct()
            .count()
        )

        is_concluida = (qt_visualizados >= qt_conteudos) and (qt_tentativas >= qt_atividades)

        if is_concluida and not prog_aula.is_concluida:
            prog_aula.is_concluida = True
            prog_aula.data_conclusao = timezone.now()
            prog_aula.save(update_fields=["is_concluida", "data_conclusao"])
            ProgressoService.recalcular_modulo(matricula, aula.modulo)
        elif not is_concluida and prog_aula.is_concluida:
            prog_aula.is_concluida = False
            prog_aula.data_conclusao = None
            prog_aula.save(update_fields=["is_concluida", "data_conclusao"])
            ProgressoService.recalcular_modulo(matricula, aula.modulo)

    @staticmethod
    def recalcular_modulo(matricula: MatriculaCurso, modulo):
        prog_modulo = ProgressoModulo.objects.get(matricula=matricula, modulo=modulo)
        aulas_obrig = Aula.objects.filter(modulo=modulo, is_obigatoria=True).count()

        aulas_concluidas = ProgressoAula.objects.filter(
            matricula=matricula,
            aula__modulo=modulo,
            aula__is_obigatoria=True,
            is_concluida=True,
        ).count()

        percent = int((aulas_concluidas / aulas_obrig) * 100) if aulas_obrig > 0 else 100
        prog_modulo.percentual = percent

        if percent >= 100 and not prog_modulo.is_concluido:
            prog_modulo.is_concluido = True
            prog_modulo.data_conclusao = timezone.now()
        elif percent < 100 and prog_modulo.is_concluido:
            prog_modulo.is_concluido = False
            prog_modulo.data_conclusao = None

        prog_modulo.save(update_fields=["percentual", "is_concluido", "data_conclusao"])

        # Propaga recalculo para o curso.
        ProgressoService.recalcular_curso(matricula)

    @staticmethod
    def recalcular_curso(matricula: MatriculaCurso):
        modulos = matricula.curso.modulos.filter(is_active=True).count()
        modulos_concluidos = ProgressoModulo.objects.filter(
            matricula=matricula,
            modulo__is_active=True,
            is_concluido=True,
        ).count()

        percent = int((modulos_concluidos / modulos) * 100) if modulos > 0 else 100
        matricula.progresso_percentual = percent

        if percent >= matricula.curso.progresso_minimo and matricula.status != "concluida":
            # Poderia checar nota minima tambem.
            matricula.status = "concluida"
            matricula.data_conclusao = timezone.now()
        elif percent < matricula.curso.progresso_minimo and matricula.status == MatriculaCurso.Status.CONCLUIDA:
            matricula.status = MatriculaCurso.Status.ATIVA
            matricula.data_conclusao = None

        matricula.save(update_fields=["progresso_percentual", "status", "data_conclusao"])
