"""Plugin de hooks padrão."""

from __future__ import annotations

from typing import Dict


def dispatch(event_name: str, payload: Dict[str, object]) -> None:
    """Plugin padrão apenas registra o disparo (placeholder)."""
    # Este plugin é intencionalmente simples; em produção integrar sistemas externos.
    return None
