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
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView

from core.activity import touch_user_session
from core.models import Cliente, ClienteTema
from core.permissions import HasClientScope
from services.progress import get_next_block_for_user
from services.diff import diff_last_approved
from consultas.models import ConsultaPublica, ManifestacaoPublica
from curriculum.models import Escola

from .serializers import (
    ClienteMeSerializer,
    ConsultaPublicaPublicSerializer,
    LoginSerializer,
    RoleTokenObtainPairSerializer,
    ManifestacaoPublicaCreateSerializer,
    ManifestacaoPublicaPublicSerializer,
    PublicClienteSerializer,
    PublicEscolaSerializer,
)


class RoleTokenObtainPairView(TokenObtainPairView):
    serializer_class = RoleTokenObtainPairSerializer


class SessionLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = []

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
                "escola_id": getattr(user, "escola_id", None),
            }
        }
        if user.cliente:
            data["cliente"] = ClienteMeSerializer.from_cliente(user.cliente).data
        return Response(data)


class AuthMeView(APIView):
    permission_classes = [HasClientScope]

    def get(self, request):
        user = request.user
        data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "nome": getattr(user, "nome", ""),
                "role": user.role,
                "cliente_id": user.cliente_id,
                "escola_id": getattr(user, "escola_id", None),
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


class ContinuarView(APIView):
    permission_classes = [HasClientScope]

    def get(self, request):
        bloco = get_next_block_for_user(request.user)
        if not bloco:
            return Response(
                {
                    "url": "/minha-trilha?concluida=1",
                    "message": "Todas as trilhas foram concluídas.",
                }
            )
        if bloco.resposta_id:
            url = f"/texto/{bloco.resposta_id}?gt={bloco.gt_id}"
        else:
            url = f"/minha-trilha/{bloco.tarefa_id}?gt={bloco.gt_id}"
        return Response(
            {
                "url": url,
                "status": bloco.status,
                "gt_id": bloco.gt_id,
                "tarefa_id": bloco.tarefa_id,
                "pergunta_id": bloco.pergunta_id,
                "resposta_id": bloco.resposta_id,
            }
        )


class ApprovedDiffView(APIView):
    permission_classes = [HasClientScope]

    def get(self, request):
        alvo_tipo = request.query_params.get("alvo_tipo")
        alvo_id = request.query_params.get("alvo_id")
        if not alvo_tipo or not alvo_id:
            raise ValidationError("Informe alvo_tipo e alvo_id")
        html = diff_last_approved(alvo_tipo, alvo_id)
        return Response({"html": html})


def _consulta_publica_por_token(token: str, require_open: bool = False) -> ConsultaPublica:
    consulta = ConsultaPublica.raw_objects.filter(token_acesso=token).first()
    if not consulta:
        raise NotFound("Consulta pública não encontrada.")
    if require_open and not consulta.esta_disponivel:
        raise ValidationError("Esta consulta pública não está recebendo novas contribuições.")
    return consulta


class ConsultaPublicaPublicView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, token: str):
        consulta = _consulta_publica_por_token(token, require_open=False)
        serializer = ConsultaPublicaPublicSerializer(consulta, context={"request": request})
        return Response(serializer.data)


class ManifestacaoPublicaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, token: str):
        consulta = _consulta_publica_por_token(token, require_open=False)
        manifestacoes = ManifestacaoPublica.objects.filter(consulta=consulta).order_by("-created_at")[:200]
        serializer = ManifestacaoPublicaPublicSerializer(manifestacoes, many=True)
        return Response(serializer.data)

    def post(self, request, token: str):
        consulta = _consulta_publica_por_token(token, require_open=True)
        serializer = ManifestacaoPublicaCreateSerializer(
            data=request.data,
            context={"consulta": consulta},
        )
        serializer.is_valid(raise_exception=True)
        manifestacao = serializer.save(
            consulta=consulta,
            cliente_id=consulta.cliente_id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        resposta = ManifestacaoPublicaPublicSerializer(manifestacao)
        return Response(resposta.data, status=201)


class PublicClientesEscolasView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        clientes = Cliente.objects.filter(escolas__isnull=False).distinct().order_by("nome")
        escolas = Escola.objects.all().order_by("nome")
        return Response({
            "clientes": PublicClienteSerializer(clientes, many=True).data,
            "escolas": PublicEscolaSerializer(escolas, many=True).data,
        })


class CadastroView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        from .serializers import CadastroSerializer
        serializer = CadastroSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"message": "Usuário cadastrado com sucesso", "id": user.id}, status=201)
