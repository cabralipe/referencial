"""Modelos da biblioteca reutilizável de mídia e blocos."""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from core.mixins import TenantModel, TimeStampedModel


class UserProfile(models.Model):
    """Perfil do usuário com configurações de armazenamento e permissões da Media Library."""
    
    class MediaRole(models.TextChoices):
        ADMIN = "admin", "Administrador"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Visualizador"
        GUEST = "guest", "Convidado"
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="media_profile"
    )
    storage_quota = models.BigIntegerField(default=1073741824)  # 1GB
    storage_used = models.BigIntegerField(default=0)
    media_role = models.CharField(
        max_length=10, 
        choices=MediaRole.choices, 
        default=MediaRole.VIEWER,
        help_text="Perfil específico para a Media Library"
    )
    can_upload = models.BooleanField(default=True, help_text="Pode fazer upload de arquivos")
    can_create_folders = models.BooleanField(default=True, help_text="Pode criar pastas")
    can_manage_tags = models.BooleanField(default=False, help_text="Pode gerenciar tags")
    can_share_files = models.BooleanField(default=True, help_text="Pode compartilhar arquivos")
    can_delete_own = models.BooleanField(default=True, help_text="Pode deletar próprios arquivos")
    can_delete_others = models.BooleanField(default=False, help_text="Pode deletar arquivos de outros")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self) -> str:
        return f"Profile: {self.user.email}"

    @property
    def storage_used_mb(self) -> float:
        return self.storage_used / (1024 * 1024)

    @property
    def storage_quota_mb(self) -> float:
        return self.storage_quota / (1024 * 1024)

    @property
    def storage_percentage(self) -> float:
        if self.storage_quota == 0:
            return 0
        return (self.storage_used / self.storage_quota) * 100
    
    def get_effective_media_role(self) -> str:
        """Retorna o papel efetivo baseado no role do usuário e media_role."""
        user_role = getattr(self.user, 'role', 'leitor')
        
        # Super admin sempre é admin na media library
        if user_role == 'super_admin':
            return self.MediaRole.ADMIN
            
        # Admin do cliente sempre é admin na media library
        if user_role == 'admin_cliente':
            return self.MediaRole.ADMIN
            
        # Articulador padrão é editor, mas pode ser customizado
        if user_role == 'articulador':
            return self.media_role if self.media_role in [self.MediaRole.ADMIN, self.MediaRole.EDITOR] else self.MediaRole.EDITOR
            
        # Outros seguem o media_role definido
        return self.media_role
    
    def can_perform_action(self, action: str) -> bool:
        """Verifica se o usuário pode realizar uma ação específica."""
        effective_role = self.get_effective_media_role()
        
        # Admin pode tudo
        if effective_role == self.MediaRole.ADMIN:
            return True
            
        # Mapear ações para permissões
        action_permissions = {
            'upload': self.can_upload and effective_role in [self.MediaRole.EDITOR, self.MediaRole.ADMIN],
            'create_folder': self.can_create_folders and effective_role in [self.MediaRole.EDITOR, self.MediaRole.ADMIN],
            'manage_tags': self.can_manage_tags and effective_role == self.MediaRole.ADMIN,
            'share_files': self.can_share_files and effective_role in [self.MediaRole.EDITOR, self.MediaRole.ADMIN],
            'delete_own': self.can_delete_own and effective_role in [self.MediaRole.EDITOR, self.MediaRole.ADMIN],
            'delete_others': self.can_delete_others and effective_role == self.MediaRole.ADMIN,
            'view_public': True,  # Todos podem ver arquivos públicos
            'view_shared': effective_role in [self.MediaRole.VIEWER, self.MediaRole.EDITOR, self.MediaRole.ADMIN],
        }
        
        return action_permissions.get(action, False)
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Obtém ou cria um perfil para o usuário com configurações padrão baseadas no role."""
        profile, created = cls.objects.get_or_create(
            user=user,
            defaults=cls._get_default_permissions_for_role(user)
        )
        return profile
    
    @classmethod
    def _get_default_permissions_for_role(cls, user):
        """Retorna permissões padrão baseadas no role do usuário."""
        user_role = getattr(user, 'role', 'leitor')
        
        if user_role in ['super_admin', 'admin_cliente']:
            return {
                'media_role': cls.MediaRole.ADMIN,
                'can_upload': True,
                'can_create_folders': True,
                'can_manage_tags': True,
                'can_share_files': True,
                'can_delete_own': True,
                'can_delete_others': True,
                'storage_quota': 5368709120,  # 5GB para admins
            }
        elif user_role == 'articulador':
            return {
                'media_role': cls.MediaRole.EDITOR,
                'can_upload': True,
                'can_create_folders': True,
                'can_manage_tags': False,
                'can_share_files': True,
                'can_delete_own': True,
                'can_delete_others': False,
                'storage_quota': 2147483648,  # 2GB para articuladores
            }
        elif user_role == 'membro_gt':
            return {
                'media_role': cls.MediaRole.VIEWER,
                'can_upload': True,
                'can_create_folders': False,
                'can_manage_tags': False,
                'can_share_files': False,
                'can_delete_own': True,
                'can_delete_others': False,
                'storage_quota': 1073741824,  # 1GB para membros
            }
        else:  # leitor
            return {
                'media_role': cls.MediaRole.GUEST,
                'can_upload': False,
                'can_create_folders': False,
                'can_manage_tags': False,
                'can_share_files': False,
                'can_delete_own': False,
                'can_delete_others': False,
                'storage_quota': 104857600,  # 100MB para leitores
            }


class MediaFolder(TenantModel):
    """Pasta para organização hierárquica de arquivos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Pasta Pai"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="media_folders",
        verbose_name="Proprietário"
    )
    is_public = models.BooleanField(default=False, verbose_name="Público")

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "owner"]),
            models.Index(fields=["parent"]),
        ]
        ordering = ("name",)
        verbose_name = "Pasta de Mídia"
        verbose_name_plural = "Pastas de Mídia"

    def __str__(self) -> str:
        return self.name

    @property
    def full_path(self) -> str:
        """Retorna o caminho completo da pasta."""
        if self.parent:
            return f"{self.parent.full_path}/{self.name}"
        return self.name

    def get_descendants(self):
        """Retorna todas as subpastas recursivamente."""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Tag(TenantModel):
    """Tags para categorização de arquivos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nome")
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name="Cor")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tags",
        verbose_name="Criado por"
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "name"]),
        ]
        ordering = ("name",)
        unique_together = ("cliente", "name")
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:
        return self.name


class MediaFile(TenantModel):
    """Arquivo de mídia com metadados e versionamento."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome")
    original_name = models.CharField(max_length=255, verbose_name="Nome Original")
    file_type = models.CharField(max_length=100, verbose_name="Tipo de Arquivo")
    file_size = models.BigIntegerField(verbose_name="Tamanho do Arquivo")
    file = models.FileField(
        upload_to='media_files/%Y/%m/%d/',
        verbose_name="Arquivo"
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Miniatura"
    )
    folder = models.ForeignKey(
        MediaFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="files",
        verbose_name="Pasta"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="media_files",
        verbose_name="Proprietário"
    )
    is_public = models.BooleanField(default=False, verbose_name="Público")
    metadata = models.JSONField(default=dict, verbose_name="Metadados")
    tags = models.ManyToManyField(
        Tag,
        through='FileTag',
        related_name="files",
        blank=True,
        verbose_name="Tags"
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "owner"]),
            models.Index(fields=["folder"]),
            models.Index(fields=["file_type"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ("-created_at",)
        verbose_name = "Arquivo de Mídia"
        verbose_name_plural = "Arquivos de Mídia"

    def __str__(self) -> str:
        return self.name

    @property
    def file_size_mb(self) -> float:
        return self.file_size / (1024 * 1024)

    @property
    def extension(self) -> str:
        return Path(self.original_name).suffix.lower()

    @property
    def is_image(self) -> bool:
        return self.file_type.startswith('image/')

    @property
    def is_video(self) -> bool:
        return self.file_type.startswith('video/')

    @property
    def is_audio(self) -> bool:
        return self.file_type.startswith('audio/')

    @property
    def is_document(self) -> bool:
        return self.file_type in [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ]


class FileVersion(TenantModel):
    """Versões de arquivos para controle de histórico."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name="Arquivo"
    )
    version_number = models.CharField(max_length=20, verbose_name="Número da Versão")
    file_data = models.FileField(
        upload_to='file_versions/%Y/%m/%d/',
        verbose_name="Dados do Arquivo"
    )
    file_size = models.BigIntegerField(verbose_name="Tamanho do Arquivo")
    change_description = models.TextField(blank=True, verbose_name="Descrição da Mudança")

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "file"]),
        ]
        ordering = ("-created_at",)
        verbose_name = "Versão de Arquivo"
        verbose_name_plural = "Versões de Arquivos"

    def __str__(self) -> str:
        return f"{self.file.name} v{self.version_number}"


class FileTag(TenantModel):
    """Relacionamento entre arquivos e tags."""
    file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        verbose_name="Arquivo"
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name="Tag"
    )

    class Meta:
        unique_together = ("cliente", "file", "tag")
        verbose_name = "Tag de Arquivo"
        verbose_name_plural = "Tags de Arquivos"

    def __str__(self) -> str:
        return f"{self.file.name} - {self.tag.name}"


class FileShare(TenantModel):
    """Compartilhamento de arquivos com permissões."""
    PERMISSION_CHOICES = [
        ('view', 'Visualizar'),
        ('edit', 'Editar'),
        ('admin', 'Administrar'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name='shares',
        verbose_name="Arquivo"
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_files",
        verbose_name="Compartilhado com"
    )
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default='view',
        verbose_name="Nível de Permissão"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expira em"
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "file"]),
            models.Index(fields=["shared_with"]),
        ]
        unique_together = ("cliente", "file", "shared_with")
        verbose_name = "Compartilhamento de Arquivo"
        verbose_name_plural = "Compartilhamentos de Arquivos"

    def __str__(self) -> str:
        return f"{self.file.name} → {self.shared_with.email}"


# Modelos legados mantidos para compatibilidade
class Midia(TenantModel):
    """Modelo legado de mídia - mantido para compatibilidade."""
    url = models.URLField()
    legenda = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="midias_enviadas",
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "created_at"]),
        ]
        ordering = ("-created_at",)
        verbose_name = "Mídia (Legado)"
        verbose_name_plural = "Mídias (Legado)"

    def __str__(self) -> str:  # pragma: no cover
        return self.url


class BlocoTexto(TenantModel):
    """Bloco de texto reutilizável."""
    titulo = models.CharField(max_length=255)
    conteudo_html = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocos_criados",
    )

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "titulo"]),
        ]
        ordering = ("titulo",)
        verbose_name = "Bloco de Texto"
        verbose_name_plural = "Blocos de Texto"

    def __str__(self) -> str:  # pragma: no cover
        return self.titulo

    @property
    def etag(self) -> str:
        return f"W/\"blocotexto-{self.pk}-v{int(self.updated_at.timestamp())}\""
