"""Serviços utilitários para criação e broadcast de notificações."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from core.models import Cliente
from core.utils import flag_ativa
from notifications.models import Notificacao
from tasks.notifications import send_email_notification


def criar_notificacao(*, cliente_id: int, usuario_id: int, tipo: str, payload: dict) -> Notificacao | None:
    cliente = Cliente.objects.filter(pk=cliente_id).first()
    if not cliente or not flag_ativa(cliente, "ff.notifications.enabled"):
        return None

    with transaction.atomic():
        notificacao = Notificacao.objects.create(
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            tipo=tipo,
            payload_json=payload,
        )
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"user.{usuario_id}",
                {"type": "deliver", "payload": {"event": "notification:new", "id": notificacao.id, "tipo": tipo, "payload": payload}},
            )
        except Exception:  # pragma: no cover - fallback quando Channels indisponível
            pass
    try:
        send_email_notification.delay(notificacao.id)
    except Exception:  # pragma: no cover - fallback quando Celery indisponível
        send_email_notification(notificacao.id)
    return notificacao
