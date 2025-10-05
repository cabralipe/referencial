"""Viewsets da API v1."""

from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError

from core.models import AuditLog, Cliente
from core.permissions import (
    HasClientScope,
    IsAdminClienteOrReadOnly,
    IsArticuladorForGT,
    IsMemberOfGT,
)
from curriculum.models import Anexo, Resposta, Tarefa, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from tasks.exports import enqueue_export_job
from tasks.synthesis import enqueue_texto_unico
from workshop.models import CelulaQuadro, Quadro

from .serializers import (
    AnexoSerializer,
    AuditLogSerializer,
    CampoDinamicoSerializer,
    ClienteMeSerializer,
    PerguntaSerializer,
    ExportJobSerializer,
    FormularioDinamicoSerializer,
    CelulaQuadroSerializer,
    QuadroSerializer,
    RespostaCampoDinamicoSerializer,
    RespostaSerializer,
    TarefaSerializer,
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
        serializer = RespostaCampoDinamicoSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente_id=_get_request_cliente_id(request))
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
