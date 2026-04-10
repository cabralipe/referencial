"""Middleware que aplica escopo de cliente em cada requisição."""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from .activity import touch_user_session
from .scope import resolve_cliente_scope
from .threadlocals import set_current_cliente_id, set_current_usuario_id


class ClienteScopeMiddleware:
    """Define o cliente ativo baseado no usuário autenticado."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        set_current_cliente_id(None)
        set_current_usuario_id(None)

        cliente_id = None
        if request.user.is_authenticated:
            cliente_id = resolve_cliente_scope(request)
            set_current_usuario_id(request.user.id)

        set_current_cliente_id(cliente_id)
        request.cliente_id = cliente_id
        if request.user.is_authenticated:
            touch_user_session(request)

        response = self.get_response(request)

        set_current_cliente_id(None)
        set_current_usuario_id(None)
        return response
