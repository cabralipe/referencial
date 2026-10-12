"""Rotas das salas de GT do Referencial dentro do AVA."""

from django.urls import path

from ava.views import gt


urlpatterns = [
    # --- Lista geral e sala ---
    path("", gt.salas_lista, name="gt_salas"),
    path("acompanhamento/", gt.acompanhamento, name="gt_acompanhamento"),
    path("<int:sala_id>/", gt.sala_detalhe, name="gt_sala"),
    path("<int:sala_id>/trabalho/", gt.sala_trabalho, name="gt_sala_trabalho"),
    path("<int:sala_id>/inscricoes/", gt.sala_inscricoes, name="gt_sala_inscricoes"),
    path("<int:sala_id>/reunioes/", gt.sala_reunioes, name="gt_sala_reunioes"),
    path("<int:sala_id>/documentos/", gt.sala_documentos, name="gt_sala_documentos"),

    # --- Inscrição ---
    path("<int:sala_id>/inscrever/", gt.inscricao_solicitar, name="gt_inscricao_solicitar"),
    path("<int:sala_id>/desistir/", gt.inscricao_desistir, name="gt_inscricao_desistir"),
    path("<int:sala_id>/inscricoes/nova/", gt.inscricao_manual, name="gt_inscricao_manual"),
    path(
        "<int:sala_id>/inscricoes/<int:inscricao_id>/<str:acao>/",
        gt.inscricao_acao,
        name="gt_inscricao_acao",
    ),
    path(
        "<int:sala_id>/lista-espera/promover/",
        gt.lista_espera_promover,
        name="gt_lista_espera_promover",
    ),

    # --- Diagnóstico e quadro do objetivo ---
    path(
        "<int:sala_id>/trabalho/diagnostico/",
        gt.trabalho_diagnostico_salvar,
        name="gt_trabalho_diagnostico",
    ),
    path("<int:sala_id>/trabalho/quadro/", gt.trabalho_quadro_salvar, name="gt_trabalho_quadro"),
    path("<int:sala_id>/trabalho/metas/", gt.meta_salvar, name="gt_meta_salvar"),
    path(
        "<int:sala_id>/trabalho/metas/<int:meta_id>/remover/",
        gt.meta_remover,
        name="gt_meta_remover",
    ),
    path(
        "<int:sala_id>/trabalho/estrategias/",
        gt.estrategia_salvar,
        name="gt_estrategia_salvar",
    ),
    path(
        "<int:sala_id>/trabalho/estrategias/<int:estrategia_id>/remover/",
        gt.estrategia_remover,
        name="gt_estrategia_remover",
    ),
    path(
        "<int:sala_id>/trabalho/comentarios/",
        gt.comentario_criar,
        name="gt_comentario_criar",
    ),
    path(
        "<int:sala_id>/trabalho/comentarios/<int:comentario_id>/resolver/",
        gt.comentario_resolver,
        name="gt_comentario_resolver",
    ),
    path(
        "<int:sala_id>/trabalho/<str:acao>/",
        gt.trabalho_transicao,
        name="gt_trabalho_transicao",
    ),

    # --- Reuniões, frequência e ata ---
    path("<int:sala_id>/reunioes/nova/", gt.reuniao_nova, name="gt_reuniao_nova"),
    path("reunioes/<int:reuniao_id>/", gt.reuniao_detalhe, name="gt_reuniao"),
    path("reunioes/<int:reuniao_id>/editar/", gt.reuniao_editar, name="gt_reuniao_editar"),
    path(
        "reunioes/<int:reuniao_id>/frequencia/preparar/",
        gt.frequencia_preparar,
        name="gt_frequencia_preparar",
    ),
    path(
        "reunioes/<int:reuniao_id>/frequencia/lancar/",
        gt.frequencia_lancar,
        name="gt_frequencia_lancar",
    ),
    path(
        "reunioes/<int:reuniao_id>/frequencia/validar/",
        gt.frequencia_validar,
        name="gt_frequencia_validar",
    ),
    path(
        "reunioes/<int:reuniao_id>/frequencia/reabrir/",
        gt.frequencia_reabrir,
        name="gt_frequencia_reabrir",
    ),
    path("reunioes/<int:reuniao_id>/ata/<str:acao>/", gt.ata_acao, name="gt_ata_acao"),

    # --- Documentos ---
    path(
        "<int:sala_id>/documentos/objetivo/",
        gt.documento_objetivo_gerar,
        name="gt_documento_objetivo",
    ),
    path(
        "reunioes/<int:reuniao_id>/documentos/ata/",
        gt.documento_ata_gerar,
        name="gt_documento_ata",
    ),
    path("documentos/<int:job_id>/arquivo/", gt.documento_download, name="gt_documento_download"),

    # --- Administração do Referencial ---
    path("admin/", gt.admin_painel, name="gt_admin"),
    path("admin/ciclos/novo/", gt.ciclo_form, name="gt_ciclo_novo"),
    path("admin/ciclos/<int:ciclo_id>/editar/", gt.ciclo_form, name="gt_ciclo_editar"),
    path(
        "admin/ciclos/<int:ciclo_id>/gerar-salas/",
        gt.ciclo_gerar_salas,
        name="gt_ciclo_gerar_salas",
    ),
    path(
        "admin/ciclos/<int:ciclo_id>/consolidar/",
        gt.consolidacao_gerar,
        name="gt_consolidacao_gerar",
    ),
    path("admin/objetivos/", gt.objetivos_lista, name="gt_objetivos"),
    path("admin/objetivos/novo/", gt.objetivo_form, name="gt_objetivo_novo"),
    path(
        "admin/objetivos/<int:objetivo_id>/editar/",
        gt.objetivo_form,
        name="gt_objetivo_editar",
    ),
    path("admin/objetivos/importar/", gt.objetivos_importar, name="gt_objetivos_importar"),
    path("admin/salas/nova/", gt.sala_form, name="gt_sala_nova"),
    path("admin/salas/<int:sala_id>/editar/", gt.sala_form, name="gt_sala_editar"),
    path("admin/salas/<int:sala_id>/situacao/", gt.sala_situacao, name="gt_sala_situacao"),
    path("admin/modelo-ata/", gt.modelo_ata_form, name="gt_modelo_ata"),

    # --- Tutorial guiado ---
    path("admin/tutorial/", gt.tutorial_guiado, name="gt_tutorial"),
    path(
        "admin/tutorial/exemplo/criar/",
        gt.tutorial_exemplo_criar,
        name="gt_tutorial_exemplo_criar",
    ),
    path(
        "admin/tutorial/exemplo/remover/",
        gt.tutorial_exemplo_remover,
        name="gt_tutorial_exemplo_remover",
    ),
]
