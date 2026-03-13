from django.urls import path
from ava.views import student

urlpatterns = [
    path("", student.dashboard, name="aluno_dashboard"),
    path("curso/<slug:slug>/", student.curso_detalhe, name="aluno_curso_detalhe"),
    path("curso/<slug:curso_slug>/aula/<int:aula_id>/", student.acessar_aula, name="aluno_acessar_aula"),
    path("curso/<slug:curso_slug>/aula/<int:aula_id>/atividade/<int:atividade_id>/", student.responder_atividade, name="aluno_responder_atividade"),
    path("conteudo/<int:conteudo_id>/marcar/", student.marcar_conteudo, name="aluno_marcar_conteudo"),
]
