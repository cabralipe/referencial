"""Armazena escopo de cliente e usuário para filtros automáticos."""

from contextlib import contextmanager

from contextvars import ContextVar
from typing import Optional

_cliente_id_var: ContextVar[Optional[int]] = ContextVar("cliente_id", default=None)
_usuario_id_var: ContextVar[Optional[int]] = ContextVar("usuario_id", default=None)


def set_current_cliente_id(cliente_id: Optional[int]) -> None:
    _cliente_id_var.set(cliente_id)


def get_current_cliente_id() -> Optional[int]:
    return _cliente_id_var.get()


@contextmanager
def cliente_scope(cliente_id: Optional[int]):
    """Troca temporariamente o escopo, restaurando-o mesmo em caso de erro."""
    previous = get_current_cliente_id()
    set_current_cliente_id(cliente_id)
    try:
        yield
    finally:
        set_current_cliente_id(previous)


def set_current_usuario_id(usuario_id: Optional[int]) -> None:
    _usuario_id_var.set(usuario_id)


def get_current_usuario_id() -> Optional[int]:
    return _usuario_id_var.get()
