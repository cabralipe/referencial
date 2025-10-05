"""Tarefas Celery para síntese do Texto Único."""

from __future__ import annotations

from celery import shared_task

from curriculum.models import TextoUnico
from curriculum.services.synthesis import gerar_texto_unico


def enqueue_texto_unico(texto_unico_id: int) -> None:
    generate_texto_unico.delay(texto_unico_id)


@shared_task(name="tasks.synthesis.generate_texto_unico")
def generate_texto_unico(texto_unico_id: int) -> int:
    texto = TextoUnico.objects.get(pk=texto_unico_id)
    gerar_texto_unico(texto)
    return texto.id
