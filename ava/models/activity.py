from django.db import models
from django.conf import settings
from core.mixins import TenantModel
from .lesson import Aula

class Atividade(TenantModel):
    class Tipo(models.TextChoices):
        QUIZ = "quiz", "Quiz Objetivo"
        TAREFA = "tarefa", "Tarefa Discursiva"
        ENVIO_ARQUIVO = "envio_arquivo", "Envio de Arquivo"
        QUESTIONARIO = "questionario", "Questionário Simples (Pesquisa)"
        REFLEXAO = "reflexao", "Reflexão Guiada"

    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="atividades")
    tipo = models.CharField("Tipo da Atividade", max_length=30, choices=Tipo.choices)
    titulo = models.CharField("Título", max_length=255)
    descricao = models.TextField("Descrição/Enunciado", blank=True)
    instrucoes = models.TextField("Instruções de envio", blank=True)
    
    nota_maxima = models.DecimalField("Nota Máxima", max_digits=5, decimal_places=2, default=100.0)
    peso = models.DecimalField("Peso na composição da média", max_digits=5, decimal_places=2, default=1.0)
    is_obrigatoria = models.BooleanField("Atividade Obrigatória?", default=True)
    prazo_envio = models.DateTimeField("Prazo fatal (Opcional)", null=True, blank=True)
    tentativas_permitidas = models.PositiveIntegerField("Máximo de Tentativas", default=1, help_text="0 para ilimitadas")
    
    correcao_automatica = models.BooleanField("Correção Automática?", default=False, help_text="Válido para Quizzes e Questionários")
    criterio_aprovacao = models.DecimalField("Nota mínima (se aplicável)", max_digits=5, decimal_places=2, default=70.0)

    class Meta:
        verbose_name = "Atividade"
        verbose_name_plural = "Atividades"
        ordering = ["aula"]

    def __str__(self):
        return self.titulo

class QuizQuestao(TenantModel):
    atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE, related_name="questoes")
    enunciado = models.TextField("Enunciado da Questão")
    peso = models.DecimalField("Peso da Questão", max_digits=5, decimal_places=2, default=1.0)
    ordem = models.PositiveIntegerField("Ordem Exibição", default=0)
    feedback_acerto = models.TextField("Feedback (Acerto)", blank=True)
    feedback_erro = models.TextField("Feedback (Erro)", blank=True)

    class Meta:
        verbose_name = "Questão de Quiz"
        verbose_name_plural = "Questões de Quiz"
        ordering = ["ordem"]

    def __str__(self):
        return f"Q{self.ordem}: {self.enunciado[:50]}..."

class QuizAlternativa(TenantModel):
    questao = models.ForeignKey(QuizQuestao, on_delete=models.CASCADE, related_name="alternativas")
    texto = models.TextField("Texto da Alternativa")
    is_correta = models.BooleanField("Alternativa Correta?", default=False)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    feedback_especifico = models.TextField("Feedback Específico", blank=True)

    class Meta:
        ordering = ["ordem"]

    def __str__(self):
        return f"{'[V]' if self.is_correta else '[F]'} {self.texto[:30]}"

class AtividadeTentativa(TenantModel):
    class Status(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        ENVIADA = "enviada", "Enviada / Aguardando Correção"
        CORRIGIDA = "corrigida", "Corrigida"

    atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE, related_name="tentativas")
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="atividades_tentativas")
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.EM_ANDAMENTO)
    
    nota_obtida = models.DecimalField("Nota Obtida", max_digits=5, decimal_places=2, null=True, blank=True)
    feedback_tutor = models.TextField("Feedback do Tutor", blank=True)
    corrigido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="atividades_corrigidas")
    
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_envio = models.DateTimeField(null=True, blank=True)
    data_correcao = models.DateTimeField(null=True, blank=True)

    texto_resposta = models.TextField("Resposta Discursiva", blank=True)
    arquivo_enviado = models.FileField("Arquivo Enviado", upload_to="ava/tentativas/arquivos/", null=True, blank=True)

    class Meta:
        verbose_name = "Tentativa de Atividade"
        verbose_name_plural = "Tentativas de Atividades"
        ordering = ["-data_inicio"]
        indexes = [
            models.Index(fields=["cliente", "aluno", "atividade"]),
        ]

class QuizRespostaItem(TenantModel):
    tentativa = models.ForeignKey(AtividadeTentativa, on_delete=models.CASCADE, related_name="respostas_quiz")
    questao = models.ForeignKey(QuizQuestao, on_delete=models.CASCADE, related_name="respostas_alunos")
    alternativa_selecionada = models.ForeignKey(QuizAlternativa, on_delete=models.CASCADE, related_name="selecoes_alunos", null=True, blank=True)
    texto_livre = models.TextField("Resposta em texto (se aplicável)", blank=True)
    is_correta = models.BooleanField("Acertou?", default=False)
    nota_item = models.DecimalField("Nota neste item", max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ["tentativa", "questao"]
