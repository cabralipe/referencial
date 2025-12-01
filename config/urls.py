from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from .views import serve_frontend

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.v1.urls")),
]

urlpatterns += [
    re_path(r"^(?!admin/|api/|static/|media/).*", serve_frontend, name="frontend"),
]

# Servir mídia local mesmo fora de DEBUG (útil em deploy com volume/pasta persistente)
if settings.MEDIA_BACKEND == "local":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
