"""Modelos para documentos em consulta pública, manifestações e formulários de inscrição."""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.mixins import TenantModel

_AREAS_ATUACAO_PADRAO = [
    "Educação",
    "Saúde",
    "Assistência Social",
    "Cultura",
    "Gestão Pública",
    "Sociedade Civil",
]

_REPRESENTACOES_PADRAO = [
    "Poder Executivo",
    "Poder Legislativo",
    "Conselho Municipal de Educação – CME",
    "Ministério Público",
    "Coordenação Geral do Referencial Curricular",
    "Articulador(a) do Território",
    "GT Educação Infantil",
    "GT Ensino Fundamental",
    "GT Educação de Jovens e Adultos – EJA",
    "GT Educação Especial",
    "GT BNCC Computação",
    "Gestor(a) Escolar",
    "Professor(a)",
    "Estudante",
    "Família / Responsável",
    "Representação Indígena",
    "Representação Quilombola",
    "Comunidade do Campo",
    "Assentamento",
]


def _upload_to(instance: "ConsultaPublica", filename: str) -> str:
    """Gera caminho de upload agrupando por cliente."""
    base = slugify(Path(filename).stem) or "documento"
    ext = Path(filename).suffix or ".pdf"
    cliente_part = f"cliente_{instance.cliente_id or 'desconhecido'}"
    return f"consultas/{cliente_part}/{base}{ext}"


def _token() -> str:
    return token_urlsafe(12)


class ConsultaPublica(TenantModel):
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    token_acesso = models.CharField(max_length=32, unique=True, default=_token)
    descricao = models.TextField(blank=True)
    pdf = models.FileField(upload_to=_upload_to)
    data_publicacao = models.DateField()
    data_validade = models.DateField(null=True, blank=True)
    data_fechamento = models.DateField(null=True, blank=True)
    perguntas_votacao = models.JSONField(default=list, blank=True)
    # Format: [{"pergunta": "...", "opcoes": ["A", "B"]}, ...]
    ativa = models.BooleanField(default=True)
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultas_publicas_criadas",
    )

    class Meta:
        unique_together = ("cliente", "slug")
        indexes = [
            models.Index(fields=["cliente", "slug"]),
            models.Index(fields=["cliente", "data_publicacao"]),
        ]
        ordering = ("-data_publicacao", "-created_at")

    def __str__(self) -> str:  # pragma: no cover
        return self.titulo

    @property
    def esta_disponivel(self) -> bool:
        hoje = timezone.localdate()
        if not self.ativa:
            return False
        if self.data_publicacao and hoje < self.data_publicacao:
            return False
        if self.data_fechamento and hoje > self.data_fechamento:
            return False
        if self.data_validade and hoje > self.data_validade:
            return False
        return True


class ManifestacaoPublica(TenantModel):
    consulta = models.ForeignKey(
        ConsultaPublica,
        on_delete=models.CASCADE,
        related_name="manifestacoes",
    )
    pagina = models.PositiveIntegerField(null=True, blank=True)
    comentario = models.TextField()
    votos = models.JSONField(default=list, blank=True)
    # Format: ["answer_for_q0", "answer_for_q1", ...]
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, blank=True, default="")
    cidade = models.CharField(max_length=120)
    estado = models.CharField(max_length=2)
    contato_email = models.EmailField(blank=True)
    area_atuacao_profissional = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "consulta"]),
            models.Index(fields=["cliente", "consulta", "pagina"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        destino = f"p.{self.pagina}" if self.pagina else "geral"
        return f"Manifestação {destino} em {self.consulta_id}"


class FormularioInscricao(TenantModel):
    """Formulário de inscrição configurável para audiências públicas."""

    titulo = models.CharField(max_length=255, default="Audiência Pública do Referencial Curricular")
    subtitulo = models.CharField(max_length=255, blank=True, default="Ficha de Inscrição")
    descricao = models.TextField(blank=True)
    token_acesso = models.CharField(max_length=32, unique=True, default=_token)
    ativo = models.BooleanField(default=True)
    opcoes_area_atuacao = models.JSONField(default=list, blank=True)
    opcoes_representacao = models.JSONField(default=list, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="formularios_inscricao_criados",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return self.titulo

    @property
    def public_url(self) -> str:
        return f"/inscricoes/{self.token_acesso}"


class InscricaoPublica(TenantModel):
    """Registro de inscrição preenchida via formulário público."""

    formulario = models.ForeignKey(
        FormularioInscricao,
        on_delete=models.CASCADE,
        related_name="inscricoes",
    )
    nome_completo = models.CharField(max_length=255)
    instituicao_comunidade = models.CharField(max_length=255, blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    areas_atuacao = models.JSONField(default=list, blank=True)
    area_atuacao_outro = models.CharField(max_length=255, blank=True)
    representacoes = models.JSONField(default=list, blank=True)
    representacao_outro = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "formulario"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return f"Inscrição de {self.nome_completo} em {self.formulario_id}"
