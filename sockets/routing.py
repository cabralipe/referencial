"""Rotas de WebSocket."""

from __future__ import annotations

from django.urls import re_path

from .consumers import PresenceConsumer

websocket_urlpatterns = [
    re_path(r"^ws/presence/(?P<doc_type>[^/]+)/(?P<object_id>[^/]+)/$", PresenceConsumer.as_asgi()),
]
