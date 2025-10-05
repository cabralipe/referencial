"""Serviços utilitários para gerar PDFs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML


def html_to_pdf_bytes(template_name: str, context: Dict[str, Any]) -> bytes:
    html = render_to_string(template_name, context)
    base_url = str(Path(settings.BASE_DIR))
    return HTML(string=html, base_url=base_url).write_pdf()
