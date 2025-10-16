"""Serializers para a API da biblioteca de mídia."""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    MediaFile, MediaFolder, Tag, FileVersion, 
    FileTag, FileShare, UserProfile, Midia, BlocoTexto
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer básico para usuário."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id', 'username', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer para perfil do usuário."""
    
    user = UserSerializer(read_only=True)
    storage_used_mb = serializers.ReadOnlyField()
    storage_quota_mb = serializers.ReadOnlyField()
    storage_percentage = serializers.ReadOnlyField()
    effective_media_role = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'storage_quota', 'storage_used',
            'storage_used_mb', 'storage_quota_mb', 'storage_percentage',
            'default_folder_view', 'auto_tag_enabled', 'media_role',
            'effective_media_role', 'permissions',
            'can_upload', 'can_create_folders', 'can_manage_tags',
            'can_share_files', 'can_delete_own', 'can_delete_others'
        ]
        read_only_fields = ['id', 'storage_used']
    
    def get_effective_media_role(self, obj):
        """Retorna o papel efetivo do usuário na media library."""
        return obj.get_effective_media_role()
    
    def get_permissions(self, obj):
        """Retorna as permissões específicas do usuário."""
        return {
            'can_upload': obj.can_perform_action('upload'),
            'can_create_folders': obj.can_perform_action('create_folders'),
            'can_manage_tags': obj.can_perform_action('manage_tags'),
            'can_share_files': obj.can_perform_action('share_files'),
            'can_delete_own': obj.can_perform_action('delete_own'),
            'can_delete_others': obj.can_perform_action('delete_others'),
        }


class TagSerializer(serializers.ModelSerializer):
    """Serializer para tags."""
    
    files_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'color', 'description', 
            'is_system', 'files_count', 'created_at'
        ]
        read_only_fields = ['id', 'is_system', 'created_at']
    
    def get_files_count(self, obj):
        """Retorna o número de arquivos com esta tag."""
        return obj.files.count()


class MediaFolderSerializer(serializers.ModelSerializer):
    """Serializer para pastas de mídia."""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    total_size = serializers.SerializerMethodField()
    breadcrumb = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFolder
        fields = [
            'id', 'name', 'description', 'parent', 'parent_name',
            'is_public', 'children', 'files_count', 'total_size',
            'breadcrumb', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        """Retorna subpastas."""
        children = obj.children.filter(is_active=True).order_by('name')
        return MediaFolderSerializer(children, many=True, context=self.context).data
    
    def get_files_count(self, obj):
        """Retorna o número de arquivos na pasta."""
        return obj.files.filter(is_active=True).count()
    
    def get_total_size(self, obj):
        """Retorna o tamanho total dos arquivos na pasta."""
        total = sum(f.file_size for f in obj.files.filter(is_active=True))
        return total
    
    def get_breadcrumb(self, obj):
        """Retorna o caminho da pasta."""
        breadcrumb = []
        current = obj
        while current:
            breadcrumb.insert(0, {
                'id': current.id,
                'name': current.name
            })
            current = current.parent
        return breadcrumb


class FileVersionSerializer(serializers.ModelSerializer):
    """Serializer para versões de arquivo."""
    
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = FileVersion
        fields = [
            'id', 'version_number', 'file_data', 'file_size',
            'file_size_mb', 'change_description', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_file_size_mb(self, obj):
        """Retorna o tamanho em MB."""
        return round(obj.file_size / (1024 * 1024), 2)


class FileTagSerializer(serializers.ModelSerializer):
    """Serializer para tags de arquivo."""
    
    tag = TagSerializer(read_only=True)
    tag_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FileTag
        fields = ['id', 'tag', 'tag_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class FileShareSerializer(serializers.ModelSerializer):
    """Serializer para compartilhamento de arquivos."""
    
    shared_with = UserSerializer(read_only=True)
    shared_with_id = serializers.IntegerField(write_only=True)
    shared_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FileShare
        fields = [
            'id', 'shared_with', 'shared_with_id', 'shared_by',
            'permission', 'expires_at', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'shared_by', 'created_at']


class MediaFileSerializer(serializers.ModelSerializer):
    """Serializer para arquivos de mídia."""
    
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    owner = UserSerializer(read_only=True)
    tags = FileTagSerializer(source='filetag_set', many=True, read_only=True)
    versions = FileVersionSerializer(many=True, read_only=True)
    shares = FileShareSerializer(source='file_shares', many=True, read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFile
        fields = [
            'id', 'name', 'description', 'file', 'thumbnail',
            'file_type', 'file_size', 'file_size_mb', 'category',
            'folder', 'folder_name', 'owner', 'is_public',
            'metadata', 'tags', 'versions', 'shares',
            'file_url', 'thumbnail_url', 'can_edit', 'can_delete',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'category', 'metadata',
            'owner', 'created_at', 'updated_at'
        ]
    
    def get_file_size_mb(self, obj):
        """Retorna o tamanho em MB."""
        return round(obj.file_size / (1024 * 1024), 2)
    
    def get_file_url(self, obj):
        """Retorna a URL do arquivo."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_thumbnail_url(self, obj):
        """Retorna a URL do thumbnail."""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_can_edit(self, obj):
        """Verifica se o usuário pode editar o arquivo."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Proprietário pode editar
        if obj.owner == request.user:
            return True
        
        # Verificar permissões de compartilhamento
        share = obj.file_shares.filter(
            shared_with=request.user,
            is_active=True,
            permission__in=['edit', 'full']
        ).first()
        
        return share is not None
    
    def get_can_delete(self, obj):
        """Verifica se o usuário pode deletar o arquivo."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Apenas proprietário pode deletar
        if obj.owner == request.user:
            return True
        
        # Verificar permissão completa
        share = obj.file_shares.filter(
            shared_with=request.user,
            is_active=True,
            permission='full'
        ).first()
        
        return share is not None


class MediaFileUploadSerializer(serializers.ModelSerializer):
    """Serializer para upload de arquivos."""
    
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = MediaFile
        fields = [
            'name', 'description', 'file', 'folder', 
            'is_public', 'tag_ids'
        ]
    
    def create(self, validated_data):
        """Cria um novo arquivo com processamento."""
        from .services import FileProcessingService, StorageService
        
        tag_ids = validated_data.pop('tag_ids', [])
        file = validated_data['file']
        
        # Validar arquivo
        is_valid, message = FileProcessingService.validate_file(file)
        if not is_valid:
            raise serializers.ValidationError({'file': message})
        
        # Verificar quota
        user = self.context['request'].user
        has_quota, quota_message = StorageService.check_storage_quota(user, file.size)
        if not has_quota:
            raise serializers.ValidationError({'file': quota_message})
        
        # Processar arquivo
        validated_data['file_type'] = FileProcessingService.get_file_type(file)
        validated_data['category'] = FileProcessingService.get_file_category(validated_data['file_type'])
        validated_data['file_size'] = file.size
        validated_data['metadata'] = FileProcessingService.extract_metadata(file)
        validated_data['owner'] = user
        
        # Sanitizar nome do arquivo
        if not validated_data.get('name'):
            validated_data['name'] = FileProcessingService.sanitize_filename(file.name)
        
        # Criar arquivo
        media_file = super().create(validated_data)
        
        # Gerar thumbnail
        thumbnail = FileProcessingService.generate_thumbnail(file)
        if thumbnail:
            media_file.thumbnail.save(thumbnail.name, thumbnail, save=True)
        
        # Adicionar tags
        if tag_ids:
            for tag_id in tag_ids:
                try:
                    tag = Tag.objects.get(id=tag_id, cliente=media_file.cliente)
                    FileTag.objects.create(
                        file=media_file,
                        tag=tag,
                        cliente=media_file.cliente
                    )
                except Tag.DoesNotExist:
                    pass
        
        # Atualizar quota do usuário
        StorageService.update_user_storage(user, file.size, 'add')
        
        return media_file


class MidiaSerializer(serializers.ModelSerializer):
    """Serializer para modelo Midia legado."""
    
    uploader = UserSerializer(read_only=True)
    
    class Meta:
        model = Midia
        fields = [
            'id', 'url', 'caption', 'tags', 'uploader',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploader', 'created_at', 'updated_at']


class BlocoTextoSerializer(serializers.ModelSerializer):
    """Serializer para blocos de texto."""
    
    creator = UserSerializer(read_only=True)
    
    class Meta:
        model = BlocoTexto
        fields = [
            'id', 'title', 'content', 'tags', 'creator',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']