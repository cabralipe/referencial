"""Views para a API da biblioteca de mídia."""

from django.db.models import Q, Count, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import ClientScopedViewSetMixin
from .models import (
    MediaFile, MediaFolder, Tag, FileVersion, 
    FileTag, FileShare, UserProfile, Midia, BlocoTexto
)
from .serializers import (
    MediaFileSerializer, MediaFileUploadSerializer, MediaFolderSerializer,
    TagSerializer, FileVersionSerializer, FileTagSerializer, 
    FileShareSerializer, UserProfileSerializer, MidiaSerializer, BlocoTextoSerializer
)
from .permissions import (
    IsOwnerOrPublic, IsOwnerOrShared, IsOwnerOrPublicFolder,
    CanManageShares, CanCreateInFolder, IsOwnerOrReadOnlyPublic,
    CanAccessFileVersions, CanManageTags, MediaLibraryPermission
)
from .services import FileProcessingService, StorageService, VersionService
from .websocket_service import media_websocket_service


class MediaFileViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para arquivos de mídia."""
    
    queryset = MediaFile.objects.select_related('owner', 'folder').prefetch_related(
        'filetag_set__tag', 'versions', 'file_shares__shared_with'
    )
    permission_classes = [IsAuthenticated, MediaLibraryPermission]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'file_type', 'folder', 'is_public']
    search_fields = ['name', 'description', 'filetag_set__tag__name']
    ordering_fields = ['name', 'created_at', 'updated_at', 'file_size']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Retorna o serializer apropriado para a ação."""
        if self.action == 'create':
            return MediaFileUploadSerializer
        return MediaFileSerializer
    
    def get_queryset(self):
        """Filtra arquivos baseado nas permissões do usuário."""
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.filter(is_public=True)
        
        # Obter perfil do usuário
        from .models import UserProfile
        profile = UserProfile.get_or_create_for_user(user)
        effective_role = profile.get_effective_media_role()
        
        # Admin vê tudo do cliente
        if effective_role == UserProfile.MediaRole.ADMIN:
            return queryset
        
        # Outros veem arquivos próprios, públicos ou compartilhados
        return queryset.filter(
            Q(owner=user) |
            Q(is_public=True) |
            Q(file_shares__shared_with=user, file_shares__is_active=True)
        ).distinct()
    
    def perform_create(self, serializer):
        """Cria um novo arquivo."""
        media_file = serializer.save(owner=self.request.user, cliente=self.get_cliente())
        
        # Enviar notificação WebSocket
        media_websocket_service.notify_file_uploaded(media_file, self.request.user)
    
    def perform_destroy(self, instance):
        """Remove arquivo e atualiza quota do usuário."""
        file_id = instance.id
        folder_id = instance.folder_id
        
        # Atualizar quota
        StorageService.update_user_storage(
            instance.owner, 
            instance.file_size, 
            'remove'
        )
        
        # Soft delete
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        
        # Enviar notificação WebSocket
        media_websocket_service.notify_file_deleted(file_id, folder_id, self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_tag(self, request, pk=None):
        """Adiciona uma tag ao arquivo."""
        file = self.get_object()
        tag_id = request.data.get('tag_id')
        
        if not tag_id:
            return Response(
                {'error': 'tag_id é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tag = Tag.objects.get(id=tag_id, cliente=self.get_cliente())
            file_tag, created = FileTag.objects.get_or_create(
                file=file,
                tag=tag,
                cliente=self.get_cliente()
            )
            
            if created:
                return Response({'message': 'Tag adicionada com sucesso'})
            else:
                return Response(
                    {'error': 'Tag já existe neste arquivo'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Tag.DoesNotExist:
            return Response(
                {'error': 'Tag não encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['delete'])
    def remove_tag(self, request, pk=None):
        """Remove uma tag do arquivo."""
        file = self.get_object()
        tag_id = request.data.get('tag_id')
        
        if not tag_id:
            return Response(
                {'error': 'tag_id é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            file_tag = FileTag.objects.get(
                file=file,
                tag_id=tag_id,
                cliente=self.get_cliente()
            )
            file_tag.delete()
            return Response({'message': 'Tag removida com sucesso'})
            
        except FileTag.DoesNotExist:
            return Response(
                {'error': 'Tag não encontrada neste arquivo'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser])
    def upload_version(self, request, pk=None):
        """Faz upload de uma nova versão do arquivo."""
        file = self.get_object()
        new_file = request.FILES.get('file')
        description = request.data.get('description', '')
        
        if not new_file:
            return Response(
                {'error': 'Arquivo é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar arquivo
        is_valid, message = FileProcessingService.validate_file(new_file)
        if not is_valid:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar quota
        has_quota, quota_message = StorageService.check_storage_quota(
            request.user, new_file.size
        )
        if not has_quota:
            return Response({'error': quota_message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar versão
        version = VersionService.create_version(file, new_file, description)
        
        # Atualizar arquivo principal
        old_size = file.file_size
        file.file = new_file
        file.file_size = new_file.size
        file.file_type = FileProcessingService.get_file_type(new_file)
        file.metadata = FileProcessingService.extract_metadata(new_file)
        
        # Gerar novo thumbnail
        thumbnail = FileProcessingService.generate_thumbnail(new_file)
        if thumbnail:
            file.thumbnail.save(thumbnail.name, thumbnail, save=False)
        
        file.save()
        
        # Atualizar quota
        size_diff = new_file.size - old_size
        if size_diff != 0:
            operation = 'add' if size_diff > 0 else 'remove'
            StorageService.update_user_storage(
                request.user, 
                abs(size_diff), 
                operation
            )
        
        serializer = FileVersionSerializer(version, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def restore_version(self, request, pk=None):
        """Restaura uma versão específica do arquivo."""
        file = self.get_object()
        version_id = request.data.get('version_id')
        
        if not version_id:
            return Response(
                {'error': 'version_id é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            version = FileVersion.objects.get(
                id=version_id,
                file=file,
                cliente=self.get_cliente()
            )
            
            backup_version = VersionService.restore_version(file, version)
            
            serializer = FileVersionSerializer(backup_version, context={'request': request})
            return Response({
                'message': 'Versão restaurada com sucesso',
                'backup_version': serializer.data
            })
            
        except FileVersion.DoesNotExist:
            return Response(
                {'error': 'Versão não encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Compartilha arquivo com outro usuário."""
        file = self.get_object()
        serializer = FileShareSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save(
                file=file,
                shared_by=request.user,
                cliente=self.get_cliente()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download do arquivo."""
        file = self.get_object()
        
        if not file.file:
            raise Http404("Arquivo não encontrado")
        
        response = HttpResponse(
            file.file.read(),
            content_type=file.file_type or 'application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{file.name}"'
        response['Content-Length'] = file.file_size
        
        return response


class MediaFolderViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para pastas de mídia."""
    
    queryset = MediaFolder.objects.select_related('parent').prefetch_related('children')
    serializer_class = MediaFolderSerializer
    permission_classes = [IsAuthenticated, MediaLibraryPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filtra pastas baseado nas permissões do usuário."""
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.filter(is_public=True)
        
        # Pastas próprias ou públicas
        return queryset.filter(
            Q(owner=user) | Q(is_public=True)
        ).distinct()
    
    def perform_create(self, serializer):
        """Cria uma nova pasta."""
        media_folder = serializer.save(owner=self.request.user, cliente=self.get_cliente())
        
        # Enviar notificação WebSocket
        media_websocket_service.notify_folder_created(media_folder, self.request.user)
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Lista arquivos da pasta."""
        folder = self.get_object()
        files = MediaFile.objects.filter(
            folder=folder,
            is_active=True,
            cliente=self.get_cliente()
        ).select_related('owner').prefetch_related('filetag_set__tag')
        
        # Aplicar filtros de permissão
        user = request.user
        if user.is_authenticated:
            files = files.filter(
                Q(owner=user) |
                Q(is_public=True) |
                Q(file_shares__shared_with=user, file_shares__is_active=True)
            ).distinct()
        else:
            files = files.filter(is_public=True)
        
        serializer = MediaFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)


class TagViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para tags."""
    
    queryset = Tag.objects.annotate(files_count=Count('files'))
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, MediaLibraryPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'files_count']
    ordering = ['name']
    
    def perform_create(self, serializer):
        """Cria uma nova tag."""
        serializer.save(cliente=self.get_cliente())
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Lista arquivos com esta tag."""
        tag = self.get_object()
        files = MediaFile.objects.filter(
            tags=tag,
            is_active=True,
            cliente=self.get_cliente()
        ).select_related('owner', 'folder').prefetch_related('filetag_set__tag')
        
        # Aplicar filtros de permissão
        user = request.user
        if user.is_authenticated:
            files = files.filter(
                Q(owner=user) |
                Q(is_public=True) |
                Q(file_shares__shared_with=user, file_shares__is_active=True)
            ).distinct()
        else:
            files = files.filter(is_public=True)
        
        serializer = MediaFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)


class FileVersionViewSet(ClientScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet para versões de arquivo (somente leitura)."""
    
    queryset = FileVersion.objects.select_related('file')
    serializer_class = FileVersionSerializer
    permission_classes = [IsAuthenticated, CanAccessFileVersions]
    
    def get_queryset(self):
        """Filtra versões baseado nas permissões do usuário."""
        queryset = super().get_queryset()
        user = self.request.user
        
        return queryset.filter(
            Q(file__owner=user) |
            Q(file__file_shares__shared_with=user, file__file_shares__is_active=True)
        ).distinct()


class FileShareViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para compartilhamentos de arquivo."""
    
    queryset = FileShare.objects.select_related('file', 'shared_with', 'shared_by')
    serializer_class = FileShareSerializer
    permission_classes = [IsAuthenticated, CanManageShares]
    
    def get_queryset(self):
        """Filtra compartilhamentos do usuário."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Compartilhamentos feitos pelo usuário ou recebidos por ele
        return queryset.filter(
            Q(shared_by=user) | Q(shared_with=user)
        )
    
    def perform_create(self, serializer):
        """Cria um novo compartilhamento."""
        file_share = serializer.save(shared_by=self.request.user, cliente=self.get_cliente())
        
        # Enviar notificação WebSocket
        media_websocket_service.notify_file_shared(file_share, self.request.user)


class UserProfileViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para perfis de usuário."""
    
    queryset = UserProfile.objects.select_related('user')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Retorna apenas o perfil do usuário atual."""
        return super().get_queryset().filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Retorna o perfil do usuário atual."""
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            cliente=self.get_cliente()
        )
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def storage_stats(self, request):
        """Retorna estatísticas de armazenamento."""
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            cliente=self.get_cliente()
        )
        
        # Estatísticas por categoria
        files = MediaFile.objects.filter(
            owner=request.user,
            is_active=True,
            cliente=self.get_cliente()
        )
        
        stats_by_category = files.values('category').annotate(
            count=Count('id'),
            total_size=Sum('file_size')
        ).order_by('category')
        
        return Response({
            'profile': UserProfileSerializer(profile, context={'request': request}).data,
            'by_category': list(stats_by_category),
            'total_files': files.count(),
            'total_size': files.aggregate(Sum('file_size'))['file_size__sum'] or 0
        })


# ViewSets para modelos legados
class MidiaViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para modelo Midia legado."""
    
    queryset = Midia.objects.select_related('uploader')
    serializer_class = MidiaSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyPublic]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['caption', 'tags']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Cria uma nova mídia."""
        serializer.save(uploader=self.request.user, cliente=self.get_cliente())


class BlocoTextoViewSet(ClientScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para blocos de texto."""
    
    queryset = BlocoTexto.objects.select_related('creator')
    serializer_class = BlocoTextoSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyPublic]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'tags']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Cria um novo bloco de texto."""
        serializer.save(creator=self.request.user, cliente=self.get_cliente())