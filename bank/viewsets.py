from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.permissions import HasClientScope
from notifications.services import criar_notificacao

from .models import PlanoPublicado, PlanoPublicadoAvaliacao, PlanoPublicadoComentario
from .serializers import (
    PlanoPublicadoAvaliacaoSerializer,
    PlanoPublicadoComentarioSerializer,
    PlanoPublicadoSerializer,
)
from .services.moderation import apply_curation_decision


class PlanoPublicadoViewSet(viewsets.ModelViewSet):
    permission_classes = [HasClientScope]
    serializer_class = PlanoPublicadoSerializer

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        qs = PlanoPublicado.objects.filter(cliente_id=cliente_id).select_related("plano", "publicado_por")
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(plano__componente_curricular__icontains=q)
                | Q(plano__unidade_tematica__icontains=q)
                | Q(plano__escola__icontains=q)
            )
        status_curadoria = self.request.query_params.get("status_curadoria")
        if status_curadoria:
            qs = qs.filter(status_curadoria=status_curadoria)
        visibilidade = self.request.query_params.get("visibilidade")
        if visibilidade:
            qs = qs.filter(visibilidade=visibilidade)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id, publicado_por=self.request.user)

    @action(detail=True, methods=["post"], url_path="curadoria")
    def curadoria(self, request, pk=None):
        aprovado = request.data.get("aprovado")
        if aprovado is None:
            raise ValidationError({"aprovado": "Informe true ou false."})
        plano_publicado = self.get_object()
        updated = apply_curation_decision(plano_publicado, bool(aprovado))
        criar_notificacao(
            cliente_id=updated.cliente_id,
            usuario_id=updated.plano.autor_id,
            tipo="banco.curadoria",
            payload={"plano_publicado_id": updated.id, "status": updated.status_curadoria},
        )
        return Response(self.get_serializer(updated).data)


class PlanoPublicadoComentarioViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [HasClientScope]
    serializer_class = PlanoPublicadoComentarioSerializer

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        plano_publicado = self.request.query_params.get("plano_publicado")
        qs = PlanoPublicadoComentario.objects.filter(cliente_id=cliente_id).select_related("autor")
        if plano_publicado:
            qs = qs.filter(plano_publicado_id=plano_publicado)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        instance = serializer.save(cliente_id=cliente_id, autor=self.request.user)
        criar_notificacao(
            cliente_id=instance.cliente_id,
            usuario_id=instance.plano_publicado.plano.autor_id,
            tipo="banco.novo_comentario",
            payload={"plano_publicado_id": instance.plano_publicado_id, "comentario_id": instance.id},
        )


class PlanoPublicadoAvaliacaoViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [HasClientScope]
    serializer_class = PlanoPublicadoAvaliacaoSerializer

    def get_queryset(self):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        plano_publicado = self.request.query_params.get("plano_publicado")
        qs = PlanoPublicadoAvaliacao.objects.filter(cliente_id=cliente_id).select_related("avaliador")
        if plano_publicado:
            qs = qs.filter(plano_publicado_id=plano_publicado)
        return qs

    def perform_create(self, serializer):
        cliente_id = getattr(self.request, "cliente_id", None) or getattr(self.request.user, "cliente_id", None)
        serializer.save(cliente_id=cliente_id, avaliador=self.request.user)

