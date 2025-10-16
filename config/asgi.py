"""ASGI config for referencial project."""

import os

from core.websocket_auth import SessionAuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

try:
    from sockets.routing import websocket_urlpatterns
except Exception:  # pragma: no cover - sockets app might not be ready in migrations
    websocket_urlpatterns = []

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": SessionAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
