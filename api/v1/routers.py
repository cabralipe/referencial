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
from .admin_viewsets import (
    AnexoAdminViewSet,
    AreaAdminViewSet,
    AuditLogAdminViewSet,
    BlocoTextoAdminViewSet,
    CampoDinamicoAdminViewSet,
    CelulaQuadroAdminViewSet,
    ClienteAdminViewSet,
    ClienteConfigAdminViewSet,
    ClienteFeatureFlagAdminViewSet,
    ClienteTemaAdminViewSet,
    ComentarioAdminViewSet,
    ConsultaPublicaAdminViewSet,
    ExportJobAdminViewSet,
    FormularioDinamicoAdminViewSet,
    GTAdminViewSet,
    ManifestacaoPublicaAdminViewSet,
    MebMessageAdminViewSet,
    MebThreadAdminViewSet,
    MidiaAdminViewSet,
    NotificacaoAdminViewSet,
    PerguntaAdminViewSet,
    QuadroAdminViewSet,
    QuadroColunaAdminViewSet,
    QuadroLinhaAdminViewSet,
    RespostaAdminViewSet,
    RespostaCampoDinamicoAdminViewSet,
    RevisaoAdminViewSet,
    ReviewDecisionAdminViewSet,
    ReviewerAssignmentAdminViewSet,
    ScoreEntryAdminViewSet,
    TarefaAdminViewSet,
    TextoColaborativoAdminViewSet,
    TextoUnicoAdminViewSet,
    ThrottleBlockAdminViewSet,
    UserSessionLogAdminViewSet,
    UsuarioAdminViewSet,
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

# Admin Console routes
router.register("admin/clientes", ClienteAdminViewSet, basename="admin_clientes")
router.register("admin/clientes-config", ClienteConfigAdminViewSet, basename="admin_clientes_config")
router.register("admin/clientes-feature-flags", ClienteFeatureFlagAdminViewSet, basename="admin_clientes_feature_flags")
router.register("admin/clientes-temas", ClienteTemaAdminViewSet, basename="admin_clientes_temas")
router.register("admin/usuarios", UsuarioAdminViewSet, basename="admin_usuarios")
router.register("admin/audit-logs", AuditLogAdminViewSet, basename="admin_audit_logs")
router.register("admin/throttle-blocks", ThrottleBlockAdminViewSet, basename="admin_throttle_blocks")
router.register("admin/score-entries", ScoreEntryAdminViewSet, basename="admin_score_entries")
router.register("admin/session-logs", UserSessionLogAdminViewSet, basename="admin_session_logs")

router.register("admin/gts", GTAdminViewSet, basename="admin_gts")
router.register("admin/areas", AreaAdminViewSet, basename="admin_areas")
router.register("admin/tarefas", TarefaAdminViewSet, basename="admin_tarefas")
router.register("admin/perguntas", PerguntaAdminViewSet, basename="admin_perguntas")
router.register("admin/respostas", RespostaAdminViewSet, basename="admin_respostas")
router.register("admin/anexos", AnexoAdminViewSet, basename="admin_anexos")
router.register("admin/textos-unicos", TextoUnicoAdminViewSet, basename="admin_textos_unicos")
router.register("admin/textos-colaborativos", TextoColaborativoAdminViewSet, basename="admin_textos_colaborativos")

router.register("admin/quadros", QuadroAdminViewSet, basename="admin_quadros")
router.register("admin/quadros-linhas", QuadroLinhaAdminViewSet, basename="admin_quadros_linhas")
router.register("admin/quadros-colunas", QuadroColunaAdminViewSet, basename="admin_quadros_colunas")
router.register("admin/quadros-celulas", CelulaQuadroAdminViewSet, basename="admin_quadros_celulas")

router.register("admin/formularios", FormularioDinamicoAdminViewSet, basename="admin_formularios")
router.register("admin/campos-dinamicos", CampoDinamicoAdminViewSet, basename="admin_campos_dinamicos")
router.register("admin/respostas-campos", RespostaCampoDinamicoAdminViewSet, basename="admin_respostas_campos")

router.register("admin/revisoes", RevisaoAdminViewSet, basename="admin_revisoes")
router.register("admin/reviewer-assignments", ReviewerAssignmentAdminViewSet, basename="admin_reviewer_assignments")
router.register("admin/review-decisions", ReviewDecisionAdminViewSet, basename="admin_review_decisions")
router.register("admin/exports", ExportJobAdminViewSet, basename="admin_exports")
router.register("admin/notificacoes", NotificacaoAdminViewSet, basename="admin_notificacoes")
router.register("admin/comentarios", ComentarioAdminViewSet, basename="admin_comentarios")
router.register("admin/midias", MidiaAdminViewSet, basename="admin_midias")
router.register("admin/blocos", BlocoTextoAdminViewSet, basename="admin_blocos")
router.register("admin/consultas-publicas", ConsultaPublicaAdminViewSet, basename="admin_consultas_publicas")
router.register("admin/manifestacoes-publicas", ManifestacaoPublicaAdminViewSet, basename="admin_manifestacoes_publicas")
router.register("admin/meb-threads", MebThreadAdminViewSet, basename="admin_meb_threads")
router.register("admin/meb-mensagens", MebMessageAdminViewSet, basename="admin_meb_mensagens")

__all__ = ["router"]
