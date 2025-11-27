"""Sincronização entre respostas e textos colaborativos."""

from __future__ import annotations

import logging
import re
from typing import Tuple

from django.utils.html import strip_tags

from curriculum.models import Pergunta, Resposta, TextoColaborativo
from sockets.utils import broadcast_stream_event

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"\s+")


def _normalize_title(pergunta: Pergunta) -> str:
    base = strip_tags(pergunta.texto or "").strip()
    base = _TAG_RE.sub(" ", base)
    prefix = f"Pergunta {pergunta.ordem} — "
    # Garantir limite do campo CharField
    remaining = 255 - len(prefix)
    if remaining < 0:
        remaining = 0
    if len(base) > remaining:
        base = f"{base[: max(remaining - 1, 0)]}…"
    return f"{prefix}{base or pergunta.texto or pergunta.id}"


def _render_conteudo(pergunta: Pergunta, resposta: Resposta) -> str:
    pergunta_html = pergunta.texto or ""
    resposta_html = resposta.conteudo_html or "<p>(sem resposta)</p>"
    return (
        f'<section data-pergunta-id="{pergunta.id}" class="collab-pergunta-bloco">'
        f'<header><p><strong>Pergunta {pergunta.ordem}</strong></p></header>'
        f'<div class="collab-pergunta-texto" data-origem="pergunta">{pergunta_html}</div>'
        f'<div class="collab-resposta-texto" data-origem="resposta">{resposta_html}</div>'
        "</section>"
    )


def broadcast_texto_colaborativo(instance: TextoColaborativo, *, created: bool) -> None:
    """Dispara eventos de streaming para manter a UI em tempo real."""
    event = "collab_text:created" if created else "collab_text:updated"
    payload = {
        "id": instance.id,
        "gt": instance.gt_id,
        "pergunta": instance.pergunta_id,
        "titulo": instance.titulo,
        "conteudo_html": instance.conteudo_html,
        "version": instance.version,
        "autor": instance.autor_id,
        "created_at": instance.created_at.isoformat(),
        "updated_at": instance.updated_at.isoformat(),
        "etag": instance.etag,
    }
    broadcast_stream_event("texto_colaborativo", instance.id, "collab_text:updated", payload)
    broadcast_stream_event("texto_colaborativo_list", instance.gt_id, event, payload)


def sync_texto_colaborativo_from_resposta(resposta: Resposta) -> Tuple[TextoColaborativo, bool]:
    """Garante que a resposta também esteja refletida em um texto colaborativo vinculado à pergunta."""
    pergunta = resposta.pergunta
    titulo = _normalize_title(pergunta)
    conteudo_html = _render_conteudo(pergunta, resposta)
    defaults = {
        "titulo": titulo,
        "conteudo_html": conteudo_html,
        "autor_id": resposta.autor_id,
    }
    texto, created = TextoColaborativo.objects.get_or_create(
        cliente_id=resposta.cliente_id,
        gt_id=resposta.gt_id,
        pergunta=pergunta,
        defaults=defaults,
    )
    if not created:
        texto.titulo = titulo
        texto.conteudo_html = conteudo_html
        texto.autor_id = resposta.autor_id
        texto.save(update_fields=["titulo", "conteudo_html", "autor", "updated_at", "version"])
    return texto, created
