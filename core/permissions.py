"""Permissões DRF reutilizáveis."""

from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Usuario
from .utils import usuario_e_membro_do_gt


class HasClientScope(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, "role", None) == Usuario.Role.SUPER_ADMIN:
            return True
        return bool(getattr(request.user, "cliente_id", None))


class IsAdminClienteOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in {
            Usuario.Role.ADMIN_CLIENTE,
            Usuario.Role.SUPER_ADMIN,
        }


class IsAdminConsole(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in {
            Usuario.Role.ADMIN_CLIENTE,
            Usuario.Role.SUPER_ADMIN,
        }


class IsMemberOfGT(BasePermission):
    """Garante que o usuário é membro do GT envolvido."""

    def has_permission(self, request, view):
        gt_id = getattr(view, "gt_id", None) or request.data.get("gt") or request.query_params.get("gt_id")
        if not gt_id:
            return True
        return usuario_e_membro_do_gt(request.user, gt_id)

    def has_object_permission(self, request, view, obj):
        """Verifica permissão no nível do objeto quando disponível."""
        if hasattr(obj, 'gt_id'):
            return usuario_e_membro_do_gt(request.user, obj.gt_id)
        elif hasattr(obj, 'gt'):
            return usuario_e_membro_do_gt(request.user, obj.gt.id)
        return True


class IsArticuladorForGT(IsMemberOfGT):
    """Permite ações destrutivas apenas para articuladores/admins."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(request.user, "role", None) in {
            Usuario.Role.ARTICULADOR,
            Usuario.Role.ADMIN_CLIENTE,
            Usuario.Role.SUPER_ADMIN,
        }
