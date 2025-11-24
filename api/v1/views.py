"""Views auxiliares da API v1."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.contrib.auth import login
from django.core.files.storage import default_storage
from django.middleware.csrf import get_token
from django.utils.text import slugify
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.activity import touch_user_session
from core.models import ClienteTema
from core.permissions import HasClientScope

from .serializers import ClienteMeSerializer, LoginSerializer


class SessionLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        request.cliente_id = getattr(user, "cliente_id", None)
        touch_user_session(request)
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


class MebAvatarUploadView(APIView):
    permission_classes = [HasClientScope]

    def post(self, request):
        user = request.user
        if getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            raise PermissionDenied("Somente administradores podem atualizar o avatar do MEB.")

        avatar = request.FILES.get("avatar")
        if not avatar:
            raise ValidationError({"avatar": "Envie um arquivo de imagem."})

        cliente_id = getattr(request, "cliente_id", None) or getattr(user, "cliente_id", None)
        if cliente_id is None:
            raise ValidationError("Cliente não identificado para o upload.")

        original_name = Path(avatar.name or "").stem or "avatar"
        filename = f"{slugify(original_name)}-{uuid4().hex}{Path(avatar.name or 'avatar.png').suffix or '.png'}"
        path = default_storage.save(f"meb/avatars/cliente_{cliente_id}/{filename}", avatar)
        url = default_storage.url(path)
        if url.startswith("/"):
            url = request.build_absolute_uri(url)

        tema, _ = ClienteTema.objects.get_or_create(
            cliente_id=cliente_id,
            defaults={"cor_primaria": "#004aad", "cor_secundaria": "#00b4d8"},
        )
        tema.meb_avatar_url = url
        tema.save(update_fields=["meb_avatar_url", "updated_at"])
        return Response({"url": url})
