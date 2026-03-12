from django.urls import path
from ava.views import student

app_name = "ava_aluno"

urlpatterns = [
    path("", student.dashboard, name="dashboard"),
    path("curso/<slug:slug>/", student.curso_detalhe, name="curso_detalhe"),
    path("curso/<slug:curso_slug>/aula/<int:aula_id>/", student.acessar_aula, name="acessar_aula"),
    path("curso/<slug:curso_slug>/aula/<int:aula_id>/atividade/<int:atividade_id>/", student.responder_atividade, name="responder_atividade"),
    path("conteudo/<int:conteudo_id>/marcar/", student.marcar_conteudo, name="marcar_conteudo"),
]
