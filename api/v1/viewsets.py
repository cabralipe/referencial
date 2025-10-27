"""Viewsets da API v1."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.views import APIView

from core.models import AuditLog, Cliente
from core.permissions import (
    HasClientScope,
    IsAdminClienteOrReadOnly,
    IsArticuladorForGT,
    IsMemberOfGT,
)
from core.utils import coletar_contexto_do_cliente, verificar_flag
from comments.models import Comentario
from curriculum.models import Anexo, GT, Resposta, Tarefa, TextoColaborativo, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from notifications.services import criar_notificacao
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
    TarefaSerializer,
    TextoColaborativoSerializer,
    TextoUnicoSerializer,
)


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
    if cliente_id is None:
        raise ValidationError("Cliente não associado")
    return int(cliente_id)


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
        queryset = Resposta.objects.select_related("gt", "pergunta").filter(cliente_id=cliente_id)
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
        cliente_id = _get_request_cliente_id(request)
        resposta = Resposta.objects.filter(gt=gt, pergunta=pergunta).first()
        if resposta:
            _check_etag(request, resposta)
            serializer = self.get_serializer(resposta, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(cliente_id=cliente_id)
            headers = {"ETag": resposta.etag}
            return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
        serializer.save(cliente_id=cliente_id)
        resposta = serializer.instance
        headers = self.get_success_headers(serializer.data)
        headers["ETag"] = resposta.etag
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        _check_etag(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente_id=instance.cliente_id)
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
    filterset_fields = ("gt",)

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        queryset = TextoColaborativo.objects.filter(cliente_id=cliente_id)
        gt_id = self.request.query_params.get("gt") or self.request.query_params.get("gt_id")
        if gt_id:
            queryset = queryset.filter(gt_id=gt_id)
        return queryset.order_by("-updated_at")

    def perform_create(self, serializer):
        cliente_id = _get_request_cliente_id(self.request)
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

    def _broadcast(self, instance: TextoColaborativo, *, created: bool) -> None:
        event = "collab_text:created" if created else "collab_text:updated"
        payload = {
            "id": instance.id,
            "gt": instance.gt_id,
            "titulo": instance.titulo,
            "conteudo_html": instance.conteudo_html,
            "version": instance.version,
            "autor": instance.autor_id,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
            "etag": instance.etag,
        }
        broadcast_stream_event("texto_colaborativo", instance.id, "collab_text:updated", payload)
        broadcast_stream_event("texto_colaborativo_list", instance.gt_id, event, payload)


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


class ExportJobViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ExportJobSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        return ExportJob.objects.all()

    def perform_create(self, serializer):
        cliente_id = _get_request_cliente_id(self.request)
        job = serializer.save(cliente_id=cliente_id)
        enqueue_export_job(job.id)


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [HasClientScope, IsAdminClienteOrReadOnly]

    def get_queryset(self):
        queryset = AuditLog.objects.all()
        entidade = self.request.query_params.get("entidade")
        entidade_id = self.request.query_params.get("entidade_id")
        if entidade:
            queryset = queryset.filter(entidade=entidade)
        if entidade_id:
            queryset = queryset.filter(entidade_id=entidade_id)
        return queryset.order_by("-timestamp")


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
