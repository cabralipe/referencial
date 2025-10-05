"""Tarefas auxiliares para geração de diff."""

from __future__ import annotations

from django.core.cache import cache

from celery import shared_task

from diffs.services import build_diff

CACHE_TTL = 60 * 60  # 1h


@shared_task(name="tasks.diffs.render_and_cache_diff")
def render_and_cache_diff(alvo_tipo: str, alvo_id: int | str, from_version: int, to_version: int) -> str:
    key = f"diff:{alvo_tipo}:{alvo_id}:{from_version}:{to_version}"
    cached = cache.get(key)
    if cached:
        return cached

    html = build_diff(alvo_tipo, alvo_id, from_version, to_version)

    cache.set(key, html, CACHE_TTL)
    return html
