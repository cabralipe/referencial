"""Viewsets da API v1."""

from __future__ import annotations

import logging
from django.contrib.auth import get_user_model
from django.db import models, transaction
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
from core.models import AuditLog, Cliente, UserSessionLog
from core.permissions import (
    HasClientScope,
    IsAdminClienteOrReadOnly,
    IsArticuladorForGT,
    IsMemberOfGT,
)
from core.utils import coletar_contexto_do_cliente, verificar_flag
from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from curriculum.models import Anexo, GT, Resposta, Tarefa, TextoColaborativo, TextoUnico
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
    CampoDinamicoSerializer,
    ClienteMeSerializer,
    OnlineUserSerializer,
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
            user.Role.ARTICULADOR,
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


class TarefaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TarefaSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("tipo", "status")

    def get_queryset(self):
        queryset = Tarefa.objects.all().order_by("ordem")
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
        queryset = TextoUnico.objects.select_related("gt", "tarefa")
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
        queryset = Quadro.objects.select_related("gt")
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


class FormularioDinamicoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FormularioDinamicoSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        return FormularioDinamico.objects.filter(ativo=True)

    @action(detail=True, methods=["get"], url_path="campos")
    def campos(self, request, pk=None):
        formulario = self.get_object()
        serializer = CampoDinamicoSerializer(formulario.campos.order_by("ordem"), many=True)
        return Response(serializer.data)

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
        queryset = ExportJob.objects.all()
        alvo_tipo = self.request.query_params.get("alvo_tipo")
        alvo_id = self.request.query_params.get("alvo_id")
        if alvo_tipo:
            queryset = queryset.filter(alvo_tipo=alvo_tipo)
        if alvo_id:
            queryset = queryset.filter(alvo_id=str(alvo_id))
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
        return Revisao.objects.filter(cliente_id=cliente_id)

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
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE})
        serializer.save(cliente_id=_get_request_cliente_id(self.request), uploaded_by=self.request.user)

    def perform_update(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE})
        serializer.save()

    def perform_destroy(self, instance):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE})
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
        return queryset

    def perform_create(self, serializer):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE})
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
        _assert_roles(request.user, {request.user.Role.ADMIN_CLIENTE})
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(serializer.data)
        response["ETag"] = serializer.instance.etag
        return response

    def perform_destroy(self, instance):
        _assert_roles(self.request.user, {self.request.user.Role.ADMIN_CLIENTE})
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
