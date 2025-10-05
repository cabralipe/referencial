"""Serviços utilitários para gerar DOCX."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict

from django.utils.html import strip_tags

try:
    from docx import Document
except ImportError:  # pragma: no cover - dependencia externa
    Document = None  # type: ignore


def html_to_docx_bytes(context: Dict[str, Any]) -> bytes:
    if Document is None:
        raise RuntimeError("python-docx não está disponível no ambiente")

    document = Document()
    titulo = context.get("titulo") or "Exportação"
    document.add_heading(titulo, level=1)

    conteudo = context.get("conteudo_html", "")
    for linha in str(conteudo).splitlines():
        texto = strip_tags(linha).strip()
        if texto:
            document.add_paragraph(texto)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.read()
