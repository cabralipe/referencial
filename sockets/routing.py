"""Rotas de WebSocket."""

from __future__ import annotations

from django.urls import re_path

from .consumers import NotificationConsumer, PresenceConsumer, StreamConsumer

websocket_urlpatterns = [
    re_path(r"^ws/presence/(?P<doc_type>[^/]+)/(?P<object_id>[^/]+)/?$", PresenceConsumer.as_asgi()),
    re_path(r"^ws/stream/(?P<alvo_tipo>[^/]+)/(?P<alvo_id>[^/]+)/?$", StreamConsumer.as_asgi()),
    re_path(r"^ws/notifications/?$", NotificationConsumer.as_asgi()),
]
