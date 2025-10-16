#!/usr/bin/env python
"""Script para testar o envio de mensagens WebSocket."""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def test_websocket_message():
    """Testa o envio de uma mensagem WebSocket."""
    channel_layer = get_channel_layer()
    
    if not channel_layer:
        print("❌ Channel layer não configurado")
        return
    
    print("🔧 Enviando mensagem de teste...")
    
    # Enviar mensagem para o grupo de teste
    async_to_sync(channel_layer.group_send)(
        "media_library.test",
        {
            "type": "file_uploaded",
            "payload": {
                "id": 999,
                "name": "arquivo_teste.jpg",
                "file_type": "image",
                "size": 1024,
                "folder_id": None,
                "created_by": {
                    "id": 1,
                    "username": "teste"
                },
                "created_at": "2025-01-08T14:30:00Z",
                "thumbnail_url": None
            }
        }
    )
    
    print("✅ Mensagem enviada com sucesso!")

if __name__ == "__main__":
    test_websocket_message()