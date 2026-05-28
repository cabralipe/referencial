from django.conf import settings
from django.db import models

from core.mixins import TenantModel

from .lesson import Aula


class Atividade(TenantModel):
    class Tipo(models.TextChoices):
        QUIZ = "quiz", "Quiz Objetivo"
        TAREFA = "tarefa", "Tarefa Discursiva"
        ENVIO_ARQUIVO = "envio_arquivo", "Envio de Arquivo"
        QUESTIONARIO = "questionario", "Question\u00e1rio Simples (Pesquisa)"
        REFLEXAO = "reflexao", "Reflex\u00e3o Guiada"
        FORUM = "forum", "Fórum Interativo"

    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="atividades")
    tipo = models.CharField("Tipo da Atividade", max_length=30, choices=Tipo.choices)
    titulo = models.CharField("T\u00edtulo", max_length=255)
    descricao = models.TextField("Descri\u00e7\u00e3o/Enunciado", blank=True)
    instrucoes = models.TextField("Instru\u00e7\u00f5es de envio", blank=True)

    nota_maxima = models.DecimalField("Nota M\u00e1xima", max_digits=5, decimal_places=2, default=100.0)
    peso = models.DecimalField("Peso na composi\u00e7\u00e3o da m\u00e9dia", max_digits=5, decimal_places=2, default=1.0)
    is_obrigatoria = models.BooleanField("Atividade Obrigat\u00f3ria?", default=True)
    prazo_envio = models.DateTimeField("Prazo fatal (Opcional)", null=True, blank=True)
    tentativas_permitidas = models.PositiveIntegerField("M\u00e1ximo de Tentativas", default=1, help_text="0 para ilimitadas")

    correcao_automatica = models.BooleanField(
        "Corre\u00e7\u00e3o Autom\u00e1tica?",
        default=False,
        help_text="V\u00e1lido para Quizzes e Question\u00e1rios",
    )
    criterio_aprovacao = models.DecimalField("Nota m\u00ednima (se aplic\u00e1vel)", max_digits=5, decimal_places=2, default=70.0)

    class Meta:
        verbose_name = "Atividade"
        verbose_name_plural = "Atividades"
        ordering = ["aula"]

    def __str__(self):
        return self.titulo


class QuizQuestao(TenantModel):
    atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE, related_name="questoes")
    enunciado = models.TextField("Enunciado da Quest\u00e3o")
    peso = models.DecimalField("Peso da Quest\u00e3o", max_digits=5, decimal_places=2, default=1.0)
    ordem = models.PositiveIntegerField("Ordem Exibi\u00e7\u00e3o", default=0)
    feedback_acerto = models.TextField("Feedback (Acerto)", blank=True)
    feedback_erro = models.TextField("Feedback (Erro)", blank=True)

    class Meta:
        verbose_name = "Quest\u00e3o de Quiz"
        verbose_name_plural = "Quest\u00f5es de Quiz"
        ordering = ["ordem"]

    def __str__(self):
        return f"Q{self.ordem}: {self.enunciado[:50]}..."


class QuizAlternativa(TenantModel):
    questao = models.ForeignKey(QuizQuestao, on_delete=models.CASCADE, related_name="alternativas")
    texto = models.TextField("Texto da Alternativa")
    is_correta = models.BooleanField("Alternativa Correta?", default=False)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    feedback_especifico = models.TextField("Feedback Espec\u00edfico", blank=True)

    class Meta:
        ordering = ["ordem"]

    def __str__(self):
        return f"{'[V]' if self.is_correta else '[F]'} {self.texto[:30]}"


class AtividadeTentativa(TenantModel):
    class Status(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        ENVIADA = "enviada", "Enviada / Aguardando Corre\u00e7\u00e3o"
        CORRIGIDA = "corrigida", "Corrigida"

    atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE, related_name="tentativas")
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="atividades_tentativas")
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.EM_ANDAMENTO)

    nota_obtida = models.DecimalField("Nota Obtida", max_digits=5, decimal_places=2, null=True, blank=True)
    feedback_tutor = models.TextField("Feedback do Tutor", blank=True)
    corrigido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="atividades_corrigidas",
    )

    data_inicio = models.DateTimeField(auto_now_add=True)
    data_envio = models.DateTimeField(null=True, blank=True)
    data_correcao = models.DateTimeField(null=True, blank=True)

    texto_resposta = models.TextField("Resposta Discursiva", blank=True)
    arquivo_enviado = models.FileField("Arquivo Enviado (legado)", upload_to="ava/tentativas/arquivos/", null=True, blank=True)

    class Meta:
        verbose_name = "Tentativa de Atividade"
        verbose_name_plural = "Tentativas de Atividades"
        ordering = ["-data_inicio"]
        indexes = [
            models.Index(fields=["cliente", "aluno", "atividade"]),
        ]


class AtividadeTentativaArquivo(TenantModel):
    tentativa = models.ForeignKey(AtividadeTentativa, on_delete=models.CASCADE, related_name="arquivos")
    arquivo = models.FileField("Arquivo", upload_to="ava/tentativas/arquivos/")
    nome_original = models.CharField("Nome original", max_length=255, blank=True)

    class Meta:
        verbose_name = "Arquivo de Tentativa"
        verbose_name_plural = "Arquivos de Tentativas"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.arquivo and not self.nome_original:
            self.nome_original = self.arquivo.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_original or f"Arquivo {self.pk}"


class QuizRespostaItem(TenantModel):
    tentativa = models.ForeignKey(AtividadeTentativa, on_delete=models.CASCADE, related_name="respostas_quiz")
    questao = models.ForeignKey(QuizQuestao, on_delete=models.CASCADE, related_name="respostas_alunos")
    alternativa_selecionada = models.ForeignKey(
        QuizAlternativa,
        on_delete=models.CASCADE,
        related_name="selecoes_alunos",
        null=True,
        blank=True,
    )
    texto_livre = models.TextField("Resposta em texto (se aplic\u00e1vel)", blank=True)
    is_correta = models.BooleanField("Acertou?", default=False)
    nota_item = models.DecimalField("Nota neste item", max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ["tentativa", "questao"]


class AtividadeForumMensagem(TenantModel):
    atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE, related_name="mensagens_forum")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensagens_forum_ava")
    resposta_para = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respostas",
    )
    texto = models.TextField("Mensagem", blank=True)
    editado_em = models.DateTimeField("Editado em", null=True, blank=True)

    class Meta:
        verbose_name = "Mensagem de Fórum"
        verbose_name_plural = "Mensagens de Fórum"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["cliente", "atividade", "created_at"]),
            models.Index(fields=["cliente", "autor", "created_at"]),
        ]

    def __str__(self):
        return f"{self.atividade.titulo} - {self.autor_id} - {self.created_at:%d/%m/%Y %H:%M}"


class AtividadeForumAnexo(TenantModel):
    mensagem = models.ForeignKey(AtividadeForumMensagem, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField("Arquivo", upload_to="ava/forum/anexos/")
    nome_original = models.CharField("Nome original", max_length=255, blank=True)

    class Meta:
        verbose_name = "Anexo de Mensagem do Fórum"
        verbose_name_plural = "Anexos de Mensagens do Fórum"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["cliente", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.arquivo and not self.nome_original:
            self.nome_original = self.arquivo.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_original or f"Anexo {self.pk}"
