"""Regras de throttling customizadas."""

from __future__ import annotations

from rest_framework.throttling import ScopedRateThrottle


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
