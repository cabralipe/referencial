from django.urls import path, include

app_name = "ava"

urlpatterns = [
    path("", include("ava.urls.public")),
    path("aluno/", include("ava.urls.student")),
]
