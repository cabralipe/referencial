"""Plugin de síntese padrão."""

from __future__ import annotations

from typing import Dict


def preprocess(ctx: Dict[str, object]) -> Dict[str, object]:
    """Normaliza respostas removendo espaços extras."""
    respostas = ctx.get("respostas", {})
    for resposta in respostas.values():
        conteudo = getattr(resposta, "conteudo_html", None)
        if isinstance(conteudo, str):
            resposta.conteudo_html = conteudo.strip()
    return ctx


def postprocess(ctx: Dict[str, object]) -> Dict[str, object]:
    """Garante que o HTML final possua container raiz."""
    conteudo = ctx.get("conteudo_html", "")
    if isinstance(conteudo, str) and not conteudo.startswith("<section"):
        ctx["conteudo_html"] = f"<section class='texto-unico'>{conteudo}</section>"
    return ctx
