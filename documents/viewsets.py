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
        planos_all = list(PlanoAula.objects.filter(cliente_id=meta.cliente_id).values("id", "escola", "metas_ppp"))
        planos = [p for p in planos_all if isinstance(p.get("metas_ppp"), list) and meta.codigo in p["metas_ppp"]]
        by_school: dict[str, int] = {}
        for plano in planos:
            school = (plano.get("escola") or "").strip() or "Não informado"
            by_school[school] = by_school.get(school, 0) + 1
        por_escola = [{"escola": escola, "total": total} for escola, total in sorted(by_school.items(), key=lambda i: i[1], reverse=True)]
        return Response({"meta": PlanoMetaPPPSerializer(meta).data, "total_planos": len(planos), "por_escola": por_escola})


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
