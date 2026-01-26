"""Serviços para diffs de texto entre versões."""

from __future__ import annotations

import difflib

from core.models import AuditLog
from reviews.models import Revisao
from curriculum.models import Resposta, TextoUnico


def render_diff(old_html: str, new_html: str) -> str:
    old_lines = (old_html or "").splitlines()
    new_lines = (new_html or "").splitlines()
    diff = difflib.ndiff(old_lines, new_lines)
    parts: list[str] = ["<div class=\"diff\">"]
    for line in diff:
        prefix = line[:2]
        content = line[2:]
        if prefix == "- ":
            parts.append(f"<del>{content}</del>")
        elif prefix == "+ ":
            parts.append(f"<ins>{content}</ins>")
        elif prefix == "  ":
            parts.append(f"<span>{content}</span>")
    parts.append("</div>")
    return "\n".join(parts)


def _latest_snapshot_before(entidade: str, entidade_id: str, timestamp) -> str | None:
    log = (
        AuditLog.objects.filter(entidade=entidade, entidade_id=str(entidade_id), timestamp__lte=timestamp)
        .order_by("-timestamp")
        .first()
    )
    if not log:
        return None
    return log.diff_json.get("current", {}).get("conteudo_html")


def diff_last_approved(alvo_tipo: str, alvo_id: str | int) -> str:
    alvo_id_str = str(alvo_id)
    if alvo_tipo == "resposta":
        alvo = Resposta.objects.filter(pk=alvo_id).first()
        entidade = "curriculum.Resposta"
    elif alvo_tipo == "texto_unico":
        alvo = TextoUnico.objects.filter(pk=alvo_id).first()
        entidade = "curriculum.TextoUnico"
    else:
        return ""
    if not alvo:
        return ""

    revisao = (
        Revisao.objects.filter(alvo_tipo=alvo_tipo, alvo_id=alvo_id_str, status=Revisao.Status.APROVADO)
        .order_by("-updated_at")
        .first()
    )
    old_html = ""
    if revisao:
        snapshot = _latest_snapshot_before(entidade, alvo_id_str, revisao.updated_at)
        old_html = snapshot or ""
    new_html = alvo.conteudo_html or ""
    return render_diff(old_html, new_html)
