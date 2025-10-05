"""Utilidades para broadcast em canais."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_stream_event(alvo_tipo: str, alvo_id: str | int, event: str, payload: dict) -> None:
    layer = get_channel_layer()
    if not layer:
        return
    try:
        async_to_sync(layer.group_send)(
            f"stream.{alvo_tipo}.{alvo_id}",
            {
                "type": "broadcast",
                "payload": {"event": event, **payload},
            },
        )
    except Exception:  # pragma: no cover - quando não há broker disponível
        pass
