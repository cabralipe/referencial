"""URLs da API pública v1."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.schemas import get_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from .routers import router
from .viewsets import ClienteViewSet, DiffView
from analytics.viewsets import AdminDashboardView, UserDashboardView
from .views import (
    AuthMeView,
    CsrfTokenView,
    SessionLoginView,
    RoleTokenObtainPairView,
    MebAvatarUploadView,
    ContinuarView,
    ApprovedDiffView,
    ConsultaPublicaPublicView,
    ManifestacaoPublicaView,
)

schema_view = get_schema_view(
    title="PLACI API",
    description="OpenAPI da Plataforma de Construcao Interativa",
    version="1.0.0",
)

urlpatterns = [
    path("", include(router.urls)),
    path("cliente/me", ClienteViewSet.as_view({"get": "me"}), name="cliente-me"),
    path("diff", DiffView.as_view(), name="diff-html"),
    path("auth/csrf", CsrfTokenView.as_view(), name="csrf-token"),
    path("auth/login", SessionLoginView.as_view(), name="auth-login"),
    path("auth/me", AuthMeView.as_view(), name="auth-me"),
    path("auth/jwt", RoleTokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/jwt/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("meb/avatar", MebAvatarUploadView.as_view(), name="meb-avatar-upload"),
    path("continuar", ContinuarView.as_view(), name="continuar"),
    path("diff/aprovado", ApprovedDiffView.as_view(), name="diff-aprovado"),
    path("analytics/dashboard", UserDashboardView.as_view(), name="analytics-user-dashboard"),
    path("analytics/admin", AdminDashboardView.as_view(), name="analytics-admin-dashboard"),
    path("schema", schema_view, name="openapi-schema"),
    path(
        "consultas_publicas/public/<str:token>",
        ConsultaPublicaPublicView.as_view(),
        name="consulta-publica-public",
    ),
    path(
        "consultas_publicas/public/<str:token>/manifestacoes",
        ManifestacaoPublicaView.as_view(),
        name="consulta-publica-manifestacoes",
    ),
]
