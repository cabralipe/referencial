"""Registra auditoria simples para modelos multi-cliente."""

from __future__ import annotations

import json
from decimal import Decimal
from datetime import date, datetime, time
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.fields.files import FieldFile

from .mixins import TenantModel
from .models import AuditLog, Cliente, ClienteFeatureFlag
from .threadlocals import get_current_usuario_id


def _json_compatible(value: Any) -> Any:
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_compatible(item) for item in value]

    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _snapshot(instance: TenantModel) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in instance._meta.fields:
        if field.name in {"id", "created_at", "updated_at"}:
            continue
        value = getattr(instance, field.name)
        if field.many_to_one or field.one_to_one:
            value = getattr(instance, f"{field.name}_id")
        data[field.name] = _json_compatible(value)
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


@receiver(post_save, sender=Cliente)
def garantir_flags_padrao(sender, instance, created, **kwargs):
    if not created:
        return
    flags = [
        "ff.reviews.enabled",
        "ff.comments.enabled",
        "ff.notifications.enabled",
        "ff.diff.enabled",
        "ff.library.enabled",
    ]
    for flag in flags:
        ClienteFeatureFlag.objects.update_or_create(
            cliente=instance,
            flag=flag,
            defaults={"ativo": True},
        )
