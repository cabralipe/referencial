"""Serviços utilitários para comparação de HTML."""

from __future__ import annotations

import difflib
from typing import Iterable

from core.models import AuditLog
from curriculum.models import Resposta, TextoUnico


def _normalize_html(html: str) -> Iterable[str]:
    return [line.strip() for line in html.splitlines()]


def diff_html(old_html: str, new_html: str) -> str:
    """Retorna diff simples usando tags <ins>/<del>."""
    old_lines = _normalize_html(old_html or "")
    new_lines = _normalize_html(new_html or "")
    diff = difflib.ndiff(old_lines, new_lines)

    chunks: list[str] = ["<div class=\"diff\">"]
    for part in diff:
        marker, content = part[:2], part[2:]
        if marker == "- ":
            chunks.append(f"<del>{content}</del>")
        elif marker == "+ ":
            chunks.append(f"<ins>{content}</ins>")
        elif marker == "  ":
            chunks.append(f"<span>{content}</span>")
    chunks.append("</div>")
    return "\n".join(chunks)


def build_diff(alvo_tipo: str, alvo_id: int | str, from_version: int, to_version: int) -> str:
    if alvo_tipo == "resposta":
        alvo = Resposta.objects.filter(pk=alvo_id).first()
        if not alvo:
            return ""
        antigo = _buscar_snapshot("curriculum.Resposta", alvo_id, from_version)
        novo = _buscar_snapshot("curriculum.Resposta", alvo_id, to_version) or alvo.conteudo_html
    elif alvo_tipo == "texto_unico":
        alvo = TextoUnico.objects.filter(pk=alvo_id).first()
        if not alvo:
            return ""
        antigo = _buscar_snapshot("curriculum.TextoUnico", alvo_id, from_version)
        novo = _buscar_snapshot("curriculum.TextoUnico", alvo_id, to_version) or alvo.conteudo_html
    else:
        return ""
    return diff_html(antigo or "", novo or "")


def _buscar_snapshot(entidade: str, objeto_id: int | str, version: int) -> str | None:
    registro = (
        AuditLog.objects.filter(entidade=entidade, entidade_id=str(objeto_id))
        .order_by("-timestamp")
        .filter(diff_json__current__version=version)
        .first()
    )
    if not registro:
        return None
    return registro.diff_json.get("current", {}).get("conteudo_html")
