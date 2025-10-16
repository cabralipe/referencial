"""Custom WebSocket authentication middleware for Django Channels."""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_session(session_key):
    """Get user from session key."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    
    try:
        User = get_user_model()
        session = Session.objects.get(session_key=session_key, expire_date__gte=timezone.now())
        user_id = session.get_decoded().get('_auth_user_id')
        if user_id:
            return User.objects.get(pk=user_id)
    except (Session.DoesNotExist, User.DoesNotExist):
        pass
    return AnonymousUser()


class SessionAuthMiddleware(BaseMiddleware):
    """Custom middleware to authenticate WebSocket connections using session."""
    
    async def __call__(self, scope, receive, send):
        # Only handle WebSocket connections
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)
        
        # Try to get session key from query parameters
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        
        session_key = None
        if "sessionid" in query_params:
            session_key = query_params["sessionid"][0]
        
        # If no session key in query params, try to get from cookies
        if not session_key:
            cookies = {}
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"cookie":
                    cookie_header = header_value.decode()
                    for cookie in cookie_header.split(";"):
                        if "=" in cookie:
                            key, value = cookie.strip().split("=", 1)
                            cookies[key] = value
            session_key = cookies.get("sessionid")
        
        # Get user from session
        if session_key:
            scope["user"] = await get_user_from_session(session_key)
            logger.info(f"WebSocket authentication: session_key={session_key}, user={scope['user']}")
        else:
            from django.contrib.auth.models import AnonymousUser
            scope["user"] = AnonymousUser()
            logger.warning("WebSocket authentication: no session key found")
        
        return await super().__call__(scope, receive, send)


def SessionAuthMiddlewareStack(inner):
    """Custom middleware stack with session authentication."""
    return SessionAuthMiddleware(AuthMiddlewareStack(inner))