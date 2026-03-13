from django.urls import include, path
from django.views.generic import RedirectView

app_name = "ava"

urlpatterns = [
    path("", RedirectView.as_view(url="/ava/catalogo/", permanent=False)),
    path("", include("ava.urls.public")),
    path("aluno/", include("ava.urls.student")),
]
