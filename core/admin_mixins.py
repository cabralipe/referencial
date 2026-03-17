"""Mixins reutilizáveis para escopo de cliente no Django Admin."""

from __future__ import annotations

from django.contrib import admin


def _model_has_field(model, field_name: str) -> bool:
    return any(field.name == field_name or field.attname == field_name for field in model._meta.fields)


def _model_has_soft_delete(model) -> bool:
    return _model_has_field(model, "is_deleted")


class ClienteScopedAdminMixin:
    """Restringe listagens, permissões e relações ao cliente do usuário logado."""

    cliente_scope_lookup: str | None = None

    def _is_super_admin(self, request) -> bool:
        return bool(getattr(request.user, "is_superuser", False)) or getattr(request.user, "role", None) == "super_admin"

    def _get_scope_lookup(self, model=None) -> str | None:
        model = model or self.model
        if model._meta.label_lower == "core.cliente":
            return "pk"
        if model is self.model and self.cliente_scope_lookup:
            return self.cliente_scope_lookup
        if _model_has_field(model, "cliente_id"):
            return "cliente_id"
        return None

    def _filter_queryset_for_cliente(self, request, queryset, model=None):
        if self._is_super_admin(request):
            return queryset

        lookup = self._get_scope_lookup(model)
        if not lookup:
            return queryset

        cliente_id = getattr(request.user, "cliente_id", None)
        if cliente_id is None:
            return queryset.none()
        return queryset.filter(**{lookup: cliente_id})

    def _belongs_to_cliente(self, request, obj) -> bool:
        if obj is None or self._is_super_admin(request):
            return True

        lookup = self._get_scope_lookup(obj.__class__)
        if lookup is None:
            return True

        if lookup == "pk":
            obj_cliente_id = obj.pk
        else:
            obj_cliente_id = getattr(obj, lookup, None)
        return obj_cliente_id == getattr(request.user, "cliente_id", None)

    def _strip_cliente_from_fields(self, fields):
        cleaned = []
        for field in fields:
            if field == "cliente":
                continue
            if isinstance(field, (list, tuple)):
                nested = tuple(item for item in field if item != "cliente")
                if nested:
                    cleaned.append(nested)
                continue
            cleaned.append(field)
        return tuple(cleaned)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return self._filter_queryset_for_cliente(request, queryset)

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if self._is_super_admin(request):
            return list_filter

        filtered = []
        for item in list_filter:
            field_name = item[0] if isinstance(item, tuple) else item
            if field_name == "cliente":
                continue
            filtered.append(item)
        return filtered

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not self._is_super_admin(request) and _model_has_field(self.model, "cliente") and "cliente" not in exclude:
            exclude.append("cliente")
        return exclude

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if self._is_super_admin(request):
            return fields
        return self._strip_cliente_from_fields(fields)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if self._is_super_admin(request):
            return fieldsets

        cleaned_fieldsets = []
        for name, options in fieldsets:
            fieldset_options = dict(options)
            fields = fieldset_options.get("fields")
            if fields:
                fieldset_options["fields"] = self._strip_cliente_from_fields(fields)
            cleaned_fieldsets.append((name, fieldset_options))
        return cleaned_fieldsets

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._belongs_to_cliente(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._belongs_to_cliente(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._belongs_to_cliente(request, obj)

    def save_model(self, request, obj, form, change):
        if not self._is_super_admin(request) and hasattr(obj, "cliente_id"):
            obj.cliente_id = getattr(request.user, "cliente_id", None)
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not self._is_super_admin(request):
            related_model = getattr(db_field.remote_field, "model", None)
            if db_field.name == "cliente" and related_model is not None:
                kwargs["queryset"] = related_model._default_manager.filter(pk=getattr(request.user, "cliente_id", None))
            elif related_model is not None and self._get_scope_lookup(related_model):
                manager = getattr(related_model, "raw_objects", related_model._default_manager)
                related_qs = manager.all()
                related_qs = self._filter_queryset_for_cliente(request, related_qs, related_model)
                if _model_has_soft_delete(related_model):
                    related_qs = related_qs.filter(is_deleted=False)
                kwargs["queryset"] = related_qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if not self._is_super_admin(request):
            related_model = getattr(db_field.remote_field, "model", None)
            if related_model is not None and self._get_scope_lookup(related_model):
                manager = getattr(related_model, "raw_objects", related_model._default_manager)
                related_qs = manager.all()
                related_qs = self._filter_queryset_for_cliente(request, related_qs, related_model)
                if _model_has_soft_delete(related_model):
                    related_qs = related_qs.filter(is_deleted=False)
                kwargs["queryset"] = related_qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)
