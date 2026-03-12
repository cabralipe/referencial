from django.utils import timezone
from django.db import transaction
from ava.models import (
    Atividade, AtividadeTentativa, QuizQuestao, QuizAlternativa, QuizRespostaItem, MatriculaCurso
)
from .progress_service import ProgressoService

class AtividadeService:
    @staticmethod
    @transaction.atomic
    def iniciar_tentativa(aluno, atividade: Atividade):
        """
        Inicia uma tentativa para a atividade. Verifica limite de tentativas.
        """
        tentativas_existentes = AtividadeTentativa.objects.filter(aluno=aluno, atividade=atividade).count()
        
        if atividade.tentativas_permitidas > 0 and tentativas_existentes >= atividade.tentativas_permitidas:
            return None, "Limite de tentativas alcançado."
            
        tentativa = AtividadeTentativa.objects.create(
            aluno=aluno,
            atividade=atividade,
            status=AtividadeTentativa.Status.EM_ANDAMENTO
        )
        return tentativa, None

    @staticmethod
    @transaction.atomic
    def submeter_quiz(tentativa: AtividadeTentativa, dados_respostas: dict):
        """
        Processa as respostas de um questionário/quiz e calcula nota se for automático.
        dados_respostas = { questao_id: alternativa_id ou "texto livre" }
        """
        atividade = tentativa.atividade
        nota_total = 0.0
        
        # Obter todas as questões da atividade
        questoes = QuizQuestao.objects.filter(atividade=atividade)
        peso_total = sum(q.peso for q in questoes) or 1.0
        
        for questao in questoes:
            resposta_dada = dados_respostas.get(str(questao.id))
            
            # Avalia se é id de alternativa ou texto
            # Para quiz objetivo a resposta deve ser o ID da alternativa
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
                            # Formula de nota ponderada
                            # Nota máx * (peso questao / peso total)
                            nota_item = float(atividade.nota_maxima) * (float(questao.peso) / float(peso_total))
                            nota_total += nota_item
                    except QuizAlternativa.DoesNotExist:
                        pass
                else:
                    texto_livre = str(resposta_dada)

            # Registra o item
            QuizRespostaItem.objects.create(
                tentativa=tentativa,
                questao=questao,
                alternativa_selecionada=alternativa_obj,
                texto_livre=texto_livre,
                is_correta=is_correta,
                nota_item=nota_item
            )

        tentativa.nota_obtida = nota_total
        tentativa.data_envio = timezone.now()
        
        if atividade.correcao_automatica:
            tentativa.status = AtividadeTentativa.Status.CORRIGIDA
            tentativa.data_correcao = timezone.now()
        else:
            tentativa.status = AtividadeTentativa.Status.ENVIADA

        tentativa.save()

        # Recalcular progresso da aula que contempla esta atividade
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
        Envia uma resposta tipo texto/arquivo que depende de correção manual.
        """
        tentativa.texto_resposta = texto_resposta
        if arquivo:
            tentativa.arquivo_enviado = arquivo
            
        tentativa.data_envio = timezone.now()
        tentativa.status = AtividadeTentativa.Status.ENVIADA
        tentativa.save()

        # Recalcular progresso da aula que contempla esta atividade
        try:
            matricula = MatriculaCurso.objects.get(curso=tentativa.atividade.aula.modulo.curso, aluno=tentativa.aluno)
            ProgressoService.recalcular_aula(matricula, tentativa.atividade.aula)
        except MatriculaCurso.DoesNotExist:
            pass

        return tentativa
