from django.urls import path

from ava.views import diario, management


urlpatterns = [
    path("dashboard/", management.dashboard, name="gestao_dashboard"),
    path("dashboard/relatorios/entenda/", management.dashboard_relatorio_entenda, name="gestao_dashboard_relatorio_entenda"),
    path("dashboard/relatorios/<str:formato>/", management.dashboard_relatorio, name="gestao_dashboard_relatorio"),
    path("tentativas/<int:tentativa_id>/", management.tentativa_detalhe, name="gestao_tentativa_detalhe"),
    path("acompanhamento/", management.acompanhamento_lista, name="gestao_acompanhamento"),
    path("acompanhamento/novo/", management.acompanhamento_novo, name="gestao_acompanhamento_novo"),
    path("acompanhamento/<int:documento_id>/editar/", management.acompanhamento_editar, name="gestao_acompanhamento_editar"),
    path("acompanhamento/<int:documento_id>/arquivo/", management.acompanhamento_arquivo, name="gestao_acompanhamento_arquivo"),
    path("acompanhamento/<int:documento_id>/arquivar/", management.acompanhamento_arquivar, name="gestao_acompanhamento_arquivar"),

    # --- Diário de Bordo do professor ---
    path("diario/", diario.diario_lista, name="diario_lista"),
    path("diario/novo/", diario.diario_novo, name="diario_novo"),
    path("diario/aulas.json", diario.diario_aulas_json, name="diario_aulas_json"),
    path(
        "diario/exportar/<str:formato>/",
        diario.diario_exportar,
        name="diario_exportar",
    ),
    path("diario/<int:diario_id>/", diario.diario_detalhe, name="diario_detalhe"),
    path("diario/<int:diario_id>/editar/", diario.diario_editar, name="diario_editar"),
    path("diario/<int:diario_id>/enviar/", diario.diario_enviar, name="diario_enviar"),
    path("diario/<int:diario_id>/revisar/", diario.diario_revisar, name="diario_revisar"),
    path("diario/<int:diario_id>/reabrir/", diario.diario_reabrir, name="diario_reabrir"),
    path(
        "diario/<int:diario_id>/participantes/adicionar/",
        diario.diario_participante_adicionar,
        name="diario_participante_adicionar",
    ),
    path(
        "diario/<int:diario_id>/participantes/<int:participante_id>/remover/",
        diario.diario_participante_remover,
        name="diario_participante_remover",
    ),
    path(
        "diario/<int:diario_id>/midias/adicionar/",
        diario.diario_midia_adicionar,
        name="diario_midia_adicionar",
    ),
    path(
        "diario/<int:diario_id>/midias/<int:midia_id>/remover/",
        diario.diario_midia_remover,
        name="diario_midia_remover",
    ),
    path(
        "diario/<int:diario_id>/midias/<int:midia_id>/arquivo/",
        diario.diario_midia_arquivo,
        name="diario_midia_arquivo",
    ),

    # --- Planilhas configuráveis ---
    path("planilhas/", diario.planilha_modelo_lista, name="planilha_modelo_lista"),
    path("planilhas/nova/", diario.planilha_modelo_form, name="planilha_modelo_nova"),
    path(
        "planilhas/<int:modelo_id>/editar/",
        diario.planilha_modelo_form,
        name="planilha_modelo_editar",
    ),
    path(
        "planilhas/<int:modelo_id>/alternar/",
        diario.planilha_modelo_alternar,
        name="planilha_modelo_alternar",
    ),
    path(
        "planilhas/<int:modelo_id>/registros/",
        diario.planilha_registros,
        name="planilha_registros",
    ),
    path(
        "planilhas/<int:modelo_id>/exportar/<str:formato>/",
        diario.planilha_exportar,
        name="planilha_exportar",
    ),
    path(
        "planilhas/<int:modelo_id>/modelo-em-branco/",
        diario.planilha_modelo_em_branco,
        name="planilha_modelo_em_branco",
    ),
    path(
        "planilhas/<int:modelo_id>/importar/",
        diario.planilha_importar,
        name="planilha_importar",
    ),
    path(
        "planilhas/importacoes/<int:importacao_id>/mapear/",
        diario.planilha_importar_mapear,
        name="planilha_importar_mapear",
    ),
    path(
        "planilhas/importacoes/<int:importacao_id>/cancelar/",
        diario.planilha_importar_cancelar,
        name="planilha_importar_cancelar",
    ),
]
