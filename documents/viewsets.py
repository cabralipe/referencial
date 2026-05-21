from django.db.models import Count

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import HasClientScope
from courses.models import PlanoAula

from .models import DocumentoPublicacao, DocumentoVersao, PlanoMetaPPP, ReferencialHabilidade
from .serializers import (
    DocumentoPublicacaoSerializer,
    DocumentoVersaoSerializer,
    PlanoMetaPPPSerializer,
    ReferencialHabilidadeSerializer,
)


class PlanoMetaPPPViewSet(viewsets.ModelViewSet):
    serializer_class = PlanoMetaPPPSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        return PlanoMetaPPP.objects.filter(cliente_id=cliente_id)

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id)

    @action(detail=True, methods=["get"], url_path="relatorio")
    def relatorio(self, request, pk=None):
        meta = self.get_object()
        planos_qs = PlanoAula.objects.filter(
            cliente_id=meta.cliente_id,
            metas_ppp__contains=[meta.codigo],
        )
        total_planos = planos_qs.count()
        por_escola = [
            {"escola": (row["escola"] or "").strip() or "Não informado", "total": row["total"]}
            for row in planos_qs.values("escola").annotate(total=Count("id")).order_by("-total")
        ]
        return Response({"meta": PlanoMetaPPPSerializer(meta).data, "total_planos": total_planos, "por_escola": por_escola})


class ReferencialHabilidadeViewSet(viewsets.ModelViewSet):
    serializer_class = ReferencialHabilidadeSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        return ReferencialHabilidade.objects.filter(cliente_id=cliente_id)

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id)


class DocumentoVersaoViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoVersaoSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        return DocumentoVersao.objects.filter(cliente_id=cliente_id)

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id, autor=self.request.user)


class DocumentoPublicacaoViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoPublicacaoSerializer
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        return DocumentoPublicacao.objects.filter(cliente_id=cliente_id)

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id, publicado_por=self.request.user)
