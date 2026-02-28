from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import HasClientScope
from notifications.services import criar_notificacao

from .models import AvaliacaoPlano, Curso, PlanoAula, Rubrica, RubricaCriterio
from .placi_serializers import (
    AvaliacaoPlanoSerializer,
    PlanoAulaSerializer,
    RubricaCriterioSerializer,
    RubricaSerializer,
)
from .services.certification_service import emit_certificate_if_eligible, evaluate_certification


class PlanoAulaEstruturadoViewSet(viewsets.ModelViewSet):
    serializer_class = PlanoAulaSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        qs = PlanoAula.objects.filter(cliente_id=cliente_id).select_related("curso", "autor")
        curso_id = self.request.query_params.get("curso")
        if curso_id:
            qs = qs.filter(curso_id=curso_id)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id, autor=self.request.user)

    @action(detail=True, methods=["patch"], url_path="autosave")
    def autosave(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        plano = self.get_object()
        plano.status = PlanoAula.Status.EM_REVISAO
        plano.save(update_fields=["status", "updated_at"])
        criar_notificacao(
            cliente_id=plano.cliente_id,
            usuario_id=plano.autor_id,
            tipo="plano.enviado",
            payload={"plano_id": plano.id},
        )
        return Response(self.get_serializer(plano).data)


class RubricaViewSet(viewsets.ModelViewSet):
    serializer_class = RubricaSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        qs = Rubrica.objects.filter(cliente_id=cliente_id).prefetch_related("criterios")
        curso_id = self.request.query_params.get("curso")
        if curso_id:
            qs = qs.filter(curso_id=curso_id)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id)


class RubricaCriterioViewSet(viewsets.ModelViewSet):
    serializer_class = RubricaCriterioSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        qs = RubricaCriterio.objects.filter(cliente_id=cliente_id)
        rubrica_id = self.request.query_params.get("rubrica")
        if rubrica_id:
            qs = qs.filter(rubrica_id=rubrica_id)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id)


class AvaliacaoPlanoViewSet(viewsets.ModelViewSet):
    serializer_class = AvaliacaoPlanoSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        qs = AvaliacaoPlano.objects.filter(cliente_id=cliente_id).select_related("criterio", "avaliador")
        plano_id = self.request.query_params.get("plano")
        if plano_id:
            qs = qs.filter(plano_id=plano_id)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        instance = serializer.save(cliente_id=cliente_id, avaliador=self.request.user)
        criar_notificacao(
            cliente_id=instance.cliente_id,
            usuario_id=instance.plano.autor_id,
            tipo="plano.avaliado",
            payload={"plano_id": instance.plano_id, "avaliacao_id": instance.id},
        )


class CertificationViewSet(viewsets.ViewSet):
    permission_classes = [HasClientScope]

    def retrieve(self, request, pk=None):
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        curso = Curso.objects.get(pk=pk, cliente_id=cliente_id)
        result = evaluate_certification(curso, request.user.id)
        return Response({"checks": result.checks, "approved": result.approved, "certificate_id": result.certificate_id})

    @action(detail=True, methods=["post"], url_path="emit")
    def emit(self, request, pk=None):
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        curso = Curso.objects.get(pk=pk, cliente_id=cliente_id)
        result = emit_certificate_if_eligible(curso, request.user.id)
        if result.approved:
            criar_notificacao(
                cliente_id=curso.cliente_id,
                usuario_id=request.user.id,
                tipo="certificacao.liberada",
                payload={"curso_id": curso.id, "certificate_id": result.certificate_id},
            )
        return Response({"checks": result.checks, "approved": result.approved, "certificate_id": result.certificate_id})

