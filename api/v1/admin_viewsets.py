"""Viewsets do Admin Console (CRUD completo)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from core.models import (
    AuditLog,
    Cliente,
    ClienteConfig,
    ClienteFeatureFlag,
    ClienteTema,
    Eixo,
    ScoreEntry,
    ThrottleBlock,
    UserSessionLog,
)
from core.permissions import HasClientScope, IsAdminConsole
from core.scope import resolve_cliente_scope
from curriculum.models import (
    Anexo,
    Area,
    Escola,
    GT,
    Pergunta,
    Resposta,
    Tarefa,
    TextoColaborativo,
    TextoUnico,
)
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from meb.models import MebMessage, MebThread
from notifications.models import Notificacao
from notifications.services import criar_notificacao
from reviews.models import Revisao, ReviewDecision, ReviewerAssignment
from workshop.models import CelulaQuadro, Quadro, QuadroColuna, QuadroLinha

from .admin_serializers import (
    AnexoAdminSerializer,
    AreaAdminSerializer,
    EscolaAdminSerializer,
    AuditLogAdminSerializer,
    BlocoTextoAdminSerializer,
    CampoDinamicoAdminSerializer,
    CelulaQuadroAdminSerializer,
    ClienteAdminSerializer,
    ClienteConfigAdminSerializer,
    ClienteFeatureFlagAdminSerializer,
    ClienteTemaAdminSerializer,
    ComentarioAdminSerializer,
    ConsultaPublicaAdminSerializer,
    EixoAdminSerializer,
    ExportJobAdminSerializer,
    FormularioDinamicoAdminSerializer,
    GTAdminSerializer,
    ManifestacaoPublicaAdminSerializer,
    MebMessageAdminSerializer,
    MebThreadAdminSerializer,
    MidiaAdminSerializer,
    NotificacaoAdminSerializer,
    PerguntaAdminSerializer,
    QuadroAdminSerializer,
    QuadroColunaAdminSerializer,
    QuadroLinhaAdminSerializer,
    RespostaAdminSerializer,
    RespostaCampoDinamicoAdminSerializer,
    RevisaoAdminSerializer,
    ReviewDecisionAdminSerializer,
    ReviewerAssignmentAdminSerializer,
    ScoreEntryAdminSerializer,
    TarefaAdminSerializer,
    TextoColaborativoAdminSerializer,
    TextoUnicoAdminSerializer,
    ThrottleBlockAdminSerializer,
    UserSessionLogAdminSerializer,
    UsuarioAdminSerializer,
)

UserModel = get_user_model()


class AdminModelViewSet(viewsets.ModelViewSet):
    permission_classes = [HasClientScope, IsAdminConsole]

    def _has_cliente_field(self, model: type[models.Model]) -> bool:
        return any(field.attname == "cliente_id" for field in model._meta.fields)

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        scope_id = resolve_cliente_scope(self.request)
        model = qs.model
        if model is Cliente:
            if user.role == user.Role.SUPER_ADMIN:
                return qs
            return qs.filter(pk=scope_id)
        if model is UserModel:
            if user.role == user.Role.SUPER_ADMIN:
                if scope_id:
                    return qs.filter(models.Q(cliente_id=scope_id) | models.Q(clientes__id=scope_id)).distinct()
                return qs
            return qs.filter(models.Q(cliente_id=scope_id) | models.Q(clientes__id=scope_id)).distinct()
        if self._has_cliente_field(model):
            if user.role == user.Role.SUPER_ADMIN:
                cliente_param = self.request.query_params.get("cliente_id")
                if cliente_param:
                    return qs.filter(cliente_id=cliente_param)
                return qs
            return qs.filter(cliente_id=scope_id)
        return qs

    def _scope_cliente_id(self):
        return resolve_cliente_scope(self.request)

    def _coerce_cliente_scope_payload(self, data):
        model = self.queryset.model
        if self.request.user.role == self.request.user.Role.SUPER_ADMIN or not self._has_cliente_field(model):
            return data

        scope_id = self._scope_cliente_id()
        if not scope_id:
            raise PermissionDenied("Cliente não associado ao usuário.")

        payload = data.copy() if hasattr(data, "copy") else dict(data)
        incoming_cliente = payload.get("cliente")
        if incoming_cliente not in {None, "", scope_id, str(scope_id)}:
            raise PermissionDenied("Não é permitido vincular outro cliente.")
        payload["cliente"] = scope_id
        return payload

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs and kwargs["data"] is not None:
            kwargs["data"] = self._coerce_cliente_scope_payload(kwargs["data"])
        return super().get_serializer(*args, **kwargs)

    def _require_cliente_scope(self, serializer):
        model = self.queryset.model
        if not self._has_cliente_field(model):
            return None
        cliente = serializer.validated_data.get("cliente")
        if self.request.user.role != self.request.user.Role.SUPER_ADMIN:
            scope_id = self._scope_cliente_id()
            if cliente and cliente.id != scope_id:
                raise PermissionDenied("Não é permitido vincular outro cliente.")
            return scope_id
        if not cliente:
            raise ValidationError({"cliente": "Informe o cliente para registros multi-tenant."})
        return None

    def perform_create(self, serializer):
        cliente_id = self._require_cliente_scope(serializer)
        if cliente_id is not None:
            serializer.save(cliente_id=cliente_id)
        else:
            serializer.save()

    def perform_update(self, serializer):
        cliente_id = self._require_cliente_scope(serializer)
        if cliente_id is not None:
            serializer.save(cliente_id=cliente_id)
        else:
            serializer.save()


class ClienteAdminViewSet(AdminModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteAdminSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != request.user.Role.SUPER_ADMIN:
            raise PermissionDenied("Apenas super admin pode criar clientes.")
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != request.user.Role.SUPER_ADMIN:
            raise PermissionDenied("Apenas super admin pode remover clientes.")
        return super().destroy(request, *args, **kwargs)


class UsuarioAdminViewSet(AdminModelViewSet):
    queryset = UserModel.objects.all()
    serializer_class = UsuarioAdminSerializer

    def _validate_escola_scope(self, serializer):
        if self.request.user.role == self.request.user.Role.SUPER_ADMIN:
            return
        scope_id = self._scope_cliente_id()
        escola = serializer.validated_data.get("escola")
        if escola and escola.cliente_id != scope_id:
            raise PermissionDenied("Não é permitido vincular escola de outro cliente.")

    def _guard_super_admin_role_change(self):
        if self.request.user.role == self.request.user.Role.SUPER_ADMIN:
            return
        if self.request.data.get("role") == self.request.user.Role.SUPER_ADMIN:
            raise PermissionDenied("Não é permitido criar super admins.")

    def create(self, request, *args, **kwargs):
        self._guard_super_admin_role_change()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._guard_super_admin_role_change()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._guard_super_admin_role_change()
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        password = serializer.validated_data.pop("password", None)
        if self.request.user.role != self.request.user.Role.SUPER_ADMIN:
            if serializer.validated_data.get("role") == self.request.user.Role.SUPER_ADMIN:
                raise PermissionDenied("Não é permitido criar super admins.")
            cliente = serializer.validated_data.get("cliente")
            clientes = serializer.validated_data.get("clientes") or []
            scope_id = self._scope_cliente_id()
            if cliente and cliente.id != scope_id:
                raise PermissionDenied("Não é permitido vincular outro cliente.")
            if any(item.id != scope_id for item in clientes):
                raise PermissionDenied("Não é permitido vincular clientes fora do escopo.")
            self._validate_escola_scope(serializer)
            serializer.validated_data["cliente_id"] = scope_id
        instance = serializer.save()
        if self.request.user.role != self.request.user.Role.SUPER_ADMIN:
            scope_id = self._scope_cliente_id()
            if scope_id:
                instance.clientes.add(scope_id)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])

    def perform_update(self, serializer):
        password = serializer.validated_data.pop("password", None)
        if self.request.user.role != self.request.user.Role.SUPER_ADMIN:
            if serializer.validated_data.get("role") == self.request.user.Role.SUPER_ADMIN:
                raise PermissionDenied("Não é permitido criar super admins.")
            cliente = serializer.validated_data.get("cliente")
            clientes = serializer.validated_data.get("clientes") or []
            scope_id = self._scope_cliente_id()
            if cliente and cliente.id != scope_id:
                raise PermissionDenied("Não é permitido vincular outro cliente.")
            if any(item.id != scope_id for item in clientes):
                raise PermissionDenied("Não é permitido vincular clientes fora do escopo.")
            self._validate_escola_scope(serializer)
            serializer.validated_data["cliente_id"] = scope_id
        instance = serializer.save()
        if self.request.user.role != self.request.user.Role.SUPER_ADMIN:
            scope_id = self._scope_cliente_id()
            if scope_id:
                instance.clientes.add(scope_id)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])


class ClienteConfigAdminViewSet(AdminModelViewSet):
    queryset = ClienteConfig.raw_objects.all()
    serializer_class = ClienteConfigAdminSerializer


class ClienteFeatureFlagAdminViewSet(AdminModelViewSet):
    queryset = ClienteFeatureFlag.raw_objects.all()
    serializer_class = ClienteFeatureFlagAdminSerializer


class ClienteTemaAdminViewSet(AdminModelViewSet):
    queryset = ClienteTema.raw_objects.all()
    serializer_class = ClienteTemaAdminSerializer


class EixoAdminViewSet(AdminModelViewSet):
    queryset = Eixo.raw_objects.all()
    serializer_class = EixoAdminSerializer


class AuditLogAdminViewSet(AdminModelViewSet):
    queryset = AuditLog.raw_objects.all()
    serializer_class = AuditLogAdminSerializer


class ThrottleBlockAdminViewSet(AdminModelViewSet):
    queryset = ThrottleBlock.objects.all()
    serializer_class = ThrottleBlockAdminSerializer


class ScoreEntryAdminViewSet(AdminModelViewSet):
    queryset = ScoreEntry.objects.all()
    serializer_class = ScoreEntryAdminSerializer


class UserSessionLogAdminViewSet(AdminModelViewSet):
    queryset = UserSessionLog.objects.all()
    serializer_class = UserSessionLogAdminSerializer


class GTAdminViewSet(AdminModelViewSet):
    queryset = GT.objects.all()
    serializer_class = GTAdminSerializer


class AreaAdminViewSet(AdminModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaAdminSerializer


class EscolaAdminViewSet(AdminModelViewSet):
    queryset = Escola.objects.all()
    serializer_class = EscolaAdminSerializer


class TarefaAdminViewSet(AdminModelViewSet):
    queryset = Tarefa.objects.all()
    serializer_class = TarefaAdminSerializer


class PerguntaAdminViewSet(AdminModelViewSet):
    queryset = Pergunta.objects.all()
    serializer_class = PerguntaAdminSerializer


class RespostaAdminViewSet(AdminModelViewSet):
    queryset = Resposta.raw_objects.all()
    serializer_class = RespostaAdminSerializer


class AnexoAdminViewSet(AdminModelViewSet):
    queryset = Anexo.objects.all()
    serializer_class = AnexoAdminSerializer


class TextoUnicoAdminViewSet(AdminModelViewSet):
    queryset = TextoUnico.objects.all()
    serializer_class = TextoUnicoAdminSerializer


class TextoColaborativoAdminViewSet(AdminModelViewSet):
    queryset = TextoColaborativo.objects.all()
    serializer_class = TextoColaborativoAdminSerializer


class QuadroAdminViewSet(AdminModelViewSet):
    queryset = Quadro.objects.all()
    serializer_class = QuadroAdminSerializer


class QuadroLinhaAdminViewSet(AdminModelViewSet):
    queryset = QuadroLinha.objects.all()
    serializer_class = QuadroLinhaAdminSerializer


class QuadroColunaAdminViewSet(AdminModelViewSet):
    queryset = QuadroColuna.objects.all()
    serializer_class = QuadroColunaAdminSerializer


class CelulaQuadroAdminViewSet(AdminModelViewSet):
    queryset = CelulaQuadro.objects.all()
    serializer_class = CelulaQuadroAdminSerializer


class FormularioDinamicoAdminViewSet(AdminModelViewSet):
    queryset = FormularioDinamico.objects.all()
    serializer_class = FormularioDinamicoAdminSerializer


class CampoDinamicoAdminViewSet(AdminModelViewSet):
    queryset = CampoDinamico.objects.all()
    serializer_class = CampoDinamicoAdminSerializer


class RespostaCampoDinamicoAdminViewSet(AdminModelViewSet):
    queryset = RespostaCampoDinamico.objects.all()
    serializer_class = RespostaCampoDinamicoAdminSerializer


class RevisaoAdminViewSet(AdminModelViewSet):
    queryset = Revisao.objects.all()
    serializer_class = RevisaoAdminSerializer


class ReviewerAssignmentAdminViewSet(AdminModelViewSet):
    queryset = ReviewerAssignment.objects.all()
    serializer_class = ReviewerAssignmentAdminSerializer

    def perform_create(self, serializer):
        assignment = serializer.save()
        criar_notificacao(
            cliente_id=assignment.cliente_id,
            usuario_id=assignment.reviewer_id,
            tipo="revisor.atribuicao",
            payload={
                "assignment_id": assignment.id,
                "scope_type": assignment.scope_type,
                "scope_id": assignment.scope_id,
            },
        )


class ReviewDecisionAdminViewSet(AdminModelViewSet):
    queryset = ReviewDecision.objects.all()
    serializer_class = ReviewDecisionAdminSerializer


class ExportJobAdminViewSet(AdminModelViewSet):
    queryset = ExportJob.objects.all()
    serializer_class = ExportJobAdminSerializer


class NotificacaoAdminViewSet(AdminModelViewSet):
    queryset = Notificacao.objects.all()
    serializer_class = NotificacaoAdminSerializer


class ComentarioAdminViewSet(AdminModelViewSet):
    queryset = Comentario.objects.all()
    serializer_class = ComentarioAdminSerializer


class MidiaAdminViewSet(AdminModelViewSet):
    queryset = Midia.objects.all()
    serializer_class = MidiaAdminSerializer


class BlocoTextoAdminViewSet(AdminModelViewSet):
    queryset = BlocoTexto.objects.all()
    serializer_class = BlocoTextoAdminSerializer


class ConsultaPublicaAdminViewSet(AdminModelViewSet):
    queryset = ConsultaPublica.objects.all()
    serializer_class = ConsultaPublicaAdminSerializer


class ManifestacaoPublicaAdminViewSet(AdminModelViewSet):
    queryset = ManifestacaoPublica.objects.all()
    serializer_class = ManifestacaoPublicaAdminSerializer


class MebThreadAdminViewSet(AdminModelViewSet):
    queryset = MebThread.objects.all()
    serializer_class = MebThreadAdminSerializer


class MebMessageAdminViewSet(AdminModelViewSet):
    queryset = MebMessage.objects.all()
    serializer_class = MebMessageAdminSerializer
