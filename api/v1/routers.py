"""Definição de rotas da API v1."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .viewsets import (
    AuditLogViewSet,
    BlocoTextoViewSet,
    ComentarioViewSet,
    ExportJobViewSet,
    FormularioDinamicoViewSet,
    MidiaViewSet,
    NotificacaoViewSet,
    RevisaoViewSet,
    QuadroViewSet,
    RespostaViewSet,
    TarefaViewSet,
    TextoUnicoViewSet,
)

# Import dos ViewSets da biblioteca de mídia
from library.views import (
    MediaFileViewSet,
    MediaFolderViewSet,
    TagViewSet,
    FileVersionViewSet,
    FileShareViewSet,
    UserProfileViewSet,
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
router.register("revisoes", RevisaoViewSet, basename="revisao")
router.register("comentarios", ComentarioViewSet, basename="comentario")
router.register("notificacoes", NotificacaoViewSet, basename="notificacao")
router.register("midias", MidiaViewSet, basename="midia")
router.register("blocos", BlocoTextoViewSet, basename="bloco")

# Rotas da biblioteca de mídia
router.register("media/files", MediaFileViewSet, basename="mediafile")
router.register("media/folders", MediaFolderViewSet, basename="mediafolder")
router.register("media/tags", TagViewSet, basename="mediatag")
router.register("media/versions", FileVersionViewSet, basename="fileversion")
router.register("media/shares", FileShareViewSet, basename="fileshare")
router.register("media/profile", UserProfileViewSet, basename="userprofile")

__all__ = ["router"]
