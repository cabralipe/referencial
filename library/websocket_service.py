"""Serviço para envio de notificações WebSocket da biblioteca de mídia."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class MediaWebSocketService:
    """Serviço para envio de notificações WebSocket da biblioteca de mídia."""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def _send_to_group(self, group_name: str, event_type: str, payload: Dict[str, Any]):
        """Envia mensagem para um grupo específico."""
        if not self.channel_layer:
            logger.warning("Channel layer não configurado")
            return
            
        try:
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    "type": event_type,
                    "payload": payload
                }
            )
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem WebSocket: {e}")
    
    def _get_user_cliente_id(self, user: User) -> Optional[str]:
        """Obtém o cliente_id do usuário."""
        return getattr(user, 'cliente_id', None)
    
    def notify_file_uploaded(self, media_file, user: User):
        """Notifica sobre upload de arquivo."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": media_file.id,
            "name": media_file.name,
            "file_type": media_file.file_type,
            "size": media_file.size,
            "folder_id": media_file.folder_id,
            "created_by": {
                "id": media_file.created_by.id,
                "username": media_file.created_by.username
            },
            "created_at": media_file.created_at.isoformat(),
            "thumbnail_url": media_file.thumbnail.url if media_file.thumbnail else None
        }
        
        # Notificar grupo geral da biblioteca
        self._send_to_group(
            f"media_library.{cliente_id}",
            "file_uploaded",
            payload
        )
        
        # Notificar grupo da pasta específica
        if media_file.folder_id:
            self._send_to_group(
                f"media_folder.{cliente_id}.{media_file.folder_id}",
                "file_uploaded",
                payload
            )
    
    def notify_file_updated(self, media_file, user: User, changes: Dict[str, Any] = None):
        """Notifica sobre atualização de arquivo."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": media_file.id,
            "name": media_file.name,
            "description": media_file.description,
            "is_public": media_file.is_public,
            "folder_id": media_file.folder_id,
            "updated_at": media_file.updated_at.isoformat(),
            "changes": changes or {}
        }
        
        # Notificar grupos relevantes
        self._send_to_group(
            f"media_library.{cliente_id}",
            "file_updated",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{media_file.id}",
            "file_updated",
            payload
        )
        
        if media_file.folder_id:
            self._send_to_group(
                f"media_folder.{cliente_id}.{media_file.folder_id}",
                "file_updated",
                payload
            )
    
    def notify_file_deleted(self, file_id: int, folder_id: Optional[int], user: User):
        """Notifica sobre exclusão de arquivo."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": file_id,
            "folder_id": folder_id,
            "deleted_at": None  # Será preenchido pelo frontend
        }
        
        # Notificar grupos relevantes
        self._send_to_group(
            f"media_library.{cliente_id}",
            "file_deleted",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{file_id}",
            "file_deleted",
            payload
        )
        
        if folder_id:
            self._send_to_group(
                f"media_folder.{cliente_id}.{folder_id}",
                "file_deleted",
                payload
            )
    
    def notify_file_moved(self, media_file, old_folder_id: Optional[int], user: User):
        """Notifica sobre movimentação de arquivo."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": media_file.id,
            "name": media_file.name,
            "old_folder_id": old_folder_id,
            "new_folder_id": media_file.folder_id,
            "moved_at": media_file.updated_at.isoformat()
        }
        
        # Notificar grupo geral
        self._send_to_group(
            f"media_library.{cliente_id}",
            "file_moved",
            payload
        )
        
        # Notificar pasta antiga
        if old_folder_id:
            self._send_to_group(
                f"media_folder.{cliente_id}.{old_folder_id}",
                "file_moved",
                payload
            )
        
        # Notificar pasta nova
        if media_file.folder_id:
            self._send_to_group(
                f"media_folder.{cliente_id}.{media_file.folder_id}",
                "file_moved",
                payload
            )
    
    def notify_folder_created(self, media_folder, user: User):
        """Notifica sobre criação de pasta."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": media_folder.id,
            "name": media_folder.name,
            "description": media_folder.description,
            "parent_id": media_folder.parent_id,
            "is_public": media_folder.is_public,
            "created_by": {
                "id": media_folder.created_by.id,
                "username": media_folder.created_by.username
            },
            "created_at": media_folder.created_at.isoformat()
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "folder_created",
            payload
        )
    
    def notify_folder_updated(self, media_folder, user: User, changes: Dict[str, Any] = None):
        """Notifica sobre atualização de pasta."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": media_folder.id,
            "name": media_folder.name,
            "description": media_folder.description,
            "is_public": media_folder.is_public,
            "updated_at": media_folder.updated_at.isoformat(),
            "changes": changes or {}
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "folder_updated",
            payload
        )
    
    def notify_folder_deleted(self, folder_id: int, parent_id: Optional[int], user: User):
        """Notifica sobre exclusão de pasta."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "id": folder_id,
            "parent_id": parent_id,
            "deleted_at": None  # Será preenchido pelo frontend
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "folder_deleted",
            payload
        )
    
    def notify_file_shared(self, file_share, user: User):
        """Notifica sobre compartilhamento de arquivo."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "file_id": file_share.file.id,
            "shared_with": {
                "id": file_share.shared_with.id,
                "username": file_share.shared_with.username
            },
            "permission": file_share.permission,
            "shared_by": {
                "id": user.id,
                "username": user.username
            },
            "shared_at": file_share.created_at.isoformat()
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "file_shared",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{file_share.file.id}",
            "share_added",
            payload
        )
    
    def notify_file_unshared(self, file_id: int, shared_with_id: int, user: User):
        """Notifica sobre cancelamento de compartilhamento."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "file_id": file_id,
            "shared_with_id": shared_with_id,
            "unshared_by": {
                "id": user.id,
                "username": user.username
            },
            "unshared_at": None  # Será preenchido pelo frontend
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "file_unshared",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{file_id}",
            "share_removed",
            payload
        )
    
    def notify_upload_progress(self, upload_id: str, progress: int, user: User):
        """Notifica sobre progresso de upload."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "upload_id": upload_id,
            "progress": progress,
            "timestamp": None  # Será preenchido pelo frontend
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "upload_progress",
            payload
        )
    
    def notify_processing_started(self, media_file, user: User):
        """Notifica sobre início de processamento."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "file_id": media_file.id,
            "file_name": media_file.name,
            "processing_type": "thumbnail_generation",
            "started_at": None  # Será preenchido pelo frontend
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "processing_started",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{media_file.id}",
            "processing_update",
            payload
        )
    
    def notify_processing_completed(self, media_file, user: User):
        """Notifica sobre conclusão de processamento."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "file_id": media_file.id,
            "file_name": media_file.name,
            "processing_type": "thumbnail_generation",
            "thumbnail_url": media_file.thumbnail.url if media_file.thumbnail else None,
            "completed_at": None  # Será preenchido pelo frontend
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "processing_completed",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{media_file.id}",
            "processing_update",
            payload
        )
    
    def notify_processing_failed(self, file_id: int, file_name: str, error: str, user: User):
        """Notifica sobre falha no processamento."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "file_id": file_id,
            "file_name": file_name,
            "processing_type": "thumbnail_generation",
            "error": error,
            "failed_at": None  # Será preenchido pelo frontend
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "processing_failed",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{file_id}",
            "processing_update",
            payload
        )
    
    def notify_version_created(self, file_version, user: User):
        """Notifica sobre criação de nova versão."""
        cliente_id = self._get_user_cliente_id(user)
        if not cliente_id:
            return
            
        payload = {
            "file_id": file_version.file.id,
            "version_number": file_version.version_number,
            "size": file_version.size,
            "created_by": {
                "id": file_version.created_by.id,
                "username": file_version.created_by.username
            },
            "created_at": file_version.created_at.isoformat(),
            "comment": file_version.comment
        }
        
        self._send_to_group(
            f"media_library.{cliente_id}",
            "version_created",
            payload
        )
        
        self._send_to_group(
            f"media_file.{cliente_id}.{file_version.file.id}",
            "version_created",
            payload
        )


# Instância global do serviço
media_websocket_service = MediaWebSocketService()