"""Middleware que aplica escopo de cliente em cada requisição."""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from .threadlocals import set_current_cliente_id, set_current_usuario_id


class ClienteScopeMiddleware:
    """Define o cliente ativo baseado no usuário autenticado."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        from .models import Usuario  # import tardio para evitar loop

        set_current_cliente_id(None)
        set_current_usuario_id(None)

        cliente_id = None
        if request.user.is_authenticated:
            cliente_id = getattr(request.user, "cliente_id", None)
            requested_scope = request.headers.get("X-Cliente-ID")
            if (
                requested_scope
                and getattr(request.user, "role", None) == Usuario.Role.SUPER_ADMIN
            ):
                try:
                    cliente_id = int(requested_scope)
                except (TypeError, ValueError):
                    cliente_id = getattr(request.user, "cliente_id", None)

            set_current_usuario_id(request.user.id)

        set_current_cliente_id(cliente_id)
        request.cliente_id = cliente_id

        response = self.get_response(request)

        set_current_cliente_id(None)
        set_current_usuario_id(None)
        return response
