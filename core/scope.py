"""Helpers para resolver o cliente ativo da requisição."""

from __future__ import annotations


def _parse_cliente_id(raw_value) -> int | None:
    if raw_value in {None, ""}:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def resolve_cliente_scope(request) -> int | None:
    """Resolve e persiste o cliente ativo considerando header e permissões do usuário."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None

    requested_cliente_id = _parse_cliente_id(request.headers.get("X-Cliente-ID"))
    current_cliente_id = _parse_cliente_id(getattr(request, "cliente_id", None))
    user_cliente_id = _parse_cliente_id(getattr(user, "cliente_id", None))

    cliente_id = current_cliente_id
    if requested_cliente_id and user.can_access_cliente(requested_cliente_id):
        cliente_id = requested_cliente_id

    if cliente_id is None and user_cliente_id and user.can_access_cliente(user_cliente_id):
        cliente_id = user_cliente_id

    if cliente_id is None and getattr(user, "role", None) != user.Role.SUPER_ADMIN:
        cliente_id = user.get_default_cliente_id()

    if (
        cliente_id is not None
        and getattr(user, "role", None) != user.Role.SUPER_ADMIN
        and not user.can_access_cliente(cliente_id)
    ):
        cliente_id = user.get_default_cliente_id()

    request.cliente_id = cliente_id
    # Compatibilidade com trechos legados que leem request.user.cliente_id.
    user.cliente_id = cliente_id
    return cliente_id
