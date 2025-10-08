"""URLs da API pública v1."""

from __future__ import annotations

from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .routers import router
from .viewsets import ClienteViewSet, DiffView
from .views import SessionLoginView, CsrfTokenView

urlpatterns = [
    path("", include(router.urls)),
    path("cliente/me", ClienteViewSet.as_view({"get": "me"}), name="cliente-me"),
    path("diff", DiffView.as_view(), name="diff-html"),
    path("auth/csrf", CsrfTokenView.as_view(), name="csrf-token"),
    path("auth/login", SessionLoginView.as_view(), name="auth-login"),
    path("auth/jwt", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/jwt/refresh", TokenRefreshView.as_view(), name="token-refresh"),
]
