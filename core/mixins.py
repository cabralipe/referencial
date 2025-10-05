"""Mixins e managers para lidar com multi-cliente e soft delete."""

from __future__ import annotations

from typing import Optional, Union

from django.db import models

from .threadlocals import get_current_cliente_id


class ClientScopedManager(models.Manager):
    """Manager que aplica automaticamente escopo por cliente e soft delete."""

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        if hasattr(self.model, "is_deleted"):
            qs = qs.filter(is_deleted=False)
        if self._has_cliente_field():
            cliente_id = get_current_cliente_id()
            if cliente_id is not None:
                qs = qs.filter(cliente_id=cliente_id)
        return qs

    def with_deleted(self):
        qs = super().get_queryset()
        if self._has_cliente_field():
            cliente_id = get_current_cliente_id()
            if cliente_id is not None:
                qs = qs.filter(cliente_id=cliente_id)
        return qs

    def for_cliente(self, cliente: Union[int, models.Model]):
        cliente_id = cliente.id if hasattr(cliente, "id") else int(cliente)
        return self.with_deleted().filter(cliente_id=cliente_id)

    def create(self, **kwargs):  # type: ignore[override]
        if self._has_cliente_field() and not kwargs.get("cliente") and not kwargs.get("cliente_id"):
            current = get_current_cliente_id()
            if current is not None:
                kwargs["cliente_id"] = current
        return super().create(**kwargs)

    def _has_cliente_field(self) -> bool:
        return any(field.attname == "cliente_id" for field in self.model._meta.fields)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self, using: Optional[str] = None, keep_parents: bool = False):  # type: ignore[override]
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])


class TenantModel(SoftDeleteModel):
    cliente = models.ForeignKey(
        "core.Cliente",
        on_delete=models.PROTECT,
        related_name="%(class)ss",
    )

    objects = ClientScopedManager()
    raw_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.cliente_id:
            current = get_current_cliente_id()
            if current is not None:
                self.cliente_id = current
        super().save(*args, **kwargs)
