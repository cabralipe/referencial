"""Configuração do Django Admin para a biblioteca de mídia."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    MediaFile, MediaFolder, Tag, FileVersion, 
    FileTag, FileShare, UserProfile, Midia, BlocoTexto
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin para perfis de usuário."""
    
    list_display = ('user', 'storage_used_mb', 'storage_quota_mb', 'storage_percentage')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('storage_used', 'storage_percentage')
    
    def storage_used_mb(self, obj):
        return f"{obj.storage_used_mb:.1f} MB"
    storage_used_mb.short_description = "Armazenamento Usado"
    
    def storage_quota_mb(self, obj):
        return f"{obj.storage_quota_mb:.1f} MB"
    storage_quota_mb.short_description = "Quota"
    
    def storage_percentage(self, obj):
        percentage = obj.storage_percentage
        color = 'green' if percentage < 70 else 'orange' if percentage < 90 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    storage_percentage.short_description = "% Usado"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin para tags."""
    
    list_display = ('name', 'color_display', 'created_by', 'files_count', 'created_at')
    list_filter = ('created_by', 'color', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('files_count',)
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = "Cor"
    
    def files_count(self, obj):
        return obj.files.count()
    files_count.short_description = "Arquivos"


@admin.register(MediaFolder)
class MediaFolderAdmin(admin.ModelAdmin):
    """Admin para pastas de mídia."""
    
    list_display = ('name', 'parent', 'owner', 'is_public', 'files_count', 'created_at')
    list_filter = ('is_public', 'created_at', 'owner')
    search_fields = ('name', 'description')
    readonly_fields = ('files_count', 'total_size')
    
    def files_count(self, obj):
        return obj.files.filter(is_active=True).count()
    files_count.short_description = "Arquivos"
    
    def total_size(self, obj):
        total = sum(f.file_size for f in obj.files.filter(is_active=True))
        return f"{total / (1024*1024):.1f} MB"
    total_size.short_description = "Tamanho Total"


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    """Admin para arquivos de mídia."""
    
    list_display = ('name', 'file_type', 'file_size_mb', 'owner', 'folder', 'is_public', 'created_at')
    list_filter = ('file_type', 'is_public', 'created_at', 'owner')
    search_fields = ('name', 'original_name')
    readonly_fields = ('file_size', 'file_type', 'metadata', 'thumbnail_preview')
    
    def file_size_mb(self, obj):
        return f"{obj.file_size / (1024*1024):.1f} MB"
    file_size_mb.short_description = "Tamanho"
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.thumbnail.url
            )
        return "Sem thumbnail"
    thumbnail_preview.short_description = "Preview"


@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    """Admin para versões de arquivo."""
    
    list_display = ('file', 'version_number', 'file_size_mb', 'change_description', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('file__name', 'change_description')
    readonly_fields = ('file_size',)
    
    def file_size_mb(self, obj):
        return f"{obj.file_size / (1024*1024):.1f} MB"
    file_size_mb.short_description = "Tamanho"


@admin.register(FileTag)
class FileTagAdmin(admin.ModelAdmin):
    """Admin para tags de arquivo."""
    
    list_display = ('file', 'tag', 'created_at')
    list_filter = ('tag', 'created_at')
    search_fields = ('file__name', 'tag__name')


@admin.register(FileShare)
class FileShareAdmin(admin.ModelAdmin):
    """Admin para compartilhamentos."""
    
    list_display = ('file', 'shared_with', 'permission_level', 'expires_at', 'created_at')
    list_filter = ('permission_level', 'created_at')
    search_fields = ('file__name', 'shared_with__username')


# Modelos legados
@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    """Admin para modelo Midia legado."""
    
    list_display = ("url", "uploaded_by", "created_at")
    search_fields = ("url", "legenda")
    list_filter = ("uploaded_by", "created_at")


@admin.register(BlocoTexto)
class BlocoTextoAdmin(admin.ModelAdmin):
    """Admin para blocos de texto."""
    
    list_display = ("titulo", "created_by", "updated_at")
    search_fields = ("titulo", "conteudo_html")
    list_filter = ("created_by", "created_at")
