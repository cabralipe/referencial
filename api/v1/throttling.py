"""Regras de throttling customizadas."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

from core.models import ThrottleBlock


class ClientScopedRateThrottle(ScopedRateThrottle):
    scope = "client"

    def get_cache_key(self, request, view):  # pragma: no cover - DRF internals
        if not request.user or not request.user.is_authenticated:
            return super().get_cache_key(request, view)
        ident = f"cliente-{getattr(request.user, 'cliente_id', 'anon')}"
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


def _register_throttle_block(throttle, request):
    if not request:
        return
    cache_key = getattr(throttle, "key", None)
    scope = getattr(throttle, "scope", None) or "unknown"
    wait = throttle.wait() or 0
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    cliente_id = getattr(request, "cliente_id", None) or getattr(user, "cliente_id", None)
    blocked_until = timezone.now() + timedelta(seconds=int(wait)) if wait else None
    ident = ""
    if cache_key and scope:
        prefix = f"throttle_{scope}_"
        if cache_key.startswith(prefix):
            ident = cache_key[len(prefix):]
    if not ident:
        if user:
            ident = str(user.pk)
        else:
            ident = throttle.get_ident(request)
    if not cache_key:
        cache_key = throttle.cache_format % {"scope": scope, "ident": ident}
    ThrottleBlock.objects.update_or_create(
        cache_key=cache_key,
        defaults={
            "cliente_id": cliente_id,
            "usuario": user,
            "scope": scope,
            "ident": str(ident),
            "wait_seconds": int(wait),
            "blocked_until": blocked_until,
        },
    )


class LoggingUserRateThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        self._request = request
        return super().allow_request(request, view)

    def throttle_failure(self):
        _register_throttle_block(self, getattr(self, "_request", None))
        return False


class LoggingAnonRateThrottle(AnonRateThrottle):
    def allow_request(self, request, view):
        self._request = request
        return super().allow_request(request, view)

    def throttle_failure(self):
        _register_throttle_block(self, getattr(self, "_request", None))
        return False


class LoggingScopedRateThrottle(ScopedRateThrottle):
    def allow_request(self, request, view):
        self._request = request
        return super().allow_request(request, view)

    def throttle_failure(self):
        _register_throttle_block(self, getattr(self, "_request", None))
        return False
