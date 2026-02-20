"""Modelos para documentos em consulta pública e manifestações abertas."""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.mixins import TenantModel


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
    cpf = models.CharField(max_length=14)
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
