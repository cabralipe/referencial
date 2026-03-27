from django.db import transaction
from django.utils import timezone

from ava.models import (
    Atividade,
    AtividadeTentativa,
    MatriculaCurso,
    QuizAlternativa,
    QuizQuestao,
    QuizRespostaItem,
)

from .progress_service import ProgressoService


class AtividadeService:
    @staticmethod
    @transaction.atomic
    def iniciar_tentativa(aluno, atividade: Atividade):
        """
        Inicia uma tentativa para a atividade. Verifica limite de tentativas.
        """
        tentativa_em_andamento = (
            AtividadeTentativa.objects.filter(
                aluno=aluno,
                atividade=atividade,
                status=AtividadeTentativa.Status.EM_ANDAMENTO,
            )
            .order_by("-data_inicio")
            .first()
        )
        if tentativa_em_andamento:
            return tentativa_em_andamento, None

        tentativas_finalizadas = AtividadeTentativa.objects.filter(
            aluno=aluno,
            atividade=atividade,
            status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA],
        ).count()

        if atividade.tentativas_permitidas > 0 and tentativas_finalizadas >= atividade.tentativas_permitidas:
            return None, "Limite de tentativas alcancado."

        tentativa = AtividadeTentativa.objects.create(
            aluno=aluno,
            atividade=atividade,
            status=AtividadeTentativa.Status.EM_ANDAMENTO,
        )
        return tentativa, None

    @staticmethod
    @transaction.atomic
    def submeter_quiz(tentativa: AtividadeTentativa, dados_respostas: dict):
        """
        Processa as respostas de um questionario/quiz e calcula nota se for automatico.
        dados_respostas = { questao_id: alternativa_id ou "texto livre" }
        """
        atividade = tentativa.atividade
        nota_total = 0.0

        # Obter todas as questoes da atividade.
        questoes = QuizQuestao.objects.filter(atividade=atividade)
        peso_total = sum(q.peso for q in questoes) or 1.0

        for questao in questoes:
            resposta_dada = dados_respostas.get(str(questao.id))

            # Para quiz objetivo, resposta deve ser ID de alternativa.
            alternativa_obj = None
            is_correta = False
            nota_item = 0.0
            texto_livre = ""

            if resposta_dada:
                if str(resposta_dada).isdigit():
                    try:
                        alternativa_obj = QuizAlternativa.objects.get(id=int(resposta_dada), questao=questao)
                        is_correta = alternativa_obj.is_correta
                        if is_correta:
                            # Formula de nota ponderada.
                            nota_item = float(atividade.nota_maxima) * (float(questao.peso) / float(peso_total))
                            nota_total += nota_item
                    except QuizAlternativa.DoesNotExist:
                        pass
                else:
                    texto_livre = str(resposta_dada)

            QuizRespostaItem.objects.create(
                tentativa=tentativa,
                questao=questao,
                alternativa_selecionada=alternativa_obj,
                texto_livre=texto_livre,
                is_correta=is_correta,
                nota_item=nota_item,
            )

        tentativa.nota_obtida = nota_total
        tentativa.data_envio = timezone.now()

        if atividade.correcao_automatica:
            tentativa.status = AtividadeTentativa.Status.CORRIGIDA
            tentativa.data_correcao = timezone.now()
        else:
            tentativa.status = AtividadeTentativa.Status.ENVIADA

        tentativa.save()

        # Recalcular progresso da aula que contempla esta atividade.
        try:
            matricula = MatriculaCurso.objects.get(curso=atividade.aula.modulo.curso, aluno=tentativa.aluno)
            ProgressoService.recalcular_aula(matricula, atividade.aula)
        except MatriculaCurso.DoesNotExist:
            pass

        return tentativa

    @staticmethod
    @transaction.atomic
    def submeter_tarefa_discursiva(tentativa: AtividadeTentativa, texto_resposta: str, arquivo=None):
        """
        Envia uma resposta tipo texto/arquivo que depende de correcao manual.
        """
        tentativa.texto_resposta = texto_resposta
        if arquivo:
            tentativa.arquivo_enviado = arquivo

        tentativa.data_envio = timezone.now()
        tentativa.status = AtividadeTentativa.Status.ENVIADA
        tentativa.save()

        # Recalcular progresso da aula que contempla esta atividade.
        try:
            matricula = MatriculaCurso.objects.get(curso=tentativa.atividade.aula.modulo.curso, aluno=tentativa.aluno)
            ProgressoService.recalcular_aula(matricula, tentativa.atividade.aula)
        except MatriculaCurso.DoesNotExist:
            pass

        return tentativa

    @staticmethod
    @transaction.atomic
    def corrigir_tentativa(
        tentativa: AtividadeTentativa,
        *,
        corretor,
        status: str,
        nota_obtida,
        feedback_tutor: str,
    ):
        """
        Aplica a correcao manual de uma tentativa enviada pelo aluno.
        """
        tentativa.status = status
        tentativa.nota_obtida = nota_obtida
        tentativa.feedback_tutor = feedback_tutor

        update_fields = ["status", "nota_obtida", "feedback_tutor"]

        if status in {AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA} and tentativa.data_envio is None:
            tentativa.data_envio = timezone.now()
            update_fields.append("data_envio")

        if status == AtividadeTentativa.Status.CORRIGIDA:
            tentativa.corrigido_por = corretor
            tentativa.data_correcao = timezone.now()
            update_fields.extend(["corrigido_por", "data_correcao"])
        else:
            tentativa.corrigido_por = None
            tentativa.data_correcao = None
            update_fields.extend(["corrigido_por", "data_correcao"])

        tentativa.save(update_fields=list(dict.fromkeys(update_fields)))

        try:
            matricula = MatriculaCurso.objects.get(curso=tentativa.atividade.aula.modulo.curso, aluno=tentativa.aluno)
            ProgressoService.recalcular_aula(matricula, tentativa.atividade.aula)
        except MatriculaCurso.DoesNotExist:
            pass

        return tentativa
