from django.utils import timezone
from ava.models import (
    MatriculaCurso, Aula, ConteudoAula,
    ProgressoAula, ProgressoConteudo, ProgressoModulo, Atividade
)

class ProgressoService:
    """
    Serviço central de cálculo e registro de progressos no AVA.
    """

    @staticmethod
    def marcar_conteudo_visualizado(aluno, conteudo_id: int):
        try:
            conteudo = ConteudoAula.objects.select_related("aula__modulo__curso").get(id=conteudo_id)
            matricula = MatriculaCurso.objects.get(curso=conteudo.aula.modulo.curso, aluno=aluno)
        except (ConteudoAula.DoesNotExist, MatriculaCurso.DoesNotExist):
            return False

        # Cria a árvore de progresso se não existir
        ProgressoService._garantir_progressos(matricula, conteudo.aula)

        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=conteudo.aula)
        prog_conteudo, created = ProgressoConteudo.objects.get_or_create(
            progresso_aula=prog_aula,
            conteudo=conteudo
        )

        if not prog_conteudo.is_visualizado:
            prog_conteudo.is_visualizado = True
            prog_conteudo.data_visualizacao = timezone.now()
            prog_conteudo.save(update_fields=["is_visualizado", "data_visualizacao"])
            
            # Recalcula aula, modulo, curso
            ProgressoService.recalcular_aula(matricula, conteudo.aula)
            return True
        return False

    @staticmethod
    def _garantir_progressos(matricula, aula):
        ProgressoModulo.objects.get_or_create(matricula=matricula, modulo=aula.modulo)
        ProgressoAula.objects.get_or_create(matricula=matricula, aula=aula)

    @staticmethod
    def recalcular_aula(matricula: MatriculaCurso, aula: Aula):
        """
        Verifica se a aula foi concluida baseado nos conteúdos obrigatórios e atividades obrigatórias enviadas.
        """
        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=aula)
        
        qt_conteudos = ConteudoAula.objects.filter(aula=aula, is_obrigatorio=True).count()
        qt_visualizados = ProgressoConteudo.objects.filter(
            progresso_aula=prog_aula, 
            conteudo__is_obrigatorio=True, 
            is_visualizado=True
        ).count()

        # Verifica atividades obrigatórias com tentativa enviada/corrigida
        qt_atividades = Atividade.objects.filter(aula=aula, is_obrigatoria=True).count()
        qt_tentativas = Atividade.objects.filter(
            aula=aula, 
            is_obrigatoria=True,
            tentativas__aluno=matricula.aluno,
            tentativas__status__in=["enviada", "corrigida"]
        ).count()

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
            is_concluida=True
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
        
        # Propaga recalculo p/ Curso
        ProgressoService.recalcular_curso(matricula)

    @staticmethod
    def recalcular_curso(matricula: MatriculaCurso):
        modulos = matricula.curso.modulos.filter(is_active=True).count()
        modulos_concluidos = ProgressoModulo.objects.filter(
            matricula=matricula,
            modulo__is_active=True,
            is_concluido=True
        ).count()

        percent = int((modulos_concluidos / modulos) * 100) if modulos > 0 else 100
        matricula.progresso_percentual = percent

        if percent >= matricula.curso.progresso_minimo and matricula.status != "concluida":
            # Poderia checar nota minima também
            matricula.status = "concluida"
            matricula.data_conclusao = timezone.now()
        
        matricula.save(update_fields=["progresso_percentual", "status", "data_conclusao"])
