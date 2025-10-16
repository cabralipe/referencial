"""Consumers de WebSocket para a biblioteca de mídia."""

from __future__ import annotations

import json
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class MediaLibraryConsumer(AsyncJsonWebsocketConsumer):
    """Consumer para atualizações em tempo real da biblioteca de mídia."""
    
    async def connect(self):
        """Aceita conexão WebSocket e adiciona ao grupo da biblioteca de mídia"""
        # Verifica se o usuário está autenticado
        if isinstance(self.scope["user"], AnonymousUser):
            await self.close()
            return
        
        # Obtém o cliente_id do usuário autenticado
        self.cliente_id = getattr(self.scope["user"], "cliente_id", None)
        
        if not self.cliente_id:
            await self.close()
            return
        
        await self.accept()
        
        # Adiciona ao grupo da biblioteca de mídia
        await self.channel_layer.group_add(
            f"media_library.{self.cliente_id}",
            self.channel_name
        )
        
        # Envia mensagem de confirmação
        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'message': 'Conectado à biblioteca de mídia'
        }))

    async def disconnect(self, close_code):
        """Desconecta o usuário do grupo."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        """Processa mensagens recebidas do cliente."""
        message_type = content.get("type")
        
        if message_type == "ping":
            await self.send_json({"type": "pong"})
        elif message_type == "subscribe_folder":
            # Subscrever a atualizações de uma pasta específica
            folder_id = content.get("folder_id")
            if folder_id:
                folder_group = f"media_folder.{self.cliente_id}.{folder_id}"
                await self.channel_layer.group_add(folder_group, self.channel_name)
                await self.send_json({
                    "type": "subscription.confirmed",
                    "folder_id": folder_id
                })
        elif message_type == "unsubscribe_folder":
            # Cancelar subscrição de uma pasta específica
            folder_id = content.get("folder_id")
            if folder_id:
                folder_group = f"media_folder.{self.cliente_id}.{folder_id}"
                await self.channel_layer.group_discard(folder_group, self.channel_name)
                await self.send_json({
                    "type": "subscription.cancelled",
                    "folder_id": folder_id
                })

    # Handlers para diferentes tipos de eventos

    async def file_uploaded(self, event):
        """Notifica sobre upload de arquivo."""
        await self.send_json({
            "type": "file.uploaded",
            "payload": event["payload"]
        })

    async def file_updated(self, event):
        """Notifica sobre atualização de arquivo."""
        await self.send_json({
            "type": "file.updated",
            "payload": event["payload"]
        })

    async def file_deleted(self, event):
        """Notifica sobre exclusão de arquivo."""
        await self.send_json({
            "type": "file.deleted",
            "payload": event["payload"]
        })

    async def file_moved(self, event):
        """Notifica sobre movimentação de arquivo."""
        await self.send_json({
            "type": "file.moved",
            "payload": event["payload"]
        })

    async def folder_created(self, event):
        """Notifica sobre criação de pasta."""
        await self.send_json({
            "type": "folder.created",
            "payload": event["payload"]
        })

    async def folder_updated(self, event):
        """Notifica sobre atualização de pasta."""
        await self.send_json({
            "type": "folder.updated",
            "payload": event["payload"]
        })

    async def folder_deleted(self, event):
        """Notifica sobre exclusão de pasta."""
        await self.send_json({
            "type": "folder.deleted",
            "payload": event["payload"]
        })

    async def file_shared(self, event):
        """Notifica sobre compartilhamento de arquivo."""
        await self.send_json({
            "type": "file.shared",
            "payload": event["payload"]
        })

    async def file_unshared(self, event):
        """Notifica sobre cancelamento de compartilhamento."""
        await self.send_json({
            "type": "file.unshared",
            "payload": event["payload"]
        })

    async def upload_progress(self, event):
        """Notifica sobre progresso de upload."""
        await self.send_json({
            "type": "upload.progress",
            "payload": event["payload"]
        })

    async def processing_started(self, event):
        """Notifica sobre início de processamento de arquivo."""
        await self.send_json({
            "type": "processing.started",
            "payload": event["payload"]
        })

    async def processing_completed(self, event):
        """Notifica sobre conclusão de processamento."""
        await self.send_json({
            "type": "processing.completed",
            "payload": event["payload"]
        })

    async def processing_failed(self, event):
        """Notifica sobre falha no processamento."""
        await self.send_json({
            "type": "processing.failed",
            "payload": event["payload"]
        })


class MediaFileConsumer(AsyncJsonWebsocketConsumer):
    """Consumer para atualizações específicas de um arquivo."""
    
    async def connect(self):
        """Conecta ao grupo de um arquivo específico."""
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return
            
        self.file_id = self.scope["url_route"]["kwargs"].get("file_id")
        if not self.file_id:
            await self.close()
            return
            
        self.cliente_id = getattr(user, 'cliente_id', None)
        if not self.cliente_id:
            await self.close()
            return
            
        self.group_name = f"media_file.{self.cliente_id}.{self.file_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Desconecta do grupo do arquivo."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        """Processa mensagens do cliente."""
        message_type = content.get("type")
        
        if message_type == "ping":
            await self.send_json({"type": "pong"})

    # Handlers para eventos específicos do arquivo

    async def file_updated(self, event):
        """Notifica sobre atualização do arquivo."""
        await self.send_json({
            "type": "file.updated",
            "payload": event["payload"]
        })

    async def file_deleted(self, event):
        """Notifica sobre exclusão do arquivo."""
        await self.send_json({
            "type": "file.deleted",
            "payload": event["payload"]
        })

    async def version_created(self, event):
        """Notifica sobre nova versão do arquivo."""
        await self.send_json({
            "type": "version.created",
            "payload": event["payload"]
        })

    async def share_added(self, event):
        """Notifica sobre novo compartilhamento."""
        await self.send_json({
            "type": "share.added",
            "payload": event["payload"]
        })

    async def share_removed(self, event):
        """Notifica sobre remoção de compartilhamento."""
        await self.send_json({
            "type": "share.removed",
            "payload": event["payload"]
        })

    async def processing_update(self, event):
        """Notifica sobre atualização no processamento."""
        await self.send_json({
            "type": "processing.update",
            "payload": event["payload"]
        })