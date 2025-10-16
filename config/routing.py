from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from core.websocket_auth import SessionAuthMiddlewareStack

from sockets.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "websocket": SessionAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
