"""Definição de rotas da API v1."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .viewsets import (
    AuditLogViewSet,
    ExportJobViewSet,
    FormularioDinamicoViewSet,
    QuadroViewSet,
    RespostaViewSet,
    TarefaViewSet,
    TextoUnicoViewSet,
)

router = DefaultRouter()
router.trailing_slash = "/?"
router.register("tarefas", TarefaViewSet, basename="tarefa")
router.register("respostas", RespostaViewSet, basename="resposta")
router.register("texto_unico", TextoUnicoViewSet, basename="texto_unico")
router.register("quadro", QuadroViewSet, basename="quadro")
router.register("formularios", FormularioDinamicoViewSet, basename="formulario")
router.register("exports", ExportJobViewSet, basename="export")
router.register("audit", AuditLogViewSet, basename="audit")

__all__ = ["router"]
