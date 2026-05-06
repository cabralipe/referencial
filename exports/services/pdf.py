"""Serviços utilitários para gerar PDFs."""

from __future__ import annotations

from pathlib import Path
import logging
from typing import Any, Dict

from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False


def html_to_pdf_bytes(template_name: str, context: Dict[str, Any]) -> bytes:
    html = render_to_string(template_name, context)
    base_url = str(Path(settings.BASE_DIR))

    if WEASYPRINT_AVAILABLE:
        return HTML(string=html, base_url=base_url).write_pdf()

    # Fallback: gera um PDF "falso" válido para não travar o fluxo.
    logger.warning("WeasyPrint indisponível (GTK3 ausente). Gerando PDF simulado.")
    
    # PDF mínimo válido (v1.4)
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 500 150] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 107 >>\nstream\n"
        b"BT /F1 16 Tf 50 100 Td (PREVIEW MODE - GTK3 MISSING) Tj 0 -25 Td (Instale GTK3 ou use Docker para ver o PDF real.) Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000111 00000 n \n0000000288 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n443\n%%EOF"
    )
