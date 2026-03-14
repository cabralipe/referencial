from django.urls import path

from ava.views import management


urlpatterns = [
    path("dashboard/", management.dashboard, name="gestao_dashboard"),
    path("tentativas/<int:tentativa_id>/", management.tentativa_detalhe, name="gestao_tentativa_detalhe"),
]
