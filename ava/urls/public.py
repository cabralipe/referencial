from django.urls import path
from ava.views import public

urlpatterns = [
    path("catalogo/", public.catalogo_cursos, name="catalogo"),
    path("curso/<slug:slug>/", public.detalhes_curso_publico, name="detalhes_curso"),
    path("curso/<slug:slug>/matricular/", public.matricular_curso_agora, name="matricular_curso"),
]
