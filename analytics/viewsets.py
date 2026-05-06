from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Usuario
from core.permissions import HasClientScope, IsAdminConsole
from core.scope import resolve_cliente_scope

from .services.reports import admin_dashboard, user_dashboard


class UserDashboardView(APIView):
    permission_classes = [HasClientScope]

    def _get_cliente_id(self, request) -> int:
        cliente_id = resolve_cliente_scope(request)
        if not cliente_id:
            raise ValidationError("Cliente não associado ao usuário.")
        return int(cliente_id)

    def get(self, request):
        cliente_id = self._get_cliente_id(request)
        data = user_dashboard(cliente_id=cliente_id, usuario_id=request.user.id)
        return Response(data)


class AdminDashboardView(APIView):
    permission_classes = [HasClientScope, IsAdminConsole]

    def _get_cliente_id(self, request) -> int:
        cliente_id = resolve_cliente_scope(request)
        if not cliente_id:
            raise ValidationError("Cliente não associado ao usuário.")
        return int(cliente_id)

    def get(self, request):
        if request.user.role not in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}:
            return Response({"detail": "Sem permissao."}, status=403)
        cliente_id = self._get_cliente_id(request)
        return Response(admin_dashboard(cliente_id=cliente_id))
