from django.urls import path

from ava.views import management


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
]
