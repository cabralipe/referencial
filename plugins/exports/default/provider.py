"""Plugin de exportação padrão."""

from __future__ import annotations

from typing import Any, Dict

from exports.services.docx import html_to_docx_bytes
from exports.services.pdf import html_to_pdf_bytes


def _default_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    tema = ctx.get("cliente", {}).get("tema", {})
    return {
        "titulo": ctx.get("titulo", "Exportação"),
        "conteudo_html": ctx.get("conteudo_html", ""),
        "tema": tema,
    }


def render_pdf(ctx: Dict[str, Any]) -> bytes:
    context = _default_context(ctx)
    return html_to_pdf_bytes("exports/pdf/base.html", context)


def render_docx(ctx: Dict[str, Any]) -> bytes:
    context = _default_context(ctx)
    return html_to_docx_bytes(context)
