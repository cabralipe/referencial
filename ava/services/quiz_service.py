from django.db import transaction
from django.utils import timezone

from ava.models import (
    Atividade,
    AtividadeForumAnexo,
    AtividadeForumMensagem,
    AtividadeTentativa,
    AtividadeTentativaArquivo,
    MatriculaCurso,
    QuizAlternativa,
    QuizQuestao,
    QuizRespostaItem,
)

from .progress_service import ProgressoService
from .access_control import user_can_access_activity_by_eixo


class AtividadeService:
    @staticmethod
    @transaction.atomic
    def iniciar_tentativa(aluno, atividade: Atividade):
        """
        Inicia uma tentativa para a atividade. Verifica limite de tentativas.
        """
        if not user_can_access_activity_by_eixo(aluno, atividade):
            return None, "Esta atividade esta restrita por eixo para este usuario."

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
            cliente_id=atividade.cliente_id,
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

        questoes = QuizQuestao.objects.filter(atividade=atividade)
        peso_total = sum(q.peso for q in questoes) or 1.0

        tentativa.respostas_quiz.all().delete()

        for questao in questoes:
            resposta_dada = dados_respostas.get(str(questao.id))

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
                            nota_item = float(atividade.nota_maxima) * (float(questao.peso) / float(peso_total))
                            nota_total += nota_item
                    except QuizAlternativa.DoesNotExist:
                        pass
                else:
                    texto_livre = str(resposta_dada)

            QuizRespostaItem.objects.create(
                cliente_id=tentativa.cliente_id,
                tentativa=tentativa,
                questao=questao,
                alternativa_selecionada=alternativa_obj,
                texto_livre=texto_livre,
                is_correta=is_correta,
                nota_item=nota_item,
            )

        tentativa.nota_obtida = nota_total
        tentativa.data_envio = timezone.now()

        if atividade.correcao_automatica or atividade.tipo == Atividade.Tipo.QUIZ:
            tentativa.status = AtividadeTentativa.Status.CORRIGIDA
            tentativa.data_correcao = timezone.now()
        else:
            tentativa.status = AtividadeTentativa.Status.ENVIADA

        tentativa.save()
        AtividadeService._recalcular_progresso_da_atividade(tentativa)
        return tentativa

    @staticmethod
    @transaction.atomic
    def submeter_tarefa_discursiva(tentativa: AtividadeTentativa, texto_resposta: str, arquivos=None):
        """
        Envia uma resposta tipo texto/arquivo que depende de correção manual.
        Aceita uma lista de arquivos (ou um único arquivo para retrocompatibilidade).
        """
        tentativa.texto_resposta = texto_resposta

        if arquivos:
            if not isinstance(arquivos, (list, tuple)):
                arquivos = [arquivos]
            arquivos_validos = [arq for arq in arquivos if getattr(arq, "name", "")]
            for arq in arquivos_validos:
                AtividadeTentativaArquivo.objects.create(
                    cliente_id=tentativa.cliente_id,
                    tentativa=tentativa,
                    arquivo=arq,
                    nome_original=getattr(arq, "name", ""),
                )

        tentativa.data_envio = timezone.now()
        tentativa.status = AtividadeTentativa.Status.ENVIADA
        tentativa.save()
        AtividadeService._recalcular_progresso_da_atividade(tentativa)
        return tentativa

    @staticmethod
    @transaction.atomic
    def publicar_mensagem_forum(
        *,
        aluno,
        atividade: Atividade,
        texto: str,
        arquivos,
        resposta_para: AtividadeForumMensagem | None = None,
    ):
        texto = (texto or "").strip()
        arquivos_validos = [arquivo for arquivo in arquivos if getattr(arquivo, "name", "")]

        if not texto and not arquivos_validos:
            raise ValueError("Escreva uma mensagem ou envie pelo menos um arquivo.")

        if resposta_para and resposta_para.atividade_id != atividade.id:
            raise ValueError("A resposta selecionada não pertence a este fórum.")

        tentativa = (
            AtividadeTentativa.objects.filter(aluno=aluno, atividade=atividade)
            .order_by("-data_inicio")
            .first()
        )
        now = timezone.now()

        if tentativa is None:
            tentativa = AtividadeTentativa.objects.create(
                cliente_id=atividade.cliente_id,
                atividade=atividade,
                aluno=aluno,
                status=AtividadeTentativa.Status.CORRIGIDA,
                texto_resposta=texto,
                data_envio=now,
                data_correcao=now,
            )
        else:
            update_fields = []
            if tentativa.status != AtividadeTentativa.Status.CORRIGIDA:
                tentativa.status = AtividadeTentativa.Status.CORRIGIDA
                update_fields.append("status")
            if not tentativa.data_envio:
                tentativa.data_envio = now
                update_fields.append("data_envio")
            if not tentativa.data_correcao:
                tentativa.data_correcao = now
                update_fields.append("data_correcao")
            if texto and not tentativa.texto_resposta:
                tentativa.texto_resposta = texto
                update_fields.append("texto_resposta")
            if update_fields:
                tentativa.save(update_fields=update_fields)

        mensagem = AtividadeForumMensagem.objects.create(
            cliente_id=atividade.cliente_id,
            atividade=atividade,
            autor=aluno,
            resposta_para=resposta_para,
            texto=texto,
        )

        for arquivo in arquivos_validos:
            AtividadeForumAnexo.objects.create(
                cliente_id=atividade.cliente_id,
                mensagem=mensagem,
                arquivo=arquivo,
                nome_original=getattr(arquivo, "name", ""),
            )

        AtividadeService._recalcular_progresso_da_atividade(tentativa)
        return mensagem, tentativa

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
        Aplica a correção manual de uma tentativa enviada pelo aluno.
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
        AtividadeService._recalcular_progresso_da_atividade(tentativa)
        return tentativa

    @staticmethod
    def _recalcular_progresso_da_atividade(tentativa: AtividadeTentativa):
        try:
            matricula = MatriculaCurso.objects.get(
                curso=tentativa.atividade.aula.modulo.curso,
                aluno=tentativa.aluno,
            )
            ProgressoService.recalcular_aula(matricula, tentativa.atividade.aula)
        except MatriculaCurso.DoesNotExist:
            pass
