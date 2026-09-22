"""Auditoria das alterações do Diário de Bordo e das planilhas configuráveis."""

from __future__ import annotations

from typing import Any

from core.models import AuditLog


class AVAAuditService:
    """Grava entradas em :class:`core.models.AuditLog`.

    A auditoria nunca deve derrubar a operação de negócio, por isso os erros
    de gravação são silenciados — o registro principal já está persistido.
    """

    @staticmethod
    def registrar(
        *,
        cliente_id: int,
        usuario,
        entidade: str,
        entidade_id: Any,
        acao: str,
        diff: dict | None = None,
    ) -> AuditLog | None:
        if not cliente_id:
            return None
        try:
            return AuditLog.objects.create(
                cliente_id=cliente_id,
                usuario_id=getattr(usuario, "id", None),
                entidade=entidade,
                entidade_id=str(entidade_id),
                acao=acao,
                diff_json=diff or {},
            )
        except Exception:  # pragma: no cover - auditoria é best-effort
            return None

    @classmethod
    def registrar_diario(cls, diario, usuario, acao: str, diff: dict | None = None):
        return cls.registrar(
            cliente_id=diario.cliente_id,
            usuario=usuario,
            entidade="ava.DiarioBordo",
            entidade_id=diario.pk,
            acao=acao,
            diff=diff,
        )

    @classmethod
    def registrar_planilha(cls, objeto, usuario, acao: str, diff: dict | None = None):
        return cls.registrar(
            cliente_id=objeto.cliente_id,
            usuario=usuario,
            entidade=f"ava.{objeto.__class__.__name__}",
            entidade_id=objeto.pk,
            acao=acao,
            diff=diff,
        )


def diff_de_campos(instancia, campos: list[str]) -> dict[str, Any]:
    """Serializa os campos indicados para guardar no ``diff_json``."""

    resultado: dict[str, Any] = {}
    for campo in campos:
        valor = getattr(instancia, campo, None)
        if hasattr(valor, "isoformat"):
            valor = valor.isoformat()
        elif valor is not None and not isinstance(valor, (str, int, float, bool)):
            valor = str(valor)
        resultado[campo] = valor
    return resultado
