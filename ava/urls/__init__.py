from django.urls import include, path
from django.views.generic import RedirectView
from ava.views.attendance import confirmar_presenca

app_name = "ava"

urlpatterns = [
    path("presenca/<uuid:token>/", confirmar_presenca, name="confirmar_presenca"),
    path("", RedirectView.as_view(url="/ava/catalogo/", permanent=False)),
    path("", include("ava.urls.public")),
    path("aluno/", include("ava.urls.student")),
    path("gestao/", include("ava.urls.management")),
    path("gts/", include("ava.urls.gt")),
]
