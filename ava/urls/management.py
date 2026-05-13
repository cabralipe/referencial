from django.urls import path

from ava.views import management


urlpatterns = [
    path("dashboard/", management.dashboard, name="gestao_dashboard"),
    path("dashboard/relatorios/entenda/", management.dashboard_relatorio_entenda, name="gestao_dashboard_relatorio_entenda"),
    path("dashboard/relatorios/<str:formato>/", management.dashboard_relatorio, name="gestao_dashboard_relatorio"),
    path("tentativas/<int:tentativa_id>/", management.tentativa_detalhe, name="gestao_tentativa_detalhe"),
]
