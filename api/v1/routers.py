"""Definição de rotas da API v1."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .viewsets import (
    AiAssistViewSet,
    AuditLogViewSet,
    ThrottleBlockViewSet,
    BlocoTextoViewSet,
    ComentarioViewSet,
    ExportJobViewSet,
    ConsultaPublicaViewSet,
    AreaViewSet,
    GTViewSet,
    FormularioDinamicoViewSet,
    MidiaViewSet,
    MuralPostViewSet,
    NotificacaoViewSet,
    PerguntaViewSet,
    PppViewSet,
    ScoreViewSet,
    RevisaoViewSet,
    QuadroViewSet,
    RespostaViewSet,
    TarefaViewSet,
    TextoColaborativoViewSet,
    TextoUnicoViewSet,
    MebThreadViewSet,
    MebMessageViewSet,
    UsuarioLookupViewSet,
)

router = DefaultRouter()
router.trailing_slash = "/?"
router.register("ai/assist", AiAssistViewSet, basename="ai-assist")
router.register("tarefas", TarefaViewSet, basename="tarefa")
router.register("perguntas", PerguntaViewSet, basename="pergunta")
router.register("gts", GTViewSet, basename="gt")
router.register("areas", AreaViewSet, basename="area")
router.register("respostas", RespostaViewSet, basename="resposta")
router.register("texto_unico", TextoUnicoViewSet, basename="texto_unico")
router.register("textos_colaborativos", TextoColaborativoViewSet, basename="texto_colaborativo")
router.register("quadro", QuadroViewSet, basename="quadro")
router.register("formularios", FormularioDinamicoViewSet, basename="formulario")
router.register("exports", ExportJobViewSet, basename="export")
router.register("audit", AuditLogViewSet, basename="audit")
router.register("throttle_blocks", ThrottleBlockViewSet, basename="throttle_block")
router.register("score", ScoreViewSet, basename="score")
router.register("revisoes", RevisaoViewSet, basename="revisao")
router.register("comentarios", ComentarioViewSet, basename="comentario")
router.register("notificacoes", NotificacaoViewSet, basename="notificacao")
router.register("mural", MuralPostViewSet, basename="mural")
router.register("midias", MidiaViewSet, basename="midia")
router.register("blocos", BlocoTextoViewSet, basename="bloco")
router.register("meb/threads", MebThreadViewSet, basename="meb_thread")
router.register("meb/mensagens", MebMessageViewSet, basename="meb_message")
router.register("usuarios/lookup", UsuarioLookupViewSet, basename="usuario_lookup")
router.register("consultas_publicas", ConsultaPublicaViewSet, basename="consulta_publica")
router.register("ppp", PppViewSet, basename="ppp")

__all__ = ["router"]
