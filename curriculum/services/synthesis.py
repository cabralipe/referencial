"""Serviços para sintetizar o Texto Único."""

from __future__ import annotations

from typing import Dict, List

from django.db import transaction
from django.utils.html import escape

from core.plugins import get_synthesis_provider
from core.utils import coletar_contexto_do_cliente, obter_config

from ..models import Pergunta, Resposta, TextoUnico


def gerar_texto_unico(texto_unico: TextoUnico) -> TextoUnico:
    """Constrói o Texto Único a partir das respostas do GT."""

    cliente = texto_unico.cliente
    perguntas = list(Pergunta.objects.filter(tarefa=texto_unico.tarefa).order_by("ordem"))
    respostas = {
        resposta.pergunta_id: resposta
        for resposta in Resposta.objects.filter(gt=texto_unico.gt, pergunta__in=perguntas)
    }

    ctx: Dict[str, object] = {
        "cliente": coletar_contexto_do_cliente(cliente),
        "texto_unico": texto_unico,
        "perguntas": perguntas,
        "respostas": respostas,
    }

    plugin_name = obter_config(cliente, "synthesis_plugin")
    provider = get_synthesis_provider(plugin_name)
    if hasattr(provider, "preprocess"):
        ctx = provider.preprocess(ctx)  # type: ignore[assignment]

    html_fragmentos: List[str] = []
    for pergunta in perguntas:
        html_fragmentos.append(f"<h3>{escape(pergunta.texto)}</h3>")
        resposta = respostas.get(pergunta.id)
        if resposta and resposta.conteudo_html:
            html_fragmentos.append(resposta.conteudo_html)
        else:
            html_fragmentos.append("<p><em>Sem resposta registrada.</em></p>")
        if resposta:
            anexos = resposta.anexos.order_by("ordem")
            if anexos.exists():
                html_fragmentos.append("<ul class=\"anexos\">")
                for anexo in anexos:
                    legenda = escape(anexo.legenda) if anexo.legenda else "Anexo"
                    html_fragmentos.append(
                        f"<li><a href=\"{anexo.url}\" target=\"_blank\">{legenda}</a></li>"
                    )
                html_fragmentos.append("</ul>")

    ctx["conteudo_html"] = "\n".join(html_fragmentos)

    if hasattr(provider, "postprocess"):
        ctx = provider.postprocess(ctx)  # type: ignore[assignment]

    texto_unico.conteudo_html = ctx["conteudo_html"]  # type: ignore[assignment]
    with transaction.atomic():
        texto_unico.save()
    return texto_unico
