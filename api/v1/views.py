"""Views auxiliares da API v1."""

from __future__ import annotations

from django.contrib.auth import login
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ClienteMeSerializer, LoginSerializer


class SessionLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "nome": getattr(user, "nome", ""),
                "role": user.role,
                "cliente_id": user.cliente_id,
            }
        }
        if user.cliente:
            data["cliente"] = ClienteMeSerializer.from_cliente(user.cliente).data
        return Response(data)


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
<<<<<<< HEAD
        # Força a criação do token CSRF
=======
>>>>>>> 7e6ca79 (Video Prototipo)
        token = get_token(request)
        return Response({"csrfToken": token})
