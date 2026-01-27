from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def serve_frontend(_request, *args, **kwargs):
    """Serves the compiled frontend index file or a helpful placeholder."""

    index_path = Path(settings.BASE_DIR) / "static" / "frontend" / "index.html"
    if not index_path.exists():
        message = (
            "<h1>Frontend não compilado</h1>"
            "<p>Execute <code>npm install</code> e <code>npm run build</code> dentro do diretório <code>frontend/</code>."
            " Em seguida, recarregue a página.</p>"
        )
        response = HttpResponse(message, content_type="text/html", status=503)
        response["Cache-Control"] = "no-store"
        return response

    content = index_path.read_text(encoding="utf-8")
    response = HttpResponse(content, content_type="text/html")
    response["Cache-Control"] = "no-store"
    return response
