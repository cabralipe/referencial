"""Modelos do wrapper de cursos (estilo AVAMEC)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from core.mixins import TenantModel


class Curso(TenantModel):
    class Categoria(models.TextChoices):
        FORMACAO = "formacao", "Formação"
        AVAMEC = "avamec", "AVAMEC"

    nome = models.CharField(max_length=255)
    categoria = models.CharField(max_length=40, choices=Categoria.choices, default=Categoria.AVAMEC)
    descricao = models.TextField(blank=True)
    objetivos = models.TextField(blank=True)
    carga_horaria_total = models.PositiveIntegerField(default=0)
    carga_horaria_presencial = models.PositiveIntegerField(default=0)
    carga_horaria_sincrona = models.PositiveIntegerField(default=0)
    carga_horaria_plataforma = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=30, default="rascunho")
    carga_presencial = models.PositiveIntegerField(default=0)
    carga_sincrona = models.PositiveIntegerField(default=0)
    carga_producao = models.PositiveIntegerField(default=0)
    publicado = models.BooleanField(default=False)
    regras_certificacao_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("nome",)
        indexes = [
            models.Index(fields=["cliente", "publicado"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class CursoModulo(TenantModel):
    class Tipo(models.TextChoices):
        APRESENTACAO = "APRESENTACAO", "Apresentação"
        MODULO = "MODULO", "Módulo"
        BANCO_PLANOS = "BANCO_PLANOS", "Banco de Planos"
        FORUM_GERAL = "FORUM_GERAL", "Fórum Geral"
        BIBLIOTECA = "BIBLIOTECA", "Biblioteca"
        ENTREGA_FINAL = "ENTREGA_FINAL", "Entrega Final"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="modulos")
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    ordem = models.PositiveIntegerField(default=0)
    carga_horaria = models.PositiveIntegerField(default=0)
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.MODULO)

    class Meta:
        ordering = ("ordem", "id")
        unique_together = ("curso", "ordem", "tipo", "titulo")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.curso_id}:{self.titulo}"


class CursoItem(TenantModel):
    class Tipo(models.TextChoices):
        VIDEO = "VIDEO", "Vídeo"
        TEXTO = "TEXTO", "Texto"
        CADERNO = "CADERNO", "Caderno"
        TAREFA = "TAREFA", "Tarefa"
        FORUM = "FORUM", "Fórum"
        FORMULARIO = "FORMULARIO", "Formulário"
        CHECKLIST = "CHECKLIST", "Checklist"
        ATIVIDADE = "ATIVIDADE", "Atividade"

    modulo = models.ForeignKey(CursoModulo, on_delete=models.CASCADE, related_name="itens")
    ordem = models.PositiveIntegerField(default=0)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=255)
    conteudo = models.TextField(blank=True)
    payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("ordem", "id")
        unique_together = ("modulo", "ordem", "titulo")
        indexes = [
            models.Index(fields=["cliente", "tipo"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.modulo_id}:{self.titulo}"


class CursoAviso(TenantModel):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="avisos")
    titulo = models.CharField(max_length=255)
    corpo = models.TextField()
    publicado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-publicado_em", "-created_at")


class CursoCronogramaItem(TenantModel):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="cronograma_itens")
    semana = models.CharField(max_length=120, blank=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("ordem", "id")


class CursoProgresso(TenantModel):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="progressos")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cursos_progressos",
    )
    percentual = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("curso", "usuario")
        indexes = [
            models.Index(fields=["cliente", "usuario"]),
        ]


class CursoProgressoItem(TenantModel):
    progresso = models.ForeignKey(CursoProgresso, on_delete=models.CASCADE, related_name="itens")
    item = models.ForeignKey(CursoItem, on_delete=models.CASCADE, related_name="progresso_itens", null=True, blank=True)
    referencia_tipo = models.CharField(max_length=50, blank=True)
    referencia_id = models.CharField(max_length=64, blank=True)
    concluido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "concluido_em"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["progresso", "item"],
                condition=models.Q(item__isnull=False),
                name="uniq_curso_progresso_item_por_item",
            ),
        ]


class CursoParticipacao(TenantModel):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="participacoes")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cursos_participacoes",
    )
    presenca_presencial = models.BooleanField(default=False)
    encontros_sincronos_presentes = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("curso", "usuario")


class PlanoAulaResposta(TenantModel):
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        ENVIADO = "ENVIADO", "Enviado"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="planos_aula")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="planos_aula_respostas",
    )
    formulario = models.ForeignKey("dynamicforms.FormularioDinamico", on_delete=models.PROTECT, related_name="planos_aula")
    titulo = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    compartilhado_banco = models.BooleanField(default=False)
    enviado_em = models.DateTimeField(null=True, blank=True)
    bloqueado_em = models.DateTimeField(null=True, blank=True)
    dados_cache_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=["cliente", "usuario", "curso"]),
            models.Index(fields=["cliente", "status"]),
        ]


class PlanoAula(TenantModel):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_REVISAO = "em_revisao", "Em revisão"
        APROVADO = "aprovado", "Aprovado"
        PUBLICADO = "publicado", "Publicado"

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="planos_estruturados")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="planos_estruturados",
    )
    escola = models.CharField(max_length=255, blank=True)
    etapa_modalidade = models.CharField(max_length=255, blank=True)
    componente_curricular = models.CharField(max_length=255, blank=True)
    unidade_tematica = models.CharField(max_length=255, blank=True)
    habilidades = models.JSONField(default=list, blank=True)
    objetivos = models.TextField(blank=True)
    conteudos = models.TextField(blank=True)
    metodologia = models.TextField(blank=True)
    recursos = models.TextField(blank=True)
    avaliacao = models.TextField(blank=True)
    estrategias_recomposicao = models.TextField(blank=True)
    estrategias_inclusivas = models.TextField(blank=True)
    referencias = models.TextField(blank=True)
    metas_ppp = models.JSONField(default=list, blank=True)
    habilidades_referencial = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=["cliente", "curso", "autor"]),
            models.Index(fields=["cliente", "status"]),
            models.Index(fields=["cliente", "escola"]),
        ]


class Rubrica(TenantModel):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="rubricas")
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ("nome",)
        unique_together = ("cliente", "curso", "nome")


class RubricaCriterio(TenantModel):
    rubrica = models.ForeignKey(Rubrica, on_delete=models.CASCADE, related_name="criterios")
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    pontuacao_maxima = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("ordem", "id")
        unique_together = ("rubrica", "nome")


class AvaliacaoPlano(TenantModel):
    plano = models.ForeignKey(PlanoAula, on_delete=models.CASCADE, related_name="avaliacoes")
    avaliador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="avaliacoes_planos",
    )
    criterio = models.ForeignKey(RubricaCriterio, on_delete=models.CASCADE, related_name="avaliacoes")
    pontuacao = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    comentario = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("plano", "avaliador", "criterio")
        indexes = [
            models.Index(fields=["cliente", "plano", "avaliador"]),
        ]


class PlanoAulaPublicacao(TenantModel):
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        ENVIADO = "ENVIADO", "Enviado"
        APROVADO = "APROVADO", "Aprovado"
        PUBLICADO = "PUBLICADO", "Publicado"

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="planos_aula_publicacoes",
    )
    resposta_formulario = models.ForeignKey(
        PlanoAulaResposta,
        on_delete=models.CASCADE,
        related_name="publicacoes",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    allow_comments = models.BooleanField(default=True)
    payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=["cliente", "status"]),
            models.Index(fields=["cliente", "autor"]),
        ]


class CursoCertificadoEmitido(TenantModel):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="certificados_emitidos")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificados_curso_emitidos",
    )
    codigo = models.CharField(max_length=64, unique=True, default="", blank=True)
    payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("curso", "usuario")

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.codigo:
            self.codigo = uuid.uuid4().hex
        super().save(*args, **kwargs)
