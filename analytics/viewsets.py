from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Usuario

from .services.reports import admin_dashboard, user_dashboard


class UserDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        data = user_dashboard(cliente_id=cliente_id, usuario_id=request.user.id)
        return Response(data)


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}:
            return Response({"detail": "Sem permissao."}, status=403)
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        return Response(admin_dashboard(cliente_id=cliente_id))

