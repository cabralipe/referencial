"""Registra auditoria simples para modelos multi-cliente."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from .mixins import TenantModel
from .models import AuditLog
from .threadlocals import get_current_usuario_id


def _snapshot(instance: TenantModel) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in instance._meta.fields:
        if field.name in {"id", "created_at", "updated_at"}:
            continue
        value = getattr(instance, field.name)
        if isinstance(value, (datetime, date, time)):
            value = value.isoformat()
        if field.many_to_one or field.one_to_one:
            data[field.name] = getattr(instance, f"{field.name}_id")
        else:
            data[field.name] = value
    return data


@receiver(post_save)
def registrar_auditoria(sender, instance, created, **kwargs):
    if sender is AuditLog:
        return
    if not isinstance(instance, TenantModel):
        return

    acao = "created" if created else "updated"
    AuditLog.raw_objects.create(
        cliente=instance.cliente,
        usuario_id=get_current_usuario_id(),
        entidade=f"{sender._meta.app_label}.{sender.__name__}",
        entidade_id=str(instance.pk),
        acao=acao,
        diff_json={"current": _snapshot(instance)},
    )
