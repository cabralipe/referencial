"""Views auxiliares da API v1."""

from __future__ import annotations

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

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


class SessionLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Logout realizado com sucesso"}, status=status.HTTP_200_OK)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
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
        # Força a criação do token CSRF
        token = get_token(request)
        return Response({"csrfToken": token})
