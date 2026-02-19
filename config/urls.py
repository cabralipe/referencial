from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from .views import serve_frontend

urlpatterns = [
    # Rotas do frontend que começam com admin/ mas devem ser servidas pelo React
    re_path(r"^admin/(mural|console|trilhas|ppp)", serve_frontend),

    path("admin/", admin.site.urls),
    path("api/v1/", include("api.v1.urls")),
    path("", include("reviews.urls")),
]

urlpatterns += [
    re_path(r"^(?!admin/|api/|static/|media/).*", serve_frontend, name="frontend"),
]

# Servir mídia sempre que o storage for local (ou quando DEBUG estiver ativo).
# Isso mantém a rota /media/ respondendo mesmo em produção para PDF de consulta pública.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Em produção com storage local, forçamos o serve do django (inseguro, mas necessário se não usar S3/Nginx)
    from django.views.static import serve
    urlpatterns += [
        re_path(r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"), serve, {"document_root": settings.MEDIA_ROOT}),
    ]
