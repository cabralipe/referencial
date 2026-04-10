"""Viewsets da API v1."""

from __future__ import annotations

import json
import logging
import os
from uuid import uuid4
from django.utils.html import escape
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
from core.models import AuditLog, Cliente, ClienteConfig, ScoreEntry, ThrottleBlock, TipoUsuarioCadastro, UserSessionLog
from core.permissions import (
    CanManageMural,
    HasClientScope,
    IsAdminClienteOrReadOnly,
    IsArticuladorForGT,
    IsMemberOfGT,
)
from core.scope import resolve_cliente_scope
from core.utils import coletar_contexto_do_cliente, obter_config, verificar_flag, usuario_e_membro_do_gt
from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from curriculum.models import Area, Anexo, Escola, GT, PPP, Pergunta, Resposta, Tarefa, TextoColaborativo, TextoUnico
from curriculum.services.collab_sync import broadcast_texto_colaborativo, sync_texto_colaborativo_from_resposta
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from notifications.services import criar_notificacao
from meb.models import MebMessage, MebThread
from meb.services import auto_reply_for_message, deliver_admin_broadcast, ensure_thread_for_user
from reviews.models import Revisao, ReviewDecision
from services.reviewer_scope import get_reviewer_queryset
from sockets.utils import broadcast_stream_event
from django.http import HttpResponse
from core.plugins import get_export_provider
from diffs.services import build_diff
from tasks.exports import enqueue_export_job, build_export_context
from tasks.synthesis import enqueue_texto_unico
from workshop.models import CelulaQuadro, Quadro
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from exports.services.pdf import html_to_pdf_bytes

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
    AreaSerializer,
    EscolaSerializer,
    PppSerializer,
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
    MuralPostCreateSerializer,
    MuralPostSerializer,
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
    cliente_id = resolve_cliente_scope(request)
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


def _get_requested_gt_id(request) -> int | None:
    raw_gt_id = request.query_params.get("gt_id") or request.query_params.get("gt")
    if raw_gt_id in {None, ""}:
        return None
    try:
        return int(raw_gt_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError("gt_id inválido.") from exc


def _validate_gt_access(request, gt_id: int) -> None:
    cliente_id = _get_request_cliente_id(request)
    gt = GT.objects.filter(cliente_id=cliente_id, pk=gt_id).only("id").first()
    if not gt:
        raise ValidationError("GT não encontrado para este cliente.")
    if not usuario_e_membro_do_gt(request.user, gt_id):
        raise PermissionDenied("GT não disponível para o usuário.")


def _filtrar_perguntas_por_usuario(queryset, user):
    role = getattr(user, "role", None)
    if role in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
        user_gt_ids = _get_user_gt_ids(user)
        if not user_gt_ids:
            return queryset.none()
        if role == user.Role.MEMBRO_GT:
            queryset = queryset.filter(gts__id__in=user_gt_ids).distinct()
        else:
            queryset = queryset.filter(
                models.Q(gts__id__in=user_gt_ids) | models.Q(gts__isnull=True)
            ).distinct()
    return queryset


def _filtrar_perguntas_por_gt(queryset, gt_id: int):
    return queryset.filter(
        models.Q(gts__id=gt_id) | models.Q(gts__isnull=True)
    ).distinct()


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


PPP_ALLOWED_VIEW_ROLES = {
    "diretor",
    "coordenador_pedagogico",
    "professor",
    "articulador",
    "admin_cliente",
    "super_admin",
}
PPP_ALLOWED_EDIT_ROLES = {
    "diretor",
    "coordenador_pedagogico",
    "articulador",
    "admin_cliente",
    "super_admin",
}
PPP_ALLOWED_CONCLUDE_ROLES = {
    "diretor",
    "coordenador_pedagogico",
    "admin_cliente",
    "super_admin",
}


def _resolve_ppp_escola_id(request, explicit_escola_id=None) -> int:
    user = request.user
    role = getattr(user, "role", None)
    if role not in PPP_ALLOWED_VIEW_ROLES:
        raise PermissionDenied("Seu perfil não possui acesso ao PPP.")

    if role in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
        escola_id = explicit_escola_id or request.query_params.get("escola_id") or request.data.get("escola_id")
        if not escola_id:
            raise ValidationError({"escola_id": "Informe a escola para acessar o PPP."})
        try:
            return int(escola_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"escola_id": "Informe um identificador numérico válido."}) from exc

    if not getattr(user, "escola_id", None):
        raise ValidationError("Usuário sem escola associada não pode acessar o PPP.")
    return int(user.escola_id)


def _get_user_tipo_cadastro(user):
    tipo_cadastro_id = getattr(user, "tipo_cadastro_id", None)
    if not tipo_cadastro_id:
        return None
    tipo_cadastro = getattr(user, "_cached_tipo_cadastro", None)
    if getattr(tipo_cadastro, "pk", None) == tipo_cadastro_id:
        return tipo_cadastro
    try:
        tipo_cadastro = user.tipo_cadastro
    except TipoUsuarioCadastro.DoesNotExist:
        tipo_cadastro = None
    if tipo_cadastro is None:
        tipo_cadastro = TipoUsuarioCadastro.raw_objects.filter(
            pk=tipo_cadastro_id,
            ativo=True,
            is_deleted=False,
        ).first()
    setattr(user, "_cached_tipo_cadastro", tipo_cadastro)
    return tipo_cadastro


def _user_can_manage_ppp_for_escola(user, escola_id: int) -> bool:
    role = getattr(user, "role", None)
    if role in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
        return True
    if getattr(user, "escola_id", None) != escola_id:
        return False
    tipo_cadastro = _get_user_tipo_cadastro(user)
    if tipo_cadastro is not None:
        return tipo_cadastro.acesso_ppp == TipoUsuarioCadastro.AcessoPPP.EDITAR
    return role in {
        user.Role.DIRETOR,
        user.Role.COORDENADOR_PEDAGOGICO,
        user.Role.ARTICULADOR,
    }


def _user_can_view_ppp_for_escola(user, escola_id: int) -> bool:
    role = getattr(user, "role", None)
    if role in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
        return True
    if getattr(user, "escola_id", None) != escola_id:
        return False
    tipo_cadastro = _get_user_tipo_cadastro(user)
    if tipo_cadastro is not None:
        return tipo_cadastro.acesso_ppp in {
            TipoUsuarioCadastro.AcessoPPP.EDITAR,
            TipoUsuarioCadastro.AcessoPPP.VISUALIZAR,
        }
    return role in PPP_ALLOWED_VIEW_ROLES


def _get_or_create_ppp_for_request(request, explicit_escola_id=None):
    cliente_id = _get_request_cliente_id(request)
    user = request.user
    escola_id = _resolve_ppp_escola_id(request, explicit_escola_id=explicit_escola_id)
    escola = Escola.objects.filter(cliente_id=cliente_id, pk=escola_id).first()
    if not escola:
        raise ValidationError({"escola_id": "Escola não encontrada para este cliente."})
    if not _user_can_manage_ppp_for_escola(user, escola.id):
        ppp = PPP.objects.filter(cliente_id=cliente_id, escola=escola).first()
        if not ppp or ppp.status != PPP.Status.CONCLUIDO:
            raise ValidationError("O PPP da sua escola ainda não foi concluído para visualização.")
        return ppp
    ppp, _ = PPP.objects.get_or_create(
        cliente_id=cliente_id,
        escola=escola,
        defaults={"titulo": f"Projeto Político-Pedagógico - {escola.nome}"},
    )
    return ppp


def _user_can_edit_ppp(user, ppp: PPP) -> bool:
    return _user_can_manage_ppp_for_escola(user, ppp.escola_id)


def _user_can_comment_ppp(user, ppp: PPP) -> bool:
    return _user_can_edit_ppp(user, ppp)


def _user_can_conclude_ppp(user, ppp: PPP) -> bool:
    return _user_can_manage_ppp_for_escola(user, ppp.escola_id)


def _serialize_ppp(serializer_class, ppp: PPP, user):
    permissions = {
        ppp.id: {
            "can_edit": _user_can_edit_ppp(user, ppp),
            "can_comment": _user_can_comment_ppp(user, ppp),
            "can_conclude": _user_can_conclude_ppp(user, ppp),
        }
    }
    return serializer_class(ppp, context={"ppp_permissions": permissions}).data


def _serialize_ppp_unavailable(escola: Escola, message: str, ppp: PPP | None = None):
    return {
        "id": None,
        "escola": escola.id,
        "escola_nome": escola.nome,
        "titulo": "",
        "conteudo_html": "",
        "status": getattr(ppp, "status", PPP.Status.EM_ELABORACAO),
        "ultima_edicao_por": None,
        "ultima_edicao_por_nome": None,
        "concluido_por": None,
        "concluido_por_nome": None,
        "concluido_em": None,
        "version": getattr(ppp, "version", 0),
        "updated_at": getattr(ppp, "updated_at", None),
        "etag": "",
        "can_edit": False,
        "can_comment": False,
        "can_conclude": False,
        "comentarios_abertos": 0,
        "is_available": False,
        "availability_message": message,
    }


SCORE_CONFIG_KEY = "score.config"
DEFAULT_SCORE_CONFIG = {
    "monthly_limit": 300,
    "default_points": 10,
    "tarefa_points": {},
}

PPP_CONFIG_KEY = "ppp.trilhas"
DEFAULT_PPP_CONFIG = {
    "tarefa_ids": [],
    "descricao": "",
}

MURAL_NOTIFICATION_TYPE = "mural_post"


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


def _normalize_ppp_config(payload):
    config = {
        "tarefa_ids": [],
        "descricao": DEFAULT_PPP_CONFIG["descricao"],
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
        tarefa_ids = raw.get("tarefa_ids") or []
        descricao = raw.get("descricao")
        if isinstance(tarefa_ids, (list, tuple)):
            normalized = []
            for item in tarefa_ids:
                try:
                    valor = int(item)
                except (TypeError, ValueError):
                    continue
                normalized.append(valor)
            config["tarefa_ids"] = sorted(set(normalized))
        if isinstance(descricao, str):
            config["descricao"] = descricao.strip()
    return config


def _get_ppp_config(cliente_id: int):
    cliente = Cliente.objects.filter(pk=cliente_id).first()
    if not cliente:
        return _normalize_ppp_config(None)
    raw = obter_config(cliente, PPP_CONFIG_KEY)
    return _normalize_ppp_config(raw)


def _save_ppp_config(cliente_id: int, payload):
    config = _normalize_ppp_config(payload)
    ClienteConfig.raw_objects.update_or_create(
        cliente_id=cliente_id,
        chave=PPP_CONFIG_KEY,
        defaults={
            "valor_texto": json.dumps(config, ensure_ascii=True),
            "is_deleted": False,
        },
    )
    return config


def _filtrar_tarefas_por_usuario(queryset, user):
    role = getattr(user, "role", None)
    if role in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
        user_gt_ids = _get_user_gt_ids(user)
        if not user_gt_ids:
            return queryset.none()
        if role == user.Role.MEMBRO_GT:
            queryset = queryset.filter(perguntas__gts__id__in=user_gt_ids).distinct()
        else:
            queryset = queryset.filter(
                models.Q(perguntas__gts__id__in=user_gt_ids)
                | models.Q(perguntas__gts__isnull=True)
                | models.Q(perguntas__isnull=True)
            ).distinct()
    return queryset


def _filtrar_tarefas_por_gt(queryset, gt_id: int):
    return queryset.filter(
        models.Q(perguntas__gts__id=gt_id)
        | models.Q(perguntas__gts__isnull=True)
        | models.Q(perguntas__isnull=True)
    ).distinct()


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


class PppViewSet(viewsets.ViewSet):
    permission_classes = [HasClientScope]

    def list(self, request):
        cliente_id = _get_request_cliente_id(request)
        escola_id = _resolve_ppp_escola_id(request)
        escola = Escola.objects.filter(cliente_id=cliente_id, pk=escola_id).first()
        if not escola:
            raise ValidationError({"escola_id": "Escola nÃ£o encontrada para este cliente."})
        if not _user_can_manage_ppp_for_escola(request.user, escola.id):
            ppp = PPP.objects.filter(cliente_id=cliente_id, escola=escola).first()
            if not ppp or ppp.status != PPP.Status.CONCLUIDO:
                return Response(
                    _serialize_ppp_unavailable(
                        escola,
                        "O PPP da sua escola ainda não foi concluído para visualização.",
                        ppp=ppp,
                    )
                )
        ppp = _get_or_create_ppp_for_request(request)
        data = _serialize_ppp(PppSerializer, ppp, request.user)
        comentarios_abertos = Comentario.objects.filter(
            cliente_id=ppp.cliente_id,
            alvo_tipo=Comentario.AlvoTipo.PPP,
            alvo_id=str(ppp.id),
            resolvido=False,
        ).count()
        data["comentarios_abertos"] = comentarios_abertos
        response = Response(data)
        response["ETag"] = ppp.etag
        return response

    @action(detail=False, methods=["get"], url_path="overview")
    def overview(self, request):
        user = request.user
        cliente_id = _get_request_cliente_id(request)
        if getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            raise PermissionDenied("Somente administradores podem consultar o panorama do PPP.")

        escolas = Escola.objects.filter(cliente_id=cliente_id).order_by("nome")
        ppps = PPP.objects.filter(cliente_id=cliente_id).select_related("escola")
        ppp_map = {ppp.escola_id: ppp for ppp in ppps}
        comentarios = (
            Comentario.objects.filter(cliente_id=cliente_id, alvo_tipo=Comentario.AlvoTipo.PPP, resolvido=False)
            .values("alvo_id")
            .annotate(total=models.Count("id"))
        )
        comentarios_map = {int(item["alvo_id"]): item["total"] for item in comentarios if str(item["alvo_id"]).isdigit()}

        payload = []
        for escola in escolas:
            ppp = ppp_map.get(escola.id)
            payload.append(
                {
                    "escola_id": escola.id,
                    "escola_nome": escola.nome,
                    "ppp_id": getattr(ppp, "id", None),
                    "status": getattr(ppp, "status", PPP.Status.EM_ELABORACAO),
                    "updated_at": getattr(ppp, "updated_at", None),
                    "comentarios_abertos": comentarios_map.get(getattr(ppp, "id", 0), 0),
                }
            )
        return Response(payload)

    @action(detail=False, methods=["patch"], url_path="conteudo")
    def conteudo(self, request):
        ppp = _get_or_create_ppp_for_request(request)
        if not _user_can_edit_ppp(request.user, ppp):
            raise PermissionDenied("Seu perfil não pode editar este PPP.")

        _check_etag(request, ppp)
        conteudo_html = request.data.get("conteudo_html")
        titulo = request.data.get("titulo")
        if conteudo_html is None:
            raise ValidationError({"conteudo_html": "Informe o conteúdo do PPP."})

        ppp.conteudo_html = str(conteudo_html)
        if isinstance(titulo, str) and titulo.strip():
            ppp.titulo = titulo.strip()
        if ppp.status == PPP.Status.CONCLUIDO:
            ppp.status = PPP.Status.EM_ELABORACAO
            ppp.concluido_por = None
            ppp.concluido_em = None
        ppp.ultima_edicao_por = request.user
        ppp.save(
            update_fields=[
                "conteudo_html",
                "titulo",
                "status",
                "concluido_por",
                "concluido_em",
                "ultima_edicao_por",
                "updated_at",
            ]
        )
        response = Response(_serialize_ppp(PppSerializer, ppp, request.user))
        response["ETag"] = ppp.etag
        return response

    @action(detail=False, methods=["post"], url_path="concluir")
    def concluir(self, request):
        ppp = _get_or_create_ppp_for_request(request)
        if not _user_can_conclude_ppp(request.user, ppp):
            raise PermissionDenied("Somente Diretor ou Coordenador Pedagógico podem concluir o PPP.")
        _check_etag(request, ppp)
        if not (ppp.conteudo_html or "").strip():
            raise ValidationError({"conteudo_html": "Preencha o texto do PPP antes de concluir."})

        ppp.status = PPP.Status.CONCLUIDO
        ppp.concluido_por = request.user
        ppp.concluido_em = timezone.now()
        ppp.ultima_edicao_por = request.user
        ppp.save(update_fields=["status", "concluido_por", "concluido_em", "ultima_edicao_por", "updated_at"])
        response = Response(_serialize_ppp(PppSerializer, ppp, request.user))
        response["ETag"] = ppp.etag
        return response

    @action(detail=False, methods=["get"], url_path="pdf")
    def pdf(self, request):
        ppp = _get_or_create_ppp_for_request(request)
        if not _user_can_comment_ppp(request.user, ppp):
            raise PermissionDenied("Seu perfil não pode acessar este PPP.")
        if ppp.status != PPP.Status.CONCLUIDO:
            raise ValidationError("Conclua o PPP antes de gerar o PDF.")

        file_bytes = html_to_pdf_bytes(
            "ppp_pdf.html",
            {
                "ppp": ppp,
                "escola": ppp.escola,
                "cliente": ppp.cliente,
                "generated_at": timezone.localtime(timezone.now()),
            },
        )
        filename = f"ppp-{ppp.escola.nome.lower().replace(' ', '-')}.pdf"
        response = HttpResponse(file_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

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


class EscolaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EscolaSerializer
    permission_classes = [HasClientScope]
    filter_backends = [filters.SearchFilter]
    search_fields = ("nome",)

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        return Escola.objects.filter(cliente_id=cliente_id).order_by("nome")


class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AreaSerializer
    permission_classes = [HasClientScope]
    filter_backends = [filters.SearchFilter]
    search_fields = ("nome",)

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Area.objects.filter(cliente_id=cliente_id).order_by("nome")
        user = self.request.user
        if not getattr(user, "is_authenticated", False):
            return queryset.none()
        if getattr(user, "role", None) in {
            user.Role.ADMIN_CLIENTE,
            user.Role.SUPER_ADMIN,
        }:
            return queryset.prefetch_related("gts")
        gt_ids = _get_user_gt_ids(user)
        if not gt_ids:
            return queryset.none()
        return queryset.filter(gts__id__in=gt_ids).distinct().prefetch_related("gts")


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
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Tarefa.objects.filter(cliente_id=cliente_id).order_by("ordem")
        user = self.request.user
        queryset = _filtrar_tarefas_por_usuario(queryset, user)
        etapa = self.request.query_params.get("etapa")
        gt_id = _get_requested_gt_id(self.request)
        if etapa:
            queryset = queryset.filter(etapa=etapa)
        if gt_id:
            _validate_gt_access(self.request, gt_id)
            queryset = _filtrar_tarefas_por_gt(queryset, gt_id)
        return queryset

    @action(detail=True, methods=["get"], url_path="perguntas")
    def perguntas(self, request, pk=None):
        tarefa = self.get_object()
        perguntas = tarefa.perguntas.all()
        perguntas = _filtrar_perguntas_por_usuario(perguntas, request.user)
        gt_id = _get_requested_gt_id(request)
        if gt_id:
            _validate_gt_access(request, gt_id)
            perguntas = _filtrar_perguntas_por_gt(perguntas, gt_id)
        perguntas = perguntas.order_by("ordem")
        serializer = PerguntaSerializer(perguntas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="progresso")
    def progresso(self, request, pk=None):
        tarefa = self.get_object()
        gt_id = request.query_params.get("gt_id") or request.query_params.get("gt")
        if not gt_id:
            raise ValidationError("Informe gt_id para calcular o progresso da trilha.")
        try:
            gt_id_int = int(gt_id)
        except (TypeError, ValueError):
            raise ValidationError("gt_id inválido.")
        if not usuario_e_membro_do_gt(request.user, gt_id_int):
            raise PermissionDenied("GT não disponível para o usuário.")

        perguntas = list(tarefa.perguntas.order_by("ordem"))
        perguntas_filtradas = []
        for pergunta in perguntas:
            if pergunta.gts.exists() and not pergunta.gts.filter(pk=gt_id_int).exists():
                continue
            perguntas_filtradas.append(pergunta)

        respostas = Resposta.objects.filter(
            gt_id=gt_id_int,
            pergunta_id__in=[p.id for p in perguntas_filtradas],
        )
        respostas_map = {resp.pergunta_id: resp for resp in respostas}
        revisoes = Revisao.objects.filter(
            cliente_id=_get_request_cliente_id(request),
            alvo_tipo=Revisao.AlvoTipo.RESPOSTA,
            alvo_id__in=[str(resp.id) for resp in respostas],
        ).order_by("-updated_at")
        revisao_map = {}
        for rev in revisoes:
            if rev.alvo_id not in revisao_map:
                revisao_map[rev.alvo_id] = rev

        blocos = []
        respondidos = 0
        aprovados = 0
        em_revisao = 0
        devolvidos = 0
        for pergunta in perguntas_filtradas:
            resposta = respostas_map.get(pergunta.id)
            resposta_id = getattr(resposta, "id", None)
            revisao = revisao_map.get(str(resposta_id)) if resposta_id else None
            status_bloco = "nao_iniciado"
            if revisao:
                if revisao.status == Revisao.Status.REPROVADO:
                    status_bloco = "devolvido"
                    devolvidos += 1
                elif revisao.status == Revisao.Status.APROVADO:
                    status_bloco = "concluido"
                    aprovados += 1
                elif revisao.status == Revisao.Status.EM_REVISAO:
                    status_bloco = "em_revisao"
                    em_revisao += 1
            if status_bloco == "nao_iniciado":
                if resposta and (resposta.conteudo_html or "").strip():
                    status_bloco = "em_andamento"
            if resposta and (resposta.conteudo_html or "").strip():
                respondidos += 1

            blocos.append(
                {
                    "pergunta_id": pergunta.id,
                    "pergunta_ordem": pergunta.ordem,
                    "pergunta_texto": pergunta.texto,
                    "resposta_id": resposta_id,
                    "status": status_bloco,
                    "atualizado_em": getattr(resposta, "updated_at", None),
                }
            )

        total = len(perguntas_filtradas)
        if devolvidos:
            status_trilha = "devolvido"
        elif em_revisao:
            status_trilha = "em_revisao"
        elif total and aprovados == total:
            status_trilha = "concluido"
        elif respondidos:
            status_trilha = "em_andamento"
        else:
            status_trilha = "nao_iniciado"

        percentual = (respondidos / total) if total else 0
        return Response(
            {
                "tarefa_id": tarefa.id,
                "gt_id": gt_id_int,
                "total_blocos": total,
                "respondidos": respondidos,
                "aprovados": aprovados,
                "em_revisao": em_revisao,
                "devolvidos": devolvidos,
                "status": status_trilha,
                "percentual": percentual,
                "blocos": blocos,
            }
        )

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
        queryset = _filtrar_perguntas_por_usuario(queryset, self.request.user)
        gt_id = _get_requested_gt_id(self.request)
        if gt_id:
            _validate_gt_access(self.request, gt_id)
            queryset = _filtrar_perguntas_por_gt(queryset, gt_id)
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
        return queryset.order_by("pergunta__ordem", "id")

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
        queryset = Quadro.objects.select_related("gt").prefetch_related("linhas", "colunas", "celulas").filter(cliente_id=cliente_id)
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.MEMBRO_GT, user.Role.ARTICULADOR}:
            gt_ids = _get_user_gt_ids(user)
            if not gt_ids:
                return queryset.none()
            queryset = queryset.filter(gt_id__in=gt_ids)
        area_id = self.request.query_params.get("area_id")
        gt_id = self.request.query_params.get("gt_id")
        template = self.request.query_params.get("template")
        if area_id:
            try:
                Area.objects.get(pk=area_id, cliente_id=cliente_id)
            except Area.DoesNotExist as exc:
                raise ValidationError("Área não encontrada.") from exc
            queryset = queryset.filter(area_id=area_id)
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
            | models.Q(alvo_tipo=ExportJob.AlvoTipo.RELATORIO)
        )
        return queryset


    def perform_create(self, serializer):
        cliente_id = _get_request_cliente_id(self.request)
        job = serializer.save(cliente_id=cliente_id)
        enqueue_export_job(job.id)

    @action(detail=False, methods=["post"], url_path="download")
    def download(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cliente_id = _get_request_cliente_id(self.request)
        # Cria o job mas marca como processando
        job = serializer.save(cliente_id=cliente_id, status=ExportJob.Status.RUNNING)

        try:
            # Lógica síncrona de geração (reusando serviços existentes)
            context = build_export_context(job)
            plugin_name = obter_config(job.cliente, "export_plugin")
            provider = get_export_provider(plugin_name)

            if job.formato == ExportJob.Formato.PDF:
                file_bytes = provider.render_pdf(context.payload)
                ext = "pdf"
                content_type = "application/pdf"
            else:
                file_bytes = provider.render_docx(context.payload)
                ext = "docx"
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            filename = f"export_{job.id}.{ext}"
            
            # Salva histórico no storage (padrão do sistema)
            saved_path = default_storage.save(f"exports/{job.id}.{ext}", ContentFile(file_bytes))
            job.url_resultado = default_storage.url(saved_path)
            job.status = ExportJob.Status.DONE
            job.finished_at = timezone.now()
            job.save()

            # Retorna o arquivo diretamente
            response = HttpResponse(file_bytes, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["X-Export-Job-Id"] = str(job.id)
            return response

        except Exception as exc:
            job.status = ExportJob.Status.ERROR
            job.save()
            logger.exception(f"Erro no download síncrono do job {job.id}")
            raise ValidationError("Falha ao gerar o arquivo. Tente novamente ou use a exportação assíncrona.") from exc



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
        elif getattr(user, "role", None) == user.Role.MEMBRO_GT:
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
        elif getattr(user, "role", None) == user.Role.REVISOR:
            queryset = get_reviewer_queryset(user)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        _assert_roles(user, {user.Role.MEMBRO_GT, user.Role.ARTICULADOR, user.Role.ADMIN_CLIENTE})
        if user.role == user.Role.MEMBRO_GT:
            alvo_tipo = serializer.validated_data.get("alvo_tipo")
            alvo_id = serializer.validated_data.get("alvo_id")
            if alvo_tipo == Revisao.AlvoTipo.RESPOSTA:
                resposta = Resposta.objects.select_related("gt").filter(pk=alvo_id).first()
                if not resposta or not usuario_e_membro_do_gt(user, resposta.gt_id):
                    raise PermissionDenied("GT não disponível para o usuário.")
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

    @action(detail=True, methods=["post"], url_path="decisao")
    def decisao(self, request, pk=None):
        revisao = self.get_object()
        _assert_roles(request.user, {request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE})
        _check_etag(request, revisao)

        decision = (request.data.get("decision") or "").lower()
        note = request.data.get("note") or ""
        checklist = request.data.get("checklist") or []
        if decision not in {"approve", "return"}:
            raise ValidationError({"decision": "Informe approve ou return."})
        if checklist and not isinstance(checklist, list):
            raise ValidationError({"checklist": "Checklist deve ser uma lista."})

        status = Revisao.Status.APROVADO if decision == "approve" else Revisao.Status.REPROVADO
        checklist_html = ""
        if checklist:
            items = "".join(f"<li>{escape(str(item))}</li>" for item in checklist)
            checklist_html = f"<ul>{items}</ul>"
        parecer_html = f"{checklist_html}<p>{escape(str(note))}</p>" if (checklist_html or note) else revisao.parecer_html

        old_status = revisao.status
        revisao.status = status
        if parecer_html is not None:
            revisao.parecer_html = parecer_html
        if not revisao.revisor or getattr(revisao.revisor, "role", None) != request.user.Role.REVISOR:
            revisao.revisor = request.user
        revisao.save(update_fields=["status", "parecer_html", "revisor", "updated_at"])

        ReviewDecision.objects.create(
            cliente_id=revisao.cliente_id,
            target_type=revisao.alvo_tipo,
            target_id=revisao.alvo_id,
            actor=request.user,
            actor_role=ReviewDecision.ActorRole.REDACTOR,
            decision_type=ReviewDecision.DecisionType.RECOMMEND_APPROVE if decision == "approve" else ReviewDecision.DecisionType.RECOMMEND_RETURN,
            checklist=checklist or [],
            note=note or "",
        )

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

        response = Response(self.get_serializer(revisao).data)
        response["ETag"] = revisao.etag
        return response

    @action(detail=True, methods=["post"], url_path="recommend")
    def recommend(self, request, pk=None):
        revisao = self.get_object()
        _assert_roles(request.user, {request.user.Role.REVISOR})

        decision = (request.data.get("decision") or "").lower()
        note = request.data.get("note") or ""
        checklist = request.data.get("checklist") or []
        if decision not in {"approve", "return", "minor"}:
            raise ValidationError({"decision": "Informe approve, return ou minor."})
        if checklist and not isinstance(checklist, list):
            raise ValidationError({"checklist": "Checklist deve ser uma lista."})

        decision_map = {
            "approve": ReviewDecision.DecisionType.RECOMMEND_APPROVE,
            "return": ReviewDecision.DecisionType.RECOMMEND_RETURN,
            "minor": ReviewDecision.DecisionType.RECOMMEND_MINOR,
        }

        recommendation = ReviewDecision.objects.create(
            cliente_id=revisao.cliente_id,
            target_type=revisao.alvo_tipo,
            target_id=revisao.alvo_id,
            actor=request.user,
            actor_role=ReviewDecision.ActorRole.REVIEWER,
            decision_type=decision_map[decision],
            checklist=checklist or [],
            note=note or "",
        )

        interessados = get_user_model().objects.filter(
            cliente_id=revisao.cliente_id,
            role__in=[request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE],
        )
        for interessado in interessados:
            criar_notificacao(
                cliente_id=revisao.cliente_id,
                usuario_id=interessado.id,
                tipo="revisao.reviewer_recommendation",
                payload={"revisao_id": revisao.id, "decision": recommendation.decision_type},
            )

        response = Response(self.get_serializer(revisao).data)
        response["ETag"] = revisao.etag
        return response

    @action(detail=True, methods=["post"], url_path="in-progress")
    def in_progress(self, request, pk=None):
        revisao = self.get_object()
        _assert_roles(request.user, {request.user.Role.REVISOR})

        ReviewDecision.objects.create(
            cliente_id=revisao.cliente_id,
            target_type=revisao.alvo_tipo,
            target_id=revisao.alvo_id,
            actor=request.user,
            actor_role=ReviewDecision.ActorRole.REVIEWER,
            decision_type=ReviewDecision.DecisionType.IN_PROGRESS,
        )
        response = Response(self.get_serializer(revisao).data)
        response["ETag"] = revisao.etag
        return response


class UsuarioLookupViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UsuarioLookupSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ("role",)
    search_fields = ("nome", "email")

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = get_user_model().objects.filter(cliente_id=cliente_id)
        q = self.request.query_params.get("q")
        if q:
            # SearchFilter will still apply; keeping explicit filter for non-standard setups
            queryset = queryset.filter(models.Q(nome__icontains=q) | models.Q(email__icontains=q))
        return queryset.order_by("nome", "id")

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


def _notificar_comentario_alvo(comentario, usuario):
    alvo_tipo = comentario.alvo_tipo
    alvo_id = comentario.alvo_id
    usuario_ids: set[int] = set()
    if alvo_tipo == Comentario.AlvoTipo.RESPOSTA:
        resposta = Resposta.objects.select_related("gt").filter(pk=alvo_id).first()
        if resposta:
            usuario_ids.update(resposta.gt.membros.values_list("id", flat=True))
    elif alvo_tipo == Comentario.AlvoTipo.TEXTO_UNICO:
        texto = TextoUnico.objects.select_related("gt").filter(pk=alvo_id).first()
        if texto:
            usuario_ids.update(texto.gt.membros.values_list("id", flat=True))
    elif alvo_tipo == Comentario.AlvoTipo.QUADRO:
        quadro = Quadro.objects.select_related("gt").filter(pk=alvo_id).first()
        if quadro:
            usuario_ids.update(quadro.gt.membros.values_list("id", flat=True))
    elif alvo_tipo == Comentario.AlvoTipo.PPP:
        ppp = PPP.objects.select_related("escola").filter(pk=alvo_id).first()
        if ppp:
            colaboradores = get_user_model().objects.filter(
                cliente_id=ppp.cliente_id,
                escola_id=ppp.escola_id,
                role__in=[
                    get_user_model().Role.DIRETOR,
                    get_user_model().Role.COORDENADOR_PEDAGOGICO,
                    get_user_model().Role.ARTICULADOR,
                ],
            )
            usuario_ids.update(colaboradores.values_list("id", flat=True))
    if usuario:
        usuario_ids.discard(usuario.id)
    for usuario_id in usuario_ids:
        criar_notificacao(
            cliente_id=comentario.cliente_id,
            usuario_id=usuario_id,
            tipo="comentario.novo",
            payload={"comentario_id": comentario.id, "alvo_tipo": comentario.alvo_tipo, "alvo_id": comentario.alvo_id},
        )


def _ppp_ids_visiveis_para_usuario(user, cliente_id: int):
    if getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
        return PPP.objects.filter(cliente_id=cliente_id).annotate(
            id_text=Cast("id", models.CharField()),
        ).values("id_text")
    if getattr(user, "role", None) in {
        user.Role.DIRETOR,
        user.Role.COORDENADOR_PEDAGOGICO,
        user.Role.ARTICULADOR,
    } and getattr(user, "escola_id", None):
        return PPP.objects.filter(cliente_id=cliente_id, escola_id=user.escola_id).annotate(
            id_text=Cast("id", models.CharField()),
        ).values("id_text")
    return PPP.objects.none().annotate(id_text=Cast("id", models.CharField())).values("id_text")


def _assert_ppp_comment_access(user, cliente_id: int, alvo_id) -> PPP:
    ppp = PPP.objects.filter(cliente_id=cliente_id, pk=alvo_id).select_related("escola").first()
    if not ppp:
        raise ValidationError({"alvo_id": "PPP não encontrado para este cliente."})
    if not _user_can_comment_ppp(user, ppp):
        raise PermissionDenied("Comentário fora do escopo permitido para o PPP.")
    return ppp


class ComentarioViewSet(FeatureFlagMixin, viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer
    permission_classes = [HasClientScope]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("alvo_tipo", "alvo_id", "resolvido")
    feature_flag = "ff.comments.enabled"
    throttle_scope = "comments-write"

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = Comentario.objects.filter(cliente_id=cliente_id).select_related("autor", "resolvido_por")
        user = self.request.user
        if getattr(user, "role", None) == user.Role.MEMBRO_GT:
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
                models.Q(alvo_tipo=Comentario.AlvoTipo.RESPOSTA, alvo_id__in=resposta_ids)
                | models.Q(alvo_tipo=Comentario.AlvoTipo.TEXTO_UNICO, alvo_id__in=texto_unico_ids)
                | models.Q(alvo_tipo=Comentario.AlvoTipo.QUADRO, alvo_id__in=quadro_ids)
            )
        elif getattr(user, "role", None) in {
            user.Role.DIRETOR,
            user.Role.COORDENADOR_PEDAGOGICO,
        }:
            ppp_ids = _ppp_ids_visiveis_para_usuario(user, cliente_id)
            queryset = queryset.filter(alvo_tipo=Comentario.AlvoTipo.PPP, alvo_id__in=ppp_ids)
        elif getattr(user, "role", None) == user.Role.REVISOR:
            revisoes = get_reviewer_queryset(user)
            resposta_ids = revisoes.filter(alvo_tipo=Comentario.AlvoTipo.RESPOSTA).values_list("alvo_id", flat=True)
            texto_unico_ids = revisoes.filter(alvo_tipo=Comentario.AlvoTipo.TEXTO_UNICO).values_list("alvo_id", flat=True)
            quadro_ids = revisoes.filter(alvo_tipo=Comentario.AlvoTipo.QUADRO).values_list("alvo_id", flat=True)
            queryset = queryset.filter(
                models.Q(alvo_tipo=Comentario.AlvoTipo.RESPOSTA, alvo_id__in=resposta_ids)
                | models.Q(alvo_tipo=Comentario.AlvoTipo.TEXTO_UNICO, alvo_id__in=texto_unico_ids)
                | models.Q(alvo_tipo=Comentario.AlvoTipo.QUADRO, alvo_id__in=quadro_ids)
            )
        elif getattr(user, "role", None) not in {
            user.Role.ADMIN_CLIENTE,
            user.Role.SUPER_ADMIN,
            user.Role.ARTICULADOR,
        }:
            queryset = queryset.none()
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        _assert_roles(
            user,
            {
                user.Role.MEMBRO_GT,
                user.Role.DIRETOR,
                user.Role.COORDENADOR_PEDAGOGICO,
                user.Role.ARTICULADOR,
                user.Role.ADMIN_CLIENTE,
                user.Role.REVISOR,
            },
        )
        cliente_id = _get_request_cliente_id(self.request)
        alvo_tipo = serializer.validated_data.get("alvo_tipo")
        alvo_id = serializer.validated_data.get("alvo_id")
        if getattr(user, "role", None) in {user.Role.DIRETOR, user.Role.COORDENADOR_PEDAGOGICO}:
            if alvo_tipo != Comentario.AlvoTipo.PPP:
                raise PermissionDenied("Diretor e Coordenador Pedagógico só podem comentar no PPP.")
        if alvo_tipo == Comentario.AlvoTipo.PPP:
            _assert_ppp_comment_access(user, cliente_id, alvo_id)
        if getattr(user, "role", None) == user.Role.REVISOR:
            permitido = get_reviewer_queryset(user).filter(alvo_tipo=alvo_tipo, alvo_id=str(alvo_id)).exists()
            if not permitido:
                raise PermissionDenied("Comentário fora do escopo atribuído.")
        mentions_ids = serializer.validated_data.pop("mentions", [])
        comentario = serializer.save(
            cliente_id=cliente_id,
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
        _notificar_comentario_alvo(comentario, user)

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
        campos_atualizados = set(serializer.validated_data.keys())
        is_author = request.user == instance.autor
        vai_resolver = (
            serializer.validated_data.get("resolvido")
            and not instance.resolvido
        )
        if vai_resolver:
            if instance.alvo_tipo == Comentario.AlvoTipo.PPP:
                ppp = _assert_ppp_comment_access(request.user, instance.cliente_id, instance.alvo_id)
                if not _user_can_conclude_ppp(request.user, ppp):
                    raise PermissionDenied("Somente Diretor ou Coordenador Pedagógico podem resolver comentários do PPP.")
            else:
                _assert_roles(request.user, {request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE, request.user.Role.REVISOR})
        elif not is_author:
            if instance.alvo_tipo == Comentario.AlvoTipo.PPP:
                _assert_ppp_comment_access(request.user, instance.cliente_id, instance.alvo_id)
            else:
                _assert_roles(request.user, {request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE, request.user.Role.REVISOR})
            if not campos_atualizados or campos_atualizados - {"resposta_html"}:
                raise PermissionDenied("Somente o autor pode atualizar este comentário.")
            if instance.respondido_por_id and instance.respondido_por_id != request.user.id:
                raise PermissionDenied("Este comentário já possui resposta registrada por outro usuário.")
        mentions_ids = serializer.validated_data.pop("mentions", None)
        save_kwargs = {}
        if not vai_resolver and not is_author and "resposta_html" in campos_atualizados:
            save_kwargs["respondido_por"] = request.user
            save_kwargs["respondido_em"] = timezone.now()
        comentario = serializer.save(**save_kwargs)
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
            payload = {
                "comentario_id": comentario.id,
                "conteudo_html": comentario.conteudo_html,
                "resposta_html": comentario.resposta_html,
            }
        broadcast_stream_event(comentario.alvo_tipo, comentario.alvo_id, evento, payload)
        serializer = self.get_serializer(comentario)
        response = Response(serializer.data)
        response["ETag"] = comentario.etag
        return response


def _build_mural_payload(*, payload, autor, gt_ids):
    titulo = (payload.get("titulo") or "").strip()
    conteudo_html = (payload.get("conteudo_html") or "").strip()
    if not titulo:
        raise ValidationError({"titulo": "Informe um título para o mural."})
    if not conteudo_html:
        raise ValidationError({"conteudo_html": "Informe o conteúdo do aviso."})

    link_url = payload.get("link_url") or ""
    anexos = payload.get("anexos") or []
    if not isinstance(anexos, list):
        raise ValidationError({"anexos": "Envie uma lista de anexos."})
    fixado = bool(payload.get("fixado", False))
    return {
        "mural_id": payload.get("mural_id") or uuid4().hex,
        "titulo": titulo,
        "conteudo_html": conteudo_html,
        "link_url": link_url,
        "anexos": anexos,
        "fixado": fixado,
        "gt_ids": gt_ids,
        "criado_por": {
            "id": getattr(autor, "id", None),
            "nome": getattr(autor, "nome", "") or getattr(autor, "email", ""),
            "email": getattr(autor, "email", ""),
        },
    }


def _pick_mural_data(notificacao):
    payload = notificacao.payload_json or {}
    return {
        "id": payload.get("mural_id", str(notificacao.id)),
        "titulo": payload.get("titulo") or "",
        "conteudo_html": payload.get("conteudo_html") or "",
        "link_url": payload.get("link_url"),
        "anexos": payload.get("anexos") or [],
        "fixado": bool(payload.get("fixado", False)),
        "gt_ids": payload.get("gt_ids") or [],
        "criado_por": payload.get("criado_por") or {},
        "created_at": notificacao.created_at,
        "updated_at": notificacao.updated_at,
    }


class MuralPostViewSet(viewsets.ViewSet):
    permission_classes = [HasClientScope]

    def list(self, request):
        cliente_id = _get_request_cliente_id(request)
        base_queryset = Notificacao.objects.filter(
            cliente_id=cliente_id,
            tipo=MURAL_NOTIFICATION_TYPE,
        )
        user = request.user
        if not CanManageMural().has_permission(request, self):
            base_queryset = base_queryset.filter(usuario=user)
        notifications = base_queryset.order_by("-updated_at")

        entries: dict[str, dict] = {}
        for notificacao in notifications:
            data = _pick_mural_data(notificacao)
            entry = entries.get(data["id"])
            if not entry or data["updated_at"] > entry["updated_at"]:
                entries[data["id"]] = data

        ordered = sorted(
            entries.values(),
            key=lambda item: (not item.get("fixado", False), item.get("updated_at")),
            reverse=True,
        )
        serializer = MuralPostSerializer(ordered, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = MuralPostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not CanManageMural().has_permission(request, self):
            raise PermissionDenied("Ação não permitida para o seu perfil")
        cliente_id = _get_request_cliente_id(request)

        gt_ids = serializer.validated_data.get("gt_ids") or []
        if gt_ids:
            gt_ids = list(
                GT.objects.filter(cliente_id=cliente_id, id__in=gt_ids).values_list("id", flat=True)
            )
        include_all = serializer.validated_data.get("include_all", False) or not gt_ids
        payload = _build_mural_payload(
            payload=serializer.validated_data,
            autor=request.user,
            gt_ids=gt_ids,
        )

        UserModel = get_user_model()
        recipients = UserModel.objects.filter(cliente_id=cliente_id, is_active=True)
        if not include_all and gt_ids:
            recipients = recipients.filter(grupos_trabalho__id__in=gt_ids)
        recipients = recipients.distinct()

        now = timezone.now()
        notificacoes = [
            Notificacao(
                cliente_id=cliente_id,
                usuario=usuario,
                tipo=MURAL_NOTIFICATION_TYPE,
                payload_json=payload,
                created_at=now,
                updated_at=now,
            )
            for usuario in recipients
        ]
        Notificacao.objects.bulk_create(notificacoes, ignore_conflicts=True)
        response_data = {
            **payload,
            "id": payload.get("mural_id"),
            "created_at": now,
            "updated_at": now,
        }
        response = MuralPostSerializer(response_data)
        return Response(response.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        serializer = MuralPostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not CanManageMural().has_permission(request, self):
            raise PermissionDenied("Ação não permitida para o seu perfil")
        cliente_id = _get_request_cliente_id(request)
        gt_ids = serializer.validated_data.get("gt_ids") or []
        if gt_ids:
            gt_ids = list(
                GT.objects.filter(cliente_id=cliente_id, id__in=gt_ids).values_list("id", flat=True)
            )
        payload = _build_mural_payload(
            payload={**serializer.validated_data, "mural_id": pk},
            autor=request.user,
            gt_ids=gt_ids,
        )
        now = timezone.now()
        queryset = Notificacao.objects.filter(
            cliente_id=cliente_id,
            tipo=MURAL_NOTIFICATION_TYPE,
            payload_json__mural_id=pk,
        )
        queryset.update(payload_json=payload, updated_at=now)
        response_data = {
            **payload,
            "id": pk,
            "created_at": now,
            "updated_at": now,
        }
        response = MuralPostSerializer(response_data)
        return Response(response.data)

    def destroy(self, request, pk=None):
        if not CanManageMural().has_permission(request, self):
            raise PermissionDenied("Ação não permitida para o seu perfil")
        cliente_id = _get_request_cliente_id(request)
        now = timezone.now()
        queryset = Notificacao.objects.filter(
            cliente_id=cliente_id,
            tipo=MURAL_NOTIFICATION_TYPE,
            payload_json__mural_id=pk,
        )
        queryset.update(is_deleted=True, updated_at=now)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
            queryset = queryset.filter(
                models.Q(url__icontains=query)
                | models.Q(titulo__icontains=query)
                | models.Q(descricao__icontains=query)
            )
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

    def _is_caderno_tags(self, tags) -> bool:
        return any(str(tag).startswith("caderno:") for tag in (tags or []))

    def perform_create(self, serializer):
        tags = serializer.validated_data.get("tags") or []
        if getattr(self.request.user, "role", None) == self.request.user.Role.MEMBRO_GT:
            if not self._is_caderno_tags(tags):
                raise PermissionDenied("Membros GT só podem criar blocos de caderno.")
        else:
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
        midia = serializer.save(cliente_id=_get_request_cliente_id(self.request), uploaded_by=self.request.user)
        if gt_id and midia.cliente_id:
            titulo = midia.titulo or "Novo material"
            descricao = f" — {midia.descricao}" if midia.descricao else ""
            conteudo = f"Novo link na Biblioteca: {titulo}{descricao}\n{midia.url}"
            deliver_admin_broadcast(
                cliente_id=midia.cliente_id,
                autor=self.request.user,
                conteudo=conteudo,
                gt_ids=[gt_id],
            )

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

    def _is_caderno_tags(self, tags) -> bool:
        return any(str(tag).startswith("caderno:") for tag in (tags or []))

    def perform_create(self, serializer):
        tags = serializer.validated_data.get("tags") or []
        if getattr(self.request.user, "role", None) == self.request.user.Role.MEMBRO_GT:
            if not self._is_caderno_tags(tags):
                raise PermissionDenied("Membros GT só podem criar blocos de caderno.")
        else:
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
        is_member = getattr(request.user, "role", None) == request.user.Role.MEMBRO_GT
        if is_member and not self._is_caderno_tags(instance.tags):
            raise PermissionDenied("Membros GT só podem editar blocos de caderno.")
        if not is_member:
            _assert_roles(request.user, {request.user.Role.ADMIN_CLIENTE, request.user.Role.ARTICULADOR})
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if is_member:
            tags = serializer.validated_data.get("tags") or instance.tags
            if not self._is_caderno_tags(tags):
                raise PermissionDenied("Mantenha a tag de caderno ao editar.")
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
        if getattr(self.request.user, "role", None) == self.request.user.Role.MEMBRO_GT:
            if not self._is_caderno_tags(instance.tags):
                raise PermissionDenied("Membros GT só podem remover blocos de caderno.")
        else:
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
