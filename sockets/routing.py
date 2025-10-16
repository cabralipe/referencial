"""Rotas de WebSocket."""

from __future__ import annotations

from django.urls import re_path

from .consumers import NotificationConsumer, PresenceConsumer, StreamConsumer

# Import media library consumers
try:
    from library.consumers import MediaLibraryConsumer, MediaFileConsumer
    media_consumers_available = True
except ImportError:
    media_consumers_available = False

websocket_urlpatterns = [
    re_path(r"^ws/presence/(?P<doc_type>[^/]+)/(?P<object_id>[^/]+)/$", PresenceConsumer.as_asgi()),
    re_path(r"^ws/stream/(?P<alvo_tipo>[^/]+)/(?P<alvo_id>[^/]+)/$", StreamConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]

# Add media library WebSocket routes if available
if media_consumers_available:
    websocket_urlpatterns.extend([
        re_path(r"^ws/media-library/$", MediaLibraryConsumer.as_asgi()),
        re_path(r"^ws/media-file/(?P<file_id>[^/]+)/$", MediaFileConsumer.as_asgi()),
    ])
