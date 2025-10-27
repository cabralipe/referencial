"""Definição de rotas da API v1."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .viewsets import (
    AuditLogViewSet,
    BlocoTextoViewSet,
    ComentarioViewSet,
    ExportJobViewSet,
    GTViewSet,
    FormularioDinamicoViewSet,
    MidiaViewSet,
    NotificacaoViewSet,
    RevisaoViewSet,
    QuadroViewSet,
    RespostaViewSet,
    TarefaViewSet,
    TextoUnicoViewSet,
)

router = DefaultRouter()
router.trailing_slash = "/?"
router.register("tarefas", TarefaViewSet, basename="tarefa")
router.register("gts", GTViewSet, basename="gt")
router.register("respostas", RespostaViewSet, basename="resposta")
router.register("texto_unico", TextoUnicoViewSet, basename="texto_unico")
router.register("quadro", QuadroViewSet, basename="quadro")
router.register("formularios", FormularioDinamicoViewSet, basename="formulario")
router.register("exports", ExportJobViewSet, basename="export")
router.register("audit", AuditLogViewSet, basename="audit")
router.register("revisoes", RevisaoViewSet, basename="revisao")
router.register("comentarios", ComentarioViewSet, basename="comentario")
router.register("notificacoes", NotificacaoViewSet, basename="notificacao")
router.register("midias", MidiaViewSet, basename="midia")
router.register("blocos", BlocoTextoViewSet, basename="bloco")

__all__ = ["router"]
