"""Viewsets da API v1."""

from __future__ import annotations

import json
import logging
import os
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models.functions import Cast
from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.views import APIView
try:  # botocore é usado apenas quando MEDIA_BACKEND=s3 está ativo
    from botocore.exceptions import BotoCoreError, ClientError, ParamValidationError

    STORAGE_EXCEPTIONS = (BotoCoreError, ClientError, ParamValidationError, OSError)
except ImportError:  # pragma: no cover
    STORAGE_EXCEPTIONS = (OSError,)

from core.activity import online_sessions_for_cliente
from core.models import AuditLog, Cliente, ClienteConfig, ScoreEntry, ThrottleBlock, UserSessionLog
from core.permissions import (
    HasClientScope,
    IsAdminClienteOrReadOnly,
    IsArticuladorForGT,
    IsMemberOfGT,
)
from core.utils import coletar_contexto_do_cliente, obter_config, verificar_flag
from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from curriculum.models import Anexo, GT, Pergunta, Resposta, Tarefa, TextoColaborativo, TextoUnico
from curriculum.services.collab_sync import broadcast_texto_colaborativo, sync_texto_colaborativo_from_resposta
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from notifications.services import criar_notificacao
from meb.models import MebMessage, MebThread
from meb.services import auto_reply_for_message, deliver_admin_broadcast, ensure_thread_for_user
from reviews.models import Revisao
from sockets.utils import broadcast_stream_event
from diffs.services import build_diff
from tasks.exports import enqueue_export_job
from tasks.synthesis import enqueue_texto_unico
from workshop.models import CelulaQuadro, Quadro

from .serializers import (
    AnexoSerializer,
    AuditLogSerializer,
    ThrottleBlockSerializer,
    CampoDinamicoSerializer,
    ClienteMeSerializer,
    AiAssistSerializer,
    OnlineUserSerializer,
    PerguntaWriteSerializer,
    PerguntaSerializer,
    GTSerializer,
    ExportJobSerializer,
    FormularioDinamicoSerializer,
    CelulaQuadroSerializer,
    QuadroSerializer,
    RespostaCampoDinamicoSerializer,
    RespostaSerializer,
    RevisaoSerializer,
    ComentarioSerializer,
    NotificacaoSerializer,
    MidiaSerializer,
    BlocoTextoSerializer,
    DiffResponseSerializer,
    MebMessageSerializer,
    MebThreadSerializer,
    TarefaSerializer,
    TextoColaborativoSerializer,
    TextoUnicoSerializer,
    UsuarioLookupSerializer,
    ConsultaPublicaSerializer,
    ManifestacaoPublicaSerializer,
)

logger = logging.getLogger(__name__)


class PreconditionFailed(APIException):
    status_code = 412
    default_code = "precondition_failed"
    default_detail = "Versão desatualizada. Atualize antes de salvar novamente."


def _check_etag(request, instance):
    header = request.headers.get("If-Match")
    if header and header != instance.etag:
        raise PreconditionFailed()


def _get_request_cliente_id(request) -> int:
    cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
    if cliente_id:
        return int(cliente_id)

    # Fallback para cenários em que apenas o GT é informado (ex.: super admin sem cliente associado).
    gt_lookup = (
        request.data.get("gt")
        or request.query_params.get("gt_id")
        or request.query_params.get("gt")
        or getattr(request, "gt_id", None)
    )
    if gt_lookup:
        gt = GT.objects.filter(pk=gt_lookup).first()
        if gt:
            return int(gt.cliente_id)

    raise ValidationError("Cliente não associado")


def _get_user_gt_ids(user) -> list[int]:
    if not getattr(user, "is_authenticated", False):
        return []
    return list(GT.objects.filter(membros=user).values_list("id", flat=True))


class FeatureFlagMixin:
    feature_flag: str | None = None

    def initial(self, request, *args, **kwargs):
        if self.feature_flag:
            verificar_flag(request, self.feature_flag)
        return super().initial(request, *args, **kwargs)


def _assert_roles(user, allowed_roles):
    if user.role in allowed_roles or user.role == user.Role.SUPER_ADMIN:
        return
    raise PermissionDenied("Ação não permitida para o seu perfil")


SCORE_CONFIG_KEY = "score.config"
DEFAULT_SCORE_CONFIG = {
    "monthly_limit": 300,
    "default_points": 10,
    "tarefa_points": {},
}


def _normalize_score_config(payload):
    config = {
        "monthly_limit": DEFAULT_SCORE_CONFIG["monthly_limit"],
        "default_points": DEFAULT_SCORE_CONFIG["default_points"],
        "tarefa_points": {},
    }
    if not payload:
        return config
    raw = payload
    if isinstance(payload, str):
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError:
            return config
    if isinstance(raw, dict):
        monthly_limit = raw.get("monthly_limit")
        default_points = raw.get("default_points")
        tarefa_points = raw.get("tarefa_points") or {}
        if monthly_limit is not None:
            try:
                config["monthly_limit"] = max(int(monthly_limit), 0)
            except (TypeError, ValueError):
                pass
        if default_points is not None:
            try:
                config["default_points"] = max(int(default_points), 0)
            except (TypeError, ValueError):
                pass
        if isinstance(tarefa_points, dict):
            sanitized = {}
            for key, value in tarefa_points.items():
                try:
                    pontos = int(value)
                except (TypeError, ValueError):
                    continue
                sanitized[str(key)] = max(pontos, 0)
            config["tarefa_points"] = sanitized
    return config


def _get_score_config(cliente_id: int):
    cliente = Cliente.objects.filter(pk=cliente_id).first()
    if not cliente:
        return _normalize_score_config(None)
    raw = obter_config(cliente, SCORE_CONFIG_KEY)
    return _normalize_score_config(raw)


def _save_score_config(cliente_id: int, payload):
    config = _normalize_score_config(payload)
    ClienteConfig.raw_objects.update_or_create(
        cliente_id=cliente_id,
        chave=SCORE_CONFIG_KEY,
        defaults={
            "valor_texto": json.dumps(config, ensure_ascii=True),
            "is_deleted": False,
        },
    )
    return config


def _registrar_score(request, cliente_id: int, tarefa_id: int | None, origem_tipo: str, origem_id: str | int, descricao: str = ""):
    user = request.user
    if not user or not user.is_authenticated:
        return
    if user.role not in {user.Role.ARTICULADOR, user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
        return
    config = _get_score_config(cliente_id)
    pontos = config.get("default_points", DEFAULT_SCORE_CONFIG["default_points"])
    if tarefa_id:
        pontos = config.get("tarefa_points", {}).get(str(tarefa_id), pontos)
    try:
        pontos = int(pontos)
    except (TypeError, ValueError):
        pontos = DEFAULT_SCORE_CONFIG["default_points"]
    if pontos <= 0:
        return
    ScoreEntry.objects.create(
        cliente_id=cliente_id,
        usuario_id=user.id,
        origem_tipo=origem_tipo,
        origem_id=str(origem_id),
        tarefa_id=tarefa_id,
        pontos=pontos,
        descricao=descricao,
    )


def _atualizar_status_tarefa(tarefa: Tarefa, novo_status: str) -> None:
    if tarefa.status == Tarefa.Status.CONCLUIDA:
        return
    if tarefa.status == novo_status:
        return
    tarefa.status = novo_status
    tarefa.save(update_fields=["status", "updated_at"])


def _build_gemini_prompt(mode: str, text: str, context: str) -> str:
    base = "Responda em portugues do Brasil, com clareza e objetividade."
    if mode == "draft":
        return (
            f"{base}\n"
            "Tarefa: gerar um rascunho para uma missao.\n"
            f"Contexto: {context}\n"
            f"Entrada: {text}\n"
            "Saida: rascunho direto, sem markdown."
        )
    if mode == "grammar":
        return (
            f"{base}\n"
            "Tarefa: corrigir gramatica e melhorar fluidez sem mudar o sentido.\n"
            f"Texto: {text}\n"
            "Saida: texto revisado, sem markdown."
        )
    return (
        f"{base}\n"
        "Tarefa: produzir um parecer de revisao curto, indicando ajustes e pontos fortes.\n"
        f"Contexto: {context}\n"
        f"Texto: {text}\n"
        "Saida: parecer objetivo, com sugestoes praticas."
    )


class ClienteViewSet(viewsets.ViewSet):
    permission_classes = [HasClientScope]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        if request.user.is_super_admin and request.headers.get("X-Cliente-ID"):
            cliente_id = request.headers.get("X-Cliente-ID")
        cliente = Cliente.objects.filter(pk=cliente_id).first()
        if not cliente:
            raise ValidationError("Cliente não associado ao usuário")
        serializer = ClienteMeSerializer.from_cliente(cliente)
        return Response(serializer.data)


class ScoreViewSet(viewsets.ViewSet):
    permission_classes = [HasClientScope]

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        cliente_id = _get_request_cliente_id(request)
        config = _get_score_config(cliente_id)
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = (
            ScoreEntry.objects.filter(
                cliente_id=cliente_id,
                usuario_id=request.user.id,
                created_at__gte=start_of_month,
            )
            .aggregate(total=models.Sum("pontos"))
            .get("total")
            or 0
        )
        monthly_limit = config.get("monthly_limit") or 0
        progress = (total / monthly_limit) if monthly_limit else 0
        return Response(
            {
                "current_points": total,
                "monthly_limit": monthly_limit,
                "progress": progress,
                "default_points": config.get("default_points"),
            }
        )

    @action(
        detail=False,
        methods=["get", "patch"],
        url_path="config",
        permission_classes=[HasClientScope, IsAdminClienteOrReadOnly],
    )
    def config(self, request):
        cliente_id = _get_request_cliente_id(request)
        if request.method == "PATCH":
            _assert_roles(request.user, {request.user.Role.ADMIN_CLIENTE})
            config = _save_score_config(cliente_id, request.data)
            return Response(config)
        return Response(_get_score_config(cliente_id))


class AiAssistViewSet(viewsets.ViewSet):
    permission_classes = [HasClientScope]

    def create(self, request):
        _assert_roles(
            request.user,
            {
                request.user.Role.MEMBRO_GT,
                request.user.Role.ARTICULADOR,
                request.user.Role.ADMIN_CLIENTE,
            },
        )
        serializer = AiAssistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mode = serializer.validated_data["mode"]
        text = serializer.validated_data["text"]
        context = serializer.validated_data.get("context") or ""

        if not os.environ.get("GEMINI_API_KEY"):
            raise ValidationError("GEMINI_API_KEY nao configurada no ambiente.")

        try:
            from google import genai
        except ImportError as exc:
            raise ValidationError("Biblioteca google-genai nao instalada.") from exc

        prompt = _build_gemini_prompt(mode, text, context)
        client = genai.Client()
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
        except Exception as exc:  # pragma: no cover
            raise ValidationError("Falha ao gerar resposta com IA.") from exc
        output = getattr(response, "text", None) or ""
        return Response({"output": output})


class GTViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GTSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ("etapa",)
    search_fields = ("nome",)

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = GT.objects.filter(cliente_id=cliente_id).order_by("nome")
        user = self.request.user
        if not getattr(user, "is_authenticated", False):
            return queryset.none()

        only_member_param = str(self.request.query_params.get("only_member", "")).lower()
        only_member = only_member_param in {"1", "true", "yes"}

        if only_member:
            return queryset.filter(membros=user)

        if getattr(user, "role", None) in {
            user.Role.ADMIN_CLIENTE,
            user.Role.SUPER_ADMIN,
        }:
            return queryset
        return queryset.filter(membros=user)


class ConsultaPublicaViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultaPublicaSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ("ativa",)
    search_fields = ("titulo", "slug")
    ordering = ("-data_publicacao", "-created_at")

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        return ConsultaPublica.objects.filter(cliente_id=cliente_id).annotate(
            manifestacoes_count=Count("manifestacoes")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        try:
            ctx["cliente_id"] = _get_request_cliente_id(self.request)
        except ValidationError:
            ctx["cliente_id"] = None
        return ctx

    def perform_create(self, serializer):
        user = self.request.user
        _assert_roles(user, {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN})
        try:
            consulta = serializer.save(
                cliente_id=_get_request_cliente_id(self.request),
                criada_por=user,
            )
        except STORAGE_EXCEPTIONS as exc:
            logger.exception("Erro ao salvar PDF da consulta pública")
            raise ValidationError({"pdf": "Falha ao salvar o PDF. Verifique a configuração do armazenamento de mídia."}) from exc
        self._created_instance = consulta

    def perform_update(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN})
        try:
            serializer.save()
        except STORAGE_EXCEPTIONS as exc:
            logger.exception("Erro ao atualizar PDF da consulta pública")
            raise ValidationError({"pdf": "Falha ao salvar o PDF. Verifique a configuração do armazenamento de mídia."}) from exc

    def perform_destroy(self, instance):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN})
        super().perform_destroy(instance)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = getattr(self, "_created_instance", None)
        if instance:
            response["ETag"] = f"W/\"consulta-{instance.pk}-v{int(instance.updated_at.timestamp())}\""
        return response

    @action(detail=True, methods=["get"], url_path="manifestacoes")
    def manifestacoes(self, request, pk=None):
        consulta = self.get_object()
        _assert_roles(request.user, {request.user.Role.ADMIN_CLIENTE, request.user.Role.SUPER_ADMIN})
        manifestacoes = ManifestacaoPublica.objects.filter(consulta=consulta)
        serializer = ManifestacaoPublicaSerializer(manifestacoes, many=True)
        return Response(serializer.data)


class TarefaViewSet(viewsets.ModelViewSet):
    serializer_class = TarefaSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("tipo", "status")

    def get_queryset(self):
        queryset = Tarefa.objects.all().order_by("ordem")
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
            user_gt_ids = _get_user_gt_ids(user)
            if not user_gt_ids:
                return queryset.none()
            queryset = queryset.filter(
                models.Q(perguntas__gts__id__in=user_gt_ids)
                | models.Q(perguntas__gts__isnull=True)
                | models.Q(perguntas__isnull=True)
            ).distinct()
        etapa = self.request.query_params.get("etapa")
        gt_id = self.request.query_params.get("gt_id")
        if etapa:
            queryset = queryset.filter(etapa=etapa)
        if gt_id:
            queryset = queryset.filter(perguntas__respostas__gt_id=gt_id).distinct()
        return queryset

    @action(detail=True, methods=["get"], url_path="perguntas")
    def perguntas(self, request, pk=None):
        tarefa = self.get_object()
        perguntas = tarefa.perguntas.order_by("ordem")
        serializer = PerguntaSerializer(perguntas, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ARTICULADOR, self.request.user.Role.ADMIN_CLIENTE})
        serializer.save(cliente_id=_get_request_cliente_id(self.request))

    def perform_update(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ARTICULADOR, self.request.user.Role.ADMIN_CLIENTE})
        serializer.save()

    def perform_destroy(self, instance):
        _assert_roles(self.request.user, {self.request.user.Role.ARTICULADOR, self.request.user.Role.ADMIN_CLIENTE})
        super().perform_destroy(instance)


class PerguntaViewSet(viewsets.ModelViewSet):
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("tarefa",)

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Pergunta.objects.filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
            user_gt_ids = _get_user_gt_ids(user)
            if not user_gt_ids:
                return queryset.none()
            queryset = queryset.filter(
                models.Q(gts__id__in=user_gt_ids) | models.Q(gts__isnull=True)
            ).distinct()
        return queryset.order_by("tarefa_id", "ordem")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PerguntaWriteSerializer
        return PerguntaSerializer

    def perform_create(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ARTICULADOR, self.request.user.Role.ADMIN_CLIENTE})
        serializer.save(cliente_id=_get_request_cliente_id(self.request))

    def perform_update(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ARTICULADOR, self.request.user.Role.ADMIN_CLIENTE})
        serializer.save()

    def perform_destroy(self, instance):
        _assert_roles(self.request.user, {self.request.user.Role.ARTICULADOR, self.request.user.Role.ADMIN_CLIENTE})
        super().perform_destroy(instance)


class RespostaViewSet(viewsets.ModelViewSet):
    serializer_class = RespostaSerializer
    permission_classes = [HasClientScope, IsMemberOfGT]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("gt", "pergunta")

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Resposta.objects.select_related(
            "gt",
            "pergunta",
            "pergunta__tarefa",
            "autor",
        ).filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
            gt_ids = _get_user_gt_ids(user)
            if not gt_ids:
                return queryset.none()
            queryset = queryset.filter(gt_id__in=gt_ids)
        gt_id = self.request.query_params.get("gt_id")
        pergunta_id = self.request.query_params.get("pergunta_id")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        if pergunta_id:
            queryset = queryset.filter(pergunta_id=pergunta_id)
        return queryset.order_by("pergunta__ordem")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gt = serializer.validated_data["gt"]
        pergunta = serializer.validated_data["pergunta"]
        cliente_id = gt.cliente_id or _get_request_cliente_id(request)
        # Usar raw_objects para evitar perder registros já existentes por filtros multi-tenant
        resposta = Resposta.raw_objects.filter(cliente_id=cliente_id, gt_id=gt.pk, pergunta_id=pergunta.pk).first()
        created_collab = False
        with transaction.atomic():
            if resposta:
                _check_etag(request, resposta)
                serializer = self.get_serializer(resposta, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save(cliente_id=cliente_id)
                resposta = serializer.instance
                status_code = status.HTTP_200_OK
                headers = {"ETag": resposta.etag}
            else:
                try:
                    serializer.save(cliente_id=cliente_id)
                    resposta = serializer.instance
                    status_code = status.HTTP_201_CREATED
                    headers = self.get_success_headers(serializer.data)
                    headers["ETag"] = resposta.etag
                except Exception as exc:
                    # Se houver corrida ou registro prévio, faz fallback para update
                    existing = Resposta.raw_objects.filter(cliente_id=cliente_id, gt_id=gt.pk, pergunta_id=pergunta.pk).first()
                    if existing is None:
                        raise
                    _check_etag(request, existing)
                    serializer = self.get_serializer(existing, data=request.data, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save(cliente_id=cliente_id)
                    resposta = serializer.instance
                    status_code = status.HTTP_200_OK
                    headers = {"ETag": resposta.etag}

            texto_colab, created_collab = sync_texto_colaborativo_from_resposta(resposta)

        broadcast_texto_colaborativo(texto_colab, created=created_collab)
        if getattr(request.user, "role", None) == request.user.Role.MEMBRO_GT and resposta.pergunta_id:
            _atualizar_status_tarefa(resposta.pergunta.tarefa, Tarefa.Status.EM_DESENVOLVIMENTO)
        _registrar_score(
            request,
            cliente_id,
            tarefa_id=resposta.pergunta.tarefa_id if resposta.pergunta_id else None,
            origem_tipo="revisao_texto",
            origem_id=resposta.id,
            descricao="Revisão de texto",
        )
        return Response(serializer.data, status=status_code, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        _check_etag(request, instance)
        with transaction.atomic():
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save(cliente_id=instance.cliente_id)
            resposta = serializer.instance
            texto_colab, created_collab = sync_texto_colaborativo_from_resposta(resposta)

        broadcast_texto_colaborativo(texto_colab, created=created_collab)
        if getattr(request.user, "role", None) == request.user.Role.MEMBRO_GT and resposta.pergunta_id:
            _atualizar_status_tarefa(resposta.pergunta.tarefa, Tarefa.Status.EM_DESENVOLVIMENTO)
        _registrar_score(
            request,
            instance.cliente_id,
            tarefa_id=resposta.pergunta.tarefa_id if resposta.pergunta_id else None,
            origem_tipo="revisao_texto",
            origem_id=resposta.id,
            descricao="Revisão de texto",
        )
        response = Response(serializer.data)
        response["ETag"] = serializer.instance.etag
        return response

    @action(detail=True, methods=["post"], url_path="anexos")
    def anexos(self, request, pk=None):
        resposta = self.get_object()
        data = request.data.copy()
        data["resposta"] = resposta.pk
        serializer = AnexoSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=resposta.cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TextoUnicoViewSet(viewsets.ModelViewSet):
    serializer_class = TextoUnicoSerializer
    permission_classes = [HasClientScope, IsArticuladorForGT]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("gt", "tarefa")

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = TextoUnico.objects.select_related("gt", "tarefa").filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
            gt_ids = _get_user_gt_ids(user)
            if not gt_ids:
                return queryset.none()
            queryset = queryset.filter(gt_id__in=gt_ids)
        gt_id = self.request.query_params.get("gt_id")
        tarefa_id = self.request.query_params.get("tarefa_id")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        if tarefa_id:
            queryset = queryset.filter(tarefa_id=tarefa_id)
        return queryset

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente_id=instance.cliente_id)
        response = Response(serializer.data)
        response["ETag"] = serializer.instance.etag
        return response

    @action(detail=False, methods=["post"], url_path="gerar")
    def gerar(self, request):
        gt_id = request.query_params.get("gt_id") or request.data.get("gt_id")
        tarefa_id = request.query_params.get("tarefa_id") or request.data.get("tarefa_id")
        if not gt_id or not tarefa_id:
            raise ValidationError("Informe gt_id e tarefa_id")
        cliente_id = _get_request_cliente_id(request)
        texto_unico, _ = TextoUnico.objects.get_or_create(
            gt_id=gt_id,
            tarefa_id=tarefa_id,
            cliente_id=cliente_id,
        )
        enqueue_texto_unico(texto_unico.id)
        serializer = self.get_serializer(texto_unico)
        response = Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        response["ETag"] = texto_unico.etag
        return response


class TextoColaborativoViewSet(viewsets.ModelViewSet):
    serializer_class = TextoColaborativoSerializer
    permission_classes = [HasClientScope, IsMemberOfGT]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("gt", "pergunta")

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = TextoColaborativo.objects.filter(cliente_id=cliente_id)
        gt_id = self.request.query_params.get("gt") or self.request.query_params.get("gt_id")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        pergunta_id = self.request.query_params.get("pergunta") or self.request.query_params.get("pergunta_id")
        if pergunta_id:
            queryset = queryset.filter(pergunta_id=pergunta_id)
        return queryset.order_by("-updated_at")

    def perform_create(self, serializer):
        gt = serializer.validated_data.get("gt")
        cliente_id = gt.cliente_id if gt else _get_request_cliente_id(self.request)
        instance = serializer.save(cliente_id=cliente_id)
        self._created_instance = instance
        self._broadcast(instance, created=True)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = getattr(self, "_created_instance", None)
        if instance:
            response["ETag"] = instance.etag
        return response

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        texto = serializer.save(cliente_id=instance.cliente_id)
        self._broadcast(texto, created=False)
        response = Response(serializer.data)
        response["ETag"] = texto.etag
        return response

    @action(detail=False, methods=["put"], url_path="lote")
    def batch_update(self, request, *args, **kwargs):
        payload = request.data.get("textos")
        if not isinstance(payload, list):
            raise ValidationError({"textos": "Envie uma lista de textos para atualizar em lote."})

        updated = []
        errors = []
        for entry in payload:
            texto_id = entry.get("id")
            etag = entry.get("etag") or entry.get("if_match")
            if not texto_id:
                errors.append({"id": None, "error": "ID do texto é obrigatório."})
                continue
            if not etag:
                errors.append({"id": texto_id, "error": "ETag obrigatório para atualização segura."})
                continue

            instance = TextoColaborativo.objects.filter(pk=texto_id).first()
            if not instance:
                errors.append({"id": texto_id, "error": "Texto colaborativo não encontrado."})
                continue

            try:
                self.check_object_permissions(request, instance)
            except PermissionDenied:
                errors.append({"id": texto_id, "error": "Permissão negada para este texto."})
                continue

            if etag != instance.etag:
                errors.append({"id": texto_id, "error": "Versão desatualizada.", "etag": instance.etag})
                continue

            serializer = self.get_serializer(
                instance,
                data={
                    "titulo": entry.get("titulo", instance.titulo),
                    "conteudo_html": entry.get("conteudo_html", instance.conteudo_html),
                },
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            texto_atualizado = serializer.save(cliente_id=instance.cliente_id)
            updated.append(serializer.data)
            broadcast_texto_colaborativo(texto_atualizado, created=False)

        status_code = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response({"updated": updated, "errors": errors}, status=status_code)

    def _broadcast(self, instance: TextoColaborativo, *, created: bool) -> None:
        broadcast_texto_colaborativo(instance, created=created)


class QuadroViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuadroSerializer
    permission_classes = [HasClientScope, IsMemberOfGT]

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Quadro.objects.select_related("gt").filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
            gt_ids = _get_user_gt_ids(user)
            if not gt_ids:
                return queryset.none()
            queryset = queryset.filter(gt_id__in=gt_ids)
        gt_id = self.request.query_params.get("gt_id")
        template = self.request.query_params.get("template")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        if template:
            queryset = queryset.filter(template=template)
        return queryset

    @action(detail=True, methods=["put"], url_path="celula")
    def atualizar_celula(self, request, pk=None):
        quadro = self.get_object()
        linha = request.data.get("linha")
        coluna = request.data.get("coluna")
        if linha is None or coluna is None:
            raise ValidationError("linha e coluna são obrigatórios")
        celula, _ = CelulaQuadro.objects.get_or_create(
            quadro=quadro,
            linha=linha,
            coluna=coluna,
            defaults={"cliente": quadro.cliente},
        )
        serializer = CelulaQuadroSerializer(celula, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=quadro.cliente)
        return Response(serializer.data)


class FormularioDinamicoViewSet(viewsets.ModelViewSet):
    serializer_class = FormularioDinamicoSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        queryset = FormularioDinamico.objects.filter(ativo=True)
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.ARTICULADOR, user.Role.SUPER_ADMIN}:
            return FormularioDinamico.objects.all()
        return queryset

    def perform_create(self, serializer):
        _assert_roles(
            self.request.user,
            {
                self.request.user.Role.ADMIN_CLIENTE,
                self.request.user.Role.ARTICULADOR,
                self.request.user.Role.MEMBRO_GT,
            },
        )
        serializer.save(cliente_id=_get_request_cliente_id(self.request))

    def perform_update(self, serializer):
        _assert_roles(
            self.request.user,
            {
                self.request.user.Role.ADMIN_CLIENTE,
                self.request.user.Role.ARTICULADOR,
                self.request.user.Role.MEMBRO_GT,
            },
        )
        serializer.save()

    @action(detail=True, methods=["get"], url_path="campos")
    def campos(self, request, pk=None):
        formulario = self.get_object()
        serializer = CampoDinamicoSerializer(formulario.campos.order_by("ordem"), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="campos")
    def criar_campo(self, request, pk=None):
        formulario = self.get_object()
        _assert_roles(
            request.user,
            {
                request.user.Role.ADMIN_CLIENTE,
                request.user.Role.ARTICULADOR,
                request.user.Role.MEMBRO_GT,
            },
        )
        serializer = CampoDinamicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campo = serializer.save(formulario=formulario, cliente_id=formulario.cliente_id)
        return Response(CampoDinamicoSerializer(campo).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="respostas")
    def respostas(self, request, pk=None):
        formulario = self.get_object()
        data = request.data.copy()
        data["formulario"] = formulario.pk
        cliente_id = _get_request_cliente_id(request)

        campo_id = data.get("campo")
        if not campo_id:
            raise ValidationError({"campo": "Campo é obrigatório"})
        if not formulario.campos.filter(pk=campo_id).exists():
            raise ValidationError({"campo": "Campo não pertence a este formulário"})

        owner_type = data.get("owner_type") or RespostaCampoDinamico.OwnerType.RESPOSTA
        data["owner_type"] = owner_type
        owner_id = data.get("owner_id")
        if owner_id is None:
            raise ValidationError({"owner_id": "Identificador do proprietário é obrigatório"})
        if owner_type == RespostaCampoDinamico.OwnerType.GT:
            user = request.user
            if getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
                pass
            else:
                if not GT.objects.filter(pk=owner_id, membros=user).exists():
                    raise PermissionDenied("Permissão negada para este GT.")

        instance = RespostaCampoDinamico.objects.filter(
            formulario=formulario,
            campo_id=campo_id,
            owner_type=owner_type,
            owner_id=str(owner_id),
            cliente_id=cliente_id,
        ).first()

        serializer = RespostaCampoDinamicoSerializer(instance, data=data, partial=bool(instance))
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente_id=cliente_id, formulario=formulario)
        status_code = status.HTTP_200_OK if instance else status.HTTP_201_CREATED
        return Response(serializer.data, status=status_code)


class ExportJobViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ExportJobSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = ExportJob.objects.filter(cliente_id=cliente_id)
        user = self.request.user
        alvo_tipo = self.request.query_params.get("alvo_tipo")
        alvo_id = self.request.query_params.get("alvo_id")
        if alvo_tipo:
            queryset = queryset.filter(alvo_tipo=alvo_tipo)
        if alvo_id:
            queryset = queryset.filter(alvo_id=str(alvo_id))
        if getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            return queryset
        gt_ids = _get_user_gt_ids(user)
        if not gt_ids:
            return queryset.none()
        resposta_ids = Resposta.objects.filter(gt_id__in=gt_ids).annotate(
            id_text=Cast("id", models.CharField()),
        ).values("id_text")
        texto_unico_ids = TextoUnico.objects.filter(gt_id__in=gt_ids).annotate(
            id_text=Cast("id", models.CharField()),
        ).values("id_text")
        quadro_ids = Quadro.objects.filter(gt_id__in=gt_ids).annotate(
            id_text=Cast("id", models.CharField()),
        ).values("id_text")
        queryset = queryset.filter(
            models.Q(alvo_tipo=ExportJob.AlvoTipo.RESPOSTA, alvo_id__in=resposta_ids)
            | models.Q(alvo_tipo=ExportJob.AlvoTipo.TEXTO_UNICO, alvo_id__in=texto_unico_ids)
            | models.Q(alvo_tipo=ExportJob.AlvoTipo.QUADRO, alvo_id__in=quadro_ids)
            | models.Q(alvo_tipo=ExportJob.AlvoTipo.COLECAO, payload_json__gt_ids__contained_by=gt_ids)
        )
        return queryset

    def perform_create(self, serializer):
        cliente_id = _get_request_cliente_id(self.request)
        job = serializer.save(cliente_id=cliente_id)
        enqueue_export_job(job.id)


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [HasClientScope, IsAdminClienteOrReadOnly]

    def get_queryset(self):
        queryset = AuditLog.objects.all()
        qp = self.request.query_params
        entidade = qp.get("entidade")
        entidade_id = qp.get("entidade_id")
        usuario_id = qp.get("usuario_id")
        acao = qp.get("acao")
        date_from = qp.get("date_from")
        date_to = qp.get("date_to")

        if entidade:
            queryset = queryset.filter(entidade=entidade)
        if entidade_id:
            queryset = queryset.filter(entidade_id=entidade_id)
        if usuario_id:
            try:
                queryset = queryset.filter(usuario_id=int(usuario_id))
            except (TypeError, ValueError):
                pass
        if acao:
            queryset = queryset.filter(acao__iexact=acao)
        if date_from:
            dt = parse_datetime(date_from) or parse_date(date_from)
            if dt:
                try:
                    # datetime
                    start = dt
                except Exception:
                    # date
                    from datetime import datetime
                    start = datetime(dt.year, dt.month, dt.day, 0, 0, 0)
                if timezone.is_naive(start):
                    start = timezone.make_aware(start, timezone.get_current_timezone())
                queryset = queryset.filter(timestamp__gte=start)
        if date_to:
            dt = parse_datetime(date_to) or parse_date(date_to)
            if dt:
                try:
                    end = dt
                except Exception:
                    from datetime import datetime
                    end = datetime(dt.year, dt.month, dt.day, 23, 59, 59)
                if timezone.is_naive(end):
                    end = timezone.make_aware(end, timezone.get_current_timezone())
                queryset = queryset.filter(timestamp__lte=end)
        return queryset.order_by("-timestamp")

    @action(detail=False, methods=["get"], url_path="online")
    def online(self, request):
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        sessions = online_sessions_for_cliente(cliente_id)
        serializer = OnlineUserSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="sessions")
    def sessions(self, request):
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        try:
            days_param = int(str(request.query_params.get("days", "30")))
        except ValueError:
            days_param = 30
        try:
            limit_param = int(str(request.query_params.get("limit", "100")))
        except ValueError:
            limit_param = 100

        cutoff = timezone.now() - timedelta(days=days_param)
        queryset = UserSessionLog.objects.filter(first_seen_at__gte=cutoff)
        if cliente_id is not None:
            queryset = queryset.filter(cliente_id=cliente_id)
        queryset = queryset.select_related("usuario", "cliente").order_by("-first_seen_at")
        if limit_param > 0:
            queryset = queryset[:limit_param]
        serializer = OnlineUserSerializer(queryset, many=True)
        return Response(serializer.data)


class ThrottleBlockViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = ThrottleBlockSerializer
    permission_classes = [HasClientScope]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        _assert_roles(user, {user.Role.ADMIN_CLIENTE})
        queryset = ThrottleBlock.objects.select_related("usuario", "cliente")
        if not getattr(user, "is_super_admin", False):
            queryset = queryset.filter(cliente_id=getattr(user, "cliente_id", None))
        show_all = str(self.request.query_params.get("show_all", "")).lower() in {"1", "true", "sim"}
        if not show_all:
            queryset = queryset.filter(blocked_until__gt=timezone.now())
        return queryset.order_by("-blocked_until", "-created_at")

    def destroy(self, request, *args, **kwargs):
        _assert_roles(request.user, {request.user.Role.ADMIN_CLIENTE})
        instance = self.get_object()
        if instance.cache_key:
            from django.core.cache import cache
            cache.delete(instance.cache_key)
        return super().destroy(request, *args, **kwargs)


class RevisaoViewSet(FeatureFlagMixin, viewsets.ModelViewSet):
    serializer_class = RevisaoSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("alvo_tipo", "alvo_id", "status")
    ordering = ("-created_at",)
    throttle_scope = "reviews-write"
    feature_flag = "ff.reviews.enabled"

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Revisao.objects.filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) == user.Role.ARTICULADOR:
            queryset = queryset.filter(models.Q(revisor_id=user.id) | models.Q(solicitante_id=user.id))
            gt_ids = _get_user_gt_ids(user)
            if not gt_ids:
                return queryset.none()
            resposta_ids = Resposta.objects.filter(gt_id__in=gt_ids).annotate(
                id_text=Cast("id", models.CharField()),
            ).values("id_text")
            texto_unico_ids = TextoUnico.objects.filter(gt_id__in=gt_ids).annotate(
                id_text=Cast("id", models.CharField()),
            ).values("id_text")
            quadro_ids = Quadro.objects.filter(gt_id__in=gt_ids).annotate(
                id_text=Cast("id", models.CharField()),
            ).values("id_text")
            queryset = queryset.filter(
                models.Q(alvo_tipo=Revisao.AlvoTipo.RESPOSTA, alvo_id__in=resposta_ids)
                | models.Q(alvo_tipo=Revisao.AlvoTipo.TEXTO_UNICO, alvo_id__in=texto_unico_ids)
                | models.Q(alvo_tipo=Revisao.AlvoTipo.QUADRO, alvo_id__in=quadro_ids)
            )
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        _assert_roles(user, {user.Role.ARTICULADOR, user.Role.ADMIN_CLIENTE})
        revisao = serializer.save(
            cliente_id=_get_request_cliente_id(self.request),
            solicitante=user,
        )
        self._created_instance = revisao
        if revisao.revisor:
            criar_notificacao(
                cliente_id=revisao.cliente_id,
                usuario_id=revisao.revisor_id,
                tipo="revisao.solicitada",
                payload={"revisao_id": revisao.id, "status": revisao.status},
            )
        broadcast_stream_event(revisao.alvo_tipo, revisao.alvo_id, "review:status_changed", {
            "revisao_id": revisao.id,
            "status": revisao.status,
        })
        tarefa_id = None
        if revisao.alvo_tipo == revisao.AlvoTipo.RESPOSTA:
            resposta = Resposta.objects.select_related("pergunta__tarefa").filter(pk=revisao.alvo_id).first()
            if resposta and resposta.pergunta_id:
                tarefa_id = resposta.pergunta.tarefa_id
        elif revisao.alvo_tipo == revisao.AlvoTipo.TEXTO_UNICO:
            texto = TextoUnico.objects.filter(pk=revisao.alvo_id).first()
            if texto:
                tarefa_id = texto.tarefa_id
        _registrar_score(
            self.request,
            revisao.cliente_id,
            tarefa_id=tarefa_id,
            origem_tipo="parecer",
            origem_id=revisao.id,
            descricao="Parecer de revisão",
        )
        if tarefa_id:
            tarefa = Tarefa.objects.filter(pk=tarefa_id).first()
            if tarefa:
                _atualizar_status_tarefa(tarefa, Tarefa.Status.EM_REVISAO)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = getattr(self, "_created_instance", None)
        if instance:
            response["ETag"] = instance.etag
        return response


class UsuarioLookupViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UsuarioLookupSerializer
    permission_classes = [HasClientScope]
    filter_backends = [filters.SearchFilter]
    search_fields = ("nome", "email")

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = get_user_model().objects.filter(cliente_id=cliente_id)
        q = self.request.query_params.get("q")
        if q:
            # SearchFilter will still apply; keeping explicit filter for non-standard setups
            queryset = queryset.filter(models.Q(nome__icontains=q) | models.Q(email__icontains=q))
        return queryset.order_by("nome")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        if request.user != instance.revisor:
            _assert_roles(request.user, {request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE})
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        old_status = instance.status
        revisao = serializer.save()
        if revisao.status != old_status:
            interessados = [uid for uid in [revisao.solicitante_id, revisao.revisor_id] if uid]
            for usuario_id in interessados:
                criar_notificacao(
                    cliente_id=revisao.cliente_id,
                    usuario_id=usuario_id,
                    tipo="revisao.status",
                    payload={"revisao_id": revisao.id, "status": revisao.status},
                )
            broadcast_stream_event(
                revisao.alvo_tipo,
                revisao.alvo_id,
                "review:status_changed",
                {"revisao_id": revisao.id, "status": revisao.status},
            )
        response = Response(serializer.data)
        response["ETag"] = revisao.etag
        return response


class ComentarioViewSet(FeatureFlagMixin, viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("alvo_tipo", "alvo_id", "resolvido")
    feature_flag = "ff.comments.enabled"
    throttle_scope = "comments-write"

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        return Comentario.objects.filter(cliente_id=cliente_id).select_related("autor", "resolvido_por")

    def perform_create(self, serializer):
        user = self.request.user
        _assert_roles(user, {user.Role.MEMBRO_GT, user.Role.ARTICULADOR, user.Role.ADMIN_CLIENTE})
        mentions_ids = serializer.validated_data.pop("mentions", [])
        comentario = serializer.save(
            cliente_id=_get_request_cliente_id(self.request),
            autor=user,
        )
        if mentions_ids:
            usuarios = get_user_model().objects.filter(id__in=mentions_ids, cliente_id=comentario.cliente_id)
            comentario.mentions.set(usuarios)
        self._created_instance = comentario
        broadcast_stream_event(
            comentario.alvo_tipo,
            comentario.alvo_id,
            "comment:created",
            {
                "comentario_id": comentario.id,
                "autor_id": comentario.autor_id,
                "conteudo_html": comentario.conteudo_html,
                "anchor_json": comentario.anchor_json,
            },
        )
        for mention in comentario.mentions.all():
            criar_notificacao(
                cliente_id=comentario.cliente_id,
                usuario_id=mention.id,
                tipo="comentario.mention",
                payload={"comentario_id": comentario.id, "alvo_tipo": comentario.alvo_tipo, "alvo_id": comentario.alvo_id},
            )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = getattr(self, "_created_instance", None)
        if instance:
            response["ETag"] = instance.etag
        return response

    def update(self, request, *args, **kwargs):
        # Permitimos updates parciais mesmo para requisições PUT, pois a
        # interface usa o método para marcar comentários como resolvidos sem
        # reenviar todo o payload original.
        parcial = kwargs.pop("partial", True)
        instance = self.get_object()
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=parcial)
        serializer.is_valid(raise_exception=True)
        vai_resolver = (
            serializer.validated_data.get("resolvido")
            and not instance.resolvido
        )
        if vai_resolver:
            _assert_roles(request.user, {request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE})
        mentions_ids = serializer.validated_data.pop("mentions", None)
        comentario = serializer.save()
        if mentions_ids is not None:
            usuarios = get_user_model().objects.filter(id__in=mentions_ids, cliente_id=comentario.cliente_id)
            comentario.mentions.set(usuarios)
        if vai_resolver:
            comentario.resolvido_por = request.user
            comentario.resolved_at = timezone.now()
            comentario.save(update_fields=["resolvido", "resolvido_por", "resolved_at", "updated_at"])
            evento = "comment:resolved"
            payload = {"comentario_id": comentario.id, "resolvido": True}
        else:
            evento = "comment:updated"
            payload = {"comentario_id": comentario.id, "conteudo_html": comentario.conteudo_html}
        broadcast_stream_event(comentario.alvo_tipo, comentario.alvo_id, evento, payload)
        serializer = self.get_serializer(comentario)
        response = Response(serializer.data)
        response["ETag"] = comentario.etag
        return response


class NotificacaoViewSet(FeatureFlagMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificacaoSerializer
    permission_classes = [HasClientScope]
    feature_flag = "ff.notifications.enabled"

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        return Notificacao.objects.filter(cliente_id=cliente_id, usuario=self.request.user)

    @action(detail=True, methods=["put"], url_path="lida")
    def marcar_lida(self, request, pk=None):
        notificacao = self.get_object()
        notificacao.lida = True
        notificacao.save(update_fields=["lida", "updated_at"])
        serializer = self.get_serializer(notificacao)
        return Response(serializer.data)


class MebThreadViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = MebThreadSerializer
    permission_classes = [HasClientScope]
    filter_backends = [filters.SearchFilter]
    search_fields = ("usuario__nome", "usuario__email")
    pagination_class = None

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = (
            MebThread.objects.filter(cliente_id=cliente_id)
            .select_related("usuario")
        )
        last_message = MebMessage.objects.filter(thread=OuterRef("pk")).order_by("-created_at")
        queryset = queryset.annotate(
            last_message_text=Subquery(last_message.values("conteudo")[:1]),
            last_message_origin=Subquery(last_message.values("origem")[:1]),
            last_message_at=Subquery(last_message.values("created_at")[:1]),
            total_messages=Count("messages"),
        )
        if not self._user_can_manage():
            queryset = queryset.filter(usuario=self.request.user)
        return queryset.order_by("-updated_at")

    def _user_can_manage(self) -> bool:
        user = self.request.user
        return getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        if not getattr(request.user, "cliente_id", None):
            raise ValidationError("Usuário sem cliente não pode iniciar o chat do MEB.")
        thread = ensure_thread_for_user(request.user, _get_request_cliente_id(request))
        serializer = self.get_serializer(thread)
        return Response(serializer.data)


class MebMessageViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = MebMessageSerializer
    permission_classes = [HasClientScope]
    pagination_class = None

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = (
            MebMessage.objects.filter(cliente_id=cliente_id)
            .select_related("autor", "thread", "thread__usuario")
            .order_by("created_at", "id")
        )
        usuario_param = self.request.query_params.get("usuario_id")
        if usuario_param:
            try:
                usuario_id = int(usuario_param)
            except (TypeError, ValueError):
                raise ValidationError({"usuario_id": "Informe um identificador numérico."})
            if not self._user_can_manage():
                raise PermissionDenied("Somente administradores podem consultar outros usuários.")
            return queryset.filter(thread__usuario_id=usuario_id)
        return queryset.filter(thread__usuario=self.request.user)

    def list(self, request, *args, **kwargs):
        if not request.query_params.get("usuario_id"):
            try:
                ensure_thread_for_user(request.user, _get_request_cliente_id(request))
            except ValueError:
                pass
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        message = serializer.save()
        if message.origem == MebMessage.Origem.CLIENTE:
            auto_reply_for_message(message.thread, message.conteudo)

    @action(detail=False, methods=["post"], url_path="broadcast")
    def broadcast(self, request):
        if not self._user_can_manage():
            raise PermissionDenied("Somente administradores podem enviar notificações em massa.")

        conteudo = str(request.data.get("conteudo") or "").strip()
        if not conteudo:
            raise ValidationError({"conteudo": "Digite uma mensagem para enviar no chat."})

        def parse_ids(raw_value):
            if raw_value is None:
                return []
            if isinstance(raw_value, str):
                raw_value = [value.strip() for value in raw_value.split(",") if value.strip()]
            if not isinstance(raw_value, (list, tuple, set)):
                return []
            parsed = []
            for item in raw_value:
                try:
                    parsed.append(int(item))
                except (TypeError, ValueError):
                    continue
            return parsed

        usuario_ids = parse_ids(request.data.get("usuarios") or request.data.get("usuario_ids"))
        gt_ids = parse_ids(request.data.get("gts") or request.data.get("gt_ids"))

        alcance = str(request.data.get("alcance") or "").lower()
        include_all = alcance in {"cliente", "secretaria", "all"} or bool(
            request.data.get("toda_secretaria")
        )

        if not include_all and not usuario_ids and not gt_ids:
            raise ValidationError("Escolha ao menos um usuário ou GT para enviar a mensagem.")

        cliente_id = _get_request_cliente_id(request)
        enviados = deliver_admin_broadcast(
            cliente_id=cliente_id,
            autor=request.user,
            conteudo=conteudo,
            usuario_ids=usuario_ids,
            gt_ids=gt_ids,
            include_all=include_all,
        )

        if enviados == 0:
            raise ValidationError("Nenhum destinatário elegível encontrado para este aviso.")

        return Response({"sent": enviados}, status=status.HTTP_201_CREATED)

    def _user_can_manage(self) -> bool:
        user = self.request.user
        return getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}


class MidiaViewSet(FeatureFlagMixin, viewsets.ModelViewSet):
    serializer_class = MidiaSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    feature_flag = "ff.library.enabled"
    throttle_scope = "library-write"

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Midia.objects.filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            gt_ids = _get_user_gt_ids(user)
            queryset = queryset.filter(models.Q(gt_id__in=gt_ids) | models.Q(gt__isnull=True))
        query = self.request.query_params.get("query")
        if query:
            queryset = queryset.filter(models.Q(url__icontains=query) | models.Q(legenda__icontains=query))
        tags = self.request.query_params.getlist("tags") or self.request.query_params.get("tags")
        if tags:
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            tags_set = set(tags)
            items = list(queryset)
            matches = [item.id for item in items if tags_set.issubset(set(item.tags or []))]
            queryset = queryset.filter(id__in=matches)
        gt_id = self.request.query_params.get("gt_id") or self.request.query_params.get("gt")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        pergunta_id = self.request.query_params.get("pergunta_id") or self.request.query_params.get("pergunta")
        if pergunta_id:
            queryset = queryset.filter(pergunta_id=pergunta_id)
        return queryset.order_by("-created_at")

    def _validate_biblioteca_relations(self, gt_id, pergunta_id):
        cliente_id = _get_request_cliente_id(self.request)
        if gt_id:
            gt = GT.objects.filter(pk=gt_id, cliente_id=cliente_id).first()
            if not gt:
                raise ValidationError({"gt": "GT inválido para este cliente."})
            if self.request.user.role not in {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN}:
                if not gt.membros.filter(pk=self.request.user.pk).exists():
                    raise PermissionDenied("GT não disponível para o usuário.")
        else:
            gt = None
        if pergunta_id:
            pergunta = Pergunta.objects.filter(pk=pergunta_id, cliente_id=cliente_id).first()
            if not pergunta:
                raise ValidationError({"pergunta": "Pergunta inválida para este cliente."})
            if gt and pergunta.gts.exists() and not pergunta.gts.filter(pk=gt.pk).exists():
                raise ValidationError({"pergunta": "Pergunta não associada ao GT selecionado."})

    def perform_create(self, serializer):
        _assert_roles(
            self.request.user,
            {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.ARTICULADOR},
        )
        gt_id = serializer.validated_data.get("gt_id") or getattr(serializer.validated_data.get("gt"), "id", None)
        pergunta_id = serializer.validated_data.get("pergunta_id") or getattr(
            serializer.validated_data.get("pergunta"), "id", None
        )
        if self.request.user.role not in {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN}:
            if not gt_id:
                raise ValidationError({"gt": "Selecione um GT para vincular a referência."})
        self._validate_biblioteca_relations(gt_id, pergunta_id)
        serializer.save(cliente_id=_get_request_cliente_id(self.request), uploaded_by=self.request.user)

    def perform_update(self, serializer):
        _assert_roles(
            self.request.user,
            {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.ARTICULADOR},
        )
        gt_id = serializer.validated_data.get("gt_id") or getattr(serializer.validated_data.get("gt"), "id", None)
        pergunta_id = serializer.validated_data.get("pergunta_id") or getattr(
            serializer.validated_data.get("pergunta"), "id", None
        )
        if self.request.user.role not in {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN}:
            gt_id = gt_id or getattr(serializer.instance.gt, "id", None)
            if not gt_id:
                raise ValidationError({"gt": "Selecione um GT para vincular a referência."})
        self._validate_biblioteca_relations(gt_id, pergunta_id)
        serializer.save()

    def perform_destroy(self, instance):
        _assert_roles(
            self.request.user,
            {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.ARTICULADOR},
        )
        instance.delete()


class BlocoTextoViewSet(FeatureFlagMixin, viewsets.ModelViewSet):
    serializer_class = BlocoTextoSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    feature_flag = "ff.library.enabled"
    throttle_scope = "library-write"

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = BlocoTexto.objects.filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            gt_ids = _get_user_gt_ids(user)
            queryset = queryset.filter(models.Q(gt_id__in=gt_ids) | models.Q(gt__isnull=True))
        query = self.request.query_params.get("query")
        if query:
            queryset = queryset.filter(models.Q(titulo__icontains=query) | models.Q(conteudo_html__icontains=query))
        tags = self.request.query_params.getlist("tags") or self.request.query_params.get("tags")
        if tags:
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            tags_set = set(tags)
            items = list(queryset)
            matches = [item.id for item in items if tags_set.issubset(set(item.tags or []))]
            queryset = queryset.filter(id__in=matches)
        gt_id = self.request.query_params.get("gt_id") or self.request.query_params.get("gt")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        pergunta_id = self.request.query_params.get("pergunta_id") or self.request.query_params.get("pergunta")
        if pergunta_id:
            queryset = queryset.filter(pergunta_id=pergunta_id)
        return queryset

    def _validate_biblioteca_relations(self, gt_id, pergunta_id):
        cliente_id = _get_request_cliente_id(self.request)
        if gt_id:
            gt = GT.objects.filter(pk=gt_id, cliente_id=cliente_id).first()
            if not gt:
                raise ValidationError({"gt": "GT inválido para este cliente."})
            if self.request.user.role not in {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN}:
                if not gt.membros.filter(pk=self.request.user.pk).exists():
                    raise PermissionDenied("GT não disponível para o usuário.")
        else:
            gt = None
        if pergunta_id:
            pergunta = Pergunta.objects.filter(pk=pergunta_id, cliente_id=cliente_id).first()
            if not pergunta:
                raise ValidationError({"pergunta": "Pergunta inválida para este cliente."})
            if gt and pergunta.gts.exists() and not pergunta.gts.filter(pk=gt.pk).exists():
                raise ValidationError({"pergunta": "Pergunta não associada ao GT selecionado."})

    def perform_create(self, serializer):
        _assert_roles(
            self.request.user,
            {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.ARTICULADOR},
        )
        gt_id = serializer.validated_data.get("gt_id") or getattr(serializer.validated_data.get("gt"), "id", None)
        pergunta_id = serializer.validated_data.get("pergunta_id") or getattr(
            serializer.validated_data.get("pergunta"), "id", None
        )
        if self.request.user.role not in {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.SUPER_ADMIN}:
            if not gt_id:
                raise ValidationError({"gt": "Selecione um GT para vincular a referência."})
        self._validate_biblioteca_relations(gt_id, pergunta_id)
        bloco = serializer.save(cliente_id=_get_request_cliente_id(self.request), created_by=self.request.user)
        self._created_instance = bloco

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = getattr(self, "_created_instance", None)
        if instance:
            response["ETag"] = instance.etag
        return response

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        _assert_roles(request.user, {request.user.Role.ADMIN_CLIENTE, request.user.Role.ARTICULADOR})
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        gt_id = serializer.validated_data.get("gt_id") or getattr(serializer.validated_data.get("gt"), "id", None)
        pergunta_id = serializer.validated_data.get("pergunta_id") or getattr(
            serializer.validated_data.get("pergunta"), "id", None
        )
        if request.user.role not in {request.user.Role.ADMIN_CLIENTE, request.user.Role.SUPER_ADMIN}:
            gt_id = gt_id or getattr(instance.gt, "id", None)
            if not gt_id:
                raise ValidationError({"gt": "Selecione um GT para vincular a referência."})
        self._validate_biblioteca_relations(gt_id, pergunta_id)
        serializer.save()
        response = Response(serializer.data)
        response["ETag"] = serializer.instance.etag
        return response

    def perform_destroy(self, instance):
        _assert_roles(
            self.request.user,
            {self.request.user.Role.ADMIN_CLIENTE, self.request.user.Role.ARTICULADOR},
        )
        instance.delete()


class DiffView(FeatureFlagMixin, APIView):
    feature_flag = "ff.diff.enabled"
    permission_classes = [HasClientScope]

    def get(self, request):
        alvo_tipo = request.query_params.get("alvo_tipo")
        alvo_id = request.query_params.get("alvo_id")
        from_version = request.query_params.get("from")
        to_version = request.query_params.get("to")
        if not all([alvo_tipo, alvo_id, from_version, to_version]):
            raise ValidationError("Informe alvo_tipo, alvo_id, from e to")
        html = build_diff(alvo_tipo, alvo_id, int(from_version), int(to_version))
        serializer = DiffResponseSerializer({"html": html})
        return Response(serializer.data)
