"""Utilidades para registrar sessões e atividade online dos usuários."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.utils import timezone

from .models import UserSessionLog

# Janela usada para considerar um usuário online.
ONLINE_WINDOW = timedelta(minutes=5)
# Intervalo mínimo entre atualizações de last_seen para evitar escrita excessiva.
UPDATE_INTERVAL = timedelta(seconds=60)


def touch_user_session(request) -> Optional[UserSessionLog]:
    """Cria ou atualiza o registro de sessão do usuário autenticado."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None

    session = getattr(request, "session", None)
    if session is None:
        return None

    if not session.session_key:
        session.save()
    session_key = session.session_key
    if not session_key:
        return None

    cliente_id = getattr(request, "cliente_id", None) or getattr(user, "cliente_id", None)
    now = timezone.now()

    existing = (
        UserSessionLog.objects.filter(session_key=session_key)
        .only("id", "last_seen_at")
        .first()
    )
    if existing:
        if existing.last_seen_at >= now - UPDATE_INTERVAL:
            return existing
        ua = request.META.get("HTTP_USER_AGENT", "")
        existing.last_seen_at = now
        existing.usuario = user
        existing.cliente_id = cliente_id
        if ua and (not existing.user_agent or existing.user_agent != ua):
            existing.user_agent = ua
            # Heurística simples de dispositivo
            existing.device = (
                "mobile" if "Mobi" in ua else "tablet" if "Tablet" in ua else "desktop"
            )
            existing.save(update_fields=["last_seen_at", "usuario", "cliente_id", "user_agent", "device", "updated_at"])
        else:
            existing.save(update_fields=["last_seen_at", "usuario", "cliente_id", "updated_at"])
        return existing

    ua = request.META.get("HTTP_USER_AGENT", "")
    return UserSessionLog.objects.create(
        session_key=session_key,
        usuario=user,
        cliente_id=cliente_id,
        first_seen_at=now,
        last_seen_at=now,
        user_agent=ua,
        device=("mobile" if "Mobi" in ua else "tablet" if "Tablet" in ua else "desktop") if ua else "",
    )


def online_sessions_for_cliente(cliente_id: Optional[int]):
    """Retorna queryset das sessões consideradas online para o cliente informado."""
    cutoff = timezone.now() - ONLINE_WINDOW
    qs = UserSessionLog.objects.filter(last_seen_at__gte=cutoff)
    if cliente_id is not None:
        qs = qs.filter(cliente_id=cliente_id)
    return qs.select_related("usuario", "cliente")
