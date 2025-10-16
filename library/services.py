"""Serviços para processamento de arquivos de mídia."""

from __future__ import annotations

import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps


class FileProcessingService:
    """Serviço para processamento de arquivos de mídia."""

    # Tamanhos de thumbnail
    THUMBNAIL_SIZE = (300, 300)
    PREVIEW_SIZE = (800, 600)

    # Tipos de arquivo suportados para thumbnail
    SUPPORTED_IMAGE_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
    }

    @classmethod
    def get_file_type(cls, file: UploadedFile) -> str:
        """Detecta o tipo MIME do arquivo."""
        # Primeiro tenta pelo content_type do upload
        if file.content_type:
            return file.content_type
        
        # Fallback para detecção por extensão
        mime_type, _ = mimetypes.guess_type(file.name)
        return mime_type or 'application/octet-stream'

    @classmethod
    def get_file_category(cls, file_type: str) -> str:
        """Retorna a categoria do arquivo baseada no tipo MIME."""
        if file_type.startswith('image/'):
            return 'image'
        elif file_type.startswith('video/'):
            return 'video'
        elif file_type.startswith('audio/'):
            return 'audio'
        elif file_type in [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        ]:
            return 'document'
        else:
            return 'other'

    @classmethod
    def generate_thumbnail(cls, file: UploadedFile) -> Optional[ContentFile]:
        """Gera thumbnail para imagens."""
        file_type = cls.get_file_type(file)
        
        if file_type not in cls.SUPPORTED_IMAGE_TYPES:
            return None

        try:
            # Abrir a imagem
            image = Image.open(file)
            
            # Converter para RGB se necessário (para PNG com transparência)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Criar fundo branco
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # Redimensionar mantendo proporção
            image = ImageOps.fit(image, cls.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            # Salvar em buffer
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            # Criar ContentFile
            thumbnail_name = f"thumb_{Path(file.name).stem}.jpg"
            return ContentFile(buffer.getvalue(), name=thumbnail_name)
            
        except Exception as e:
            # Log do erro (em produção, usar logging adequado)
            print(f"Erro ao gerar thumbnail: {e}")
            return None

    @classmethod
    def extract_metadata(cls, file: UploadedFile) -> dict:
        """Extrai metadados do arquivo."""
        metadata = {
            'original_name': file.name,
            'size': file.size,
            'content_type': cls.get_file_type(file),
            'category': cls.get_file_category(cls.get_file_type(file)),
        }

        # Para imagens, extrair dimensões
        if metadata['category'] == 'image':
            try:
                image = Image.open(file)
                metadata.update({
                    'width': image.width,
                    'height': image.height,
                    'format': image.format,
                    'mode': image.mode,
                })
                
                # Extrair EXIF se disponível
                if hasattr(image, '_getexif') and image._getexif():
                    exif = image._getexif()
                    if exif:
                        metadata['exif'] = {
                            str(k): str(v) for k, v in exif.items() 
                            if isinstance(v, (str, int, float))
                        }
                        
            except Exception as e:
                print(f"Erro ao extrair metadados da imagem: {e}")

        return metadata

    @classmethod
    def validate_file(cls, file: UploadedFile) -> Tuple[bool, str]:
        """Valida se o arquivo pode ser processado."""
        # Verificar tamanho máximo (100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if file.size > max_size:
            return False, f"Arquivo muito grande. Máximo permitido: {max_size // (1024*1024)}MB"

        # Verificar extensão
        allowed_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # Imagens
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',   # Vídeos
            '.mp3', '.wav', '.ogg', '.m4a', '.flac',           # Áudios
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',          # Documentos
            '.ppt', '.pptx', '.txt', '.rtf',                   # Documentos
            '.zip', '.rar', '.7z', '.tar', '.gz',              # Arquivos
        }
        
        file_ext = Path(file.name).suffix.lower()
        if file_ext not in allowed_extensions:
            return False, f"Tipo de arquivo não permitido: {file_ext}"

        return True, "Arquivo válido"

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitiza o nome do arquivo removendo caracteres perigosos."""
        # Manter apenas caracteres alfanuméricos, pontos, hífens e underscores
        import re
        
        # Extrair nome e extensão
        path = Path(filename)
        name = path.stem
        ext = path.suffix
        
        # Sanitizar o nome
        name = re.sub(r'[^\w\-_\.]', '_', name)
        name = re.sub(r'_+', '_', name)  # Múltiplos underscores viram um
        name = name.strip('_')  # Remove underscores do início/fim
        
        # Limitar tamanho
        if len(name) > 100:
            name = name[:100]
        
        return f"{name}{ext}"


class StorageService:
    """Serviço para gerenciamento de armazenamento."""

    @classmethod
    def update_user_storage(cls, user, file_size: int, operation: str = 'add'):
        """Atualiza o uso de armazenamento do usuário."""
        from .models import UserProfile
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if operation == 'add':
            profile.storage_used += file_size
        elif operation == 'remove':
            profile.storage_used = max(0, profile.storage_used - file_size)
        
        profile.save(update_fields=['storage_used'])
        return profile

    @classmethod
    def check_storage_quota(cls, user, file_size: int) -> Tuple[bool, str]:
        """Verifica se o usuário tem quota suficiente."""
        from .models import UserProfile
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if profile.storage_used + file_size > profile.storage_quota:
            used_mb = profile.storage_used_mb
            quota_mb = profile.storage_quota_mb
            return False, f"Quota excedida. Usado: {used_mb:.1f}MB / {quota_mb:.1f}MB"
        
        return True, "Quota disponível"


class VersionService:
    """Serviço para controle de versões de arquivos."""

    @classmethod
    def create_version(cls, media_file, new_file: UploadedFile, description: str = ""):
        """Cria uma nova versão do arquivo."""
        from .models import FileVersion
        
        # Determinar número da próxima versão
        last_version = media_file.versions.order_by('-created_at').first()
        if last_version:
            try:
                last_num = float(last_version.version_number)
                new_version_num = f"{last_num + 0.1:.1f}"
            except ValueError:
                new_version_num = "2.0"
        else:
            new_version_num = "1.0"

        # Criar nova versão
        version = FileVersion.objects.create(
            file=media_file,
            version_number=new_version_num,
            file_data=new_file,
            file_size=new_file.size,
            change_description=description,
            cliente=media_file.cliente
        )

        return version

    @classmethod
    def restore_version(cls, media_file, version):
        """Restaura uma versão específica como atual."""
        # Criar backup da versão atual
        current_version = cls.create_version(
            media_file,
            media_file.file,
            f"Backup antes de restaurar v{version.version_number}"
        )

        # Atualizar arquivo principal
        media_file.file = version.file_data
        media_file.file_size = version.file_size
        media_file.save(update_fields=['file', 'file_size', 'updated_at'])

        return current_version