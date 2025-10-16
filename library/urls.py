"""URLs para a API da biblioteca de mídia."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MediaFileViewSet, MediaFolderViewSet, TagViewSet,
    FileVersionViewSet, FileShareViewSet, UserProfileViewSet,
    MidiaViewSet, BlocoTextoViewSet
)

# Router para as APIs
router = DefaultRouter()
router.register(r'files', MediaFileViewSet, basename='mediafile')
router.register(r'folders', MediaFolderViewSet, basename='mediafolder')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'versions', FileVersionViewSet, basename='fileversion')
router.register(r'shares', FileShareViewSet, basename='fileshare')
router.register(r'profile', UserProfileViewSet, basename='userprofile')

# Modelos legados
router.register(r'midia', MidiaViewSet, basename='midia')
router.register(r'blocos-texto', BlocoTextoViewSet, basename='blocotexto')

app_name = 'library'

urlpatterns = [
    path('api/', include(router.urls)),
]