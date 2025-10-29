#!/usr/bin/env python
"""Script para debugar o middleware e o sistema de filtros."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.threadlocals import get_current_cliente_id, set_current_cliente_id
from core.models import Usuario
from curriculum.models import GT

def debug_middleware():
    """Debug do sistema de filtros."""
    
    print("=== DEBUG DO SISTEMA DE FILTROS ===")
    
    # 1. Verificar estado inicial
    print(f"Cliente ID atual (inicial): {get_current_cliente_id()}")
    
    # 2. Testar com usuário super admin
    super_user = Usuario.objects.get(email='super@test.com')
    print(f"\nUsuário super admin: {super_user.email}")
    print(f"Cliente ID do usuário: {super_user.cliente_id}")
    
    # Simular o que o middleware faria
    set_current_cliente_id(super_user.cliente_id)
    print(f"Cliente ID após middleware: {get_current_cliente_id()}")
    
    # Testar queryset
    gts_super = GT.objects.all()
    print(f"GTs para super admin: {gts_super.count()}")
    
    # 3. Testar com usuário admin normal
    normal_admin = Usuario.objects.get(email='normal_admin@test.com')
    print(f"\nUsuário admin normal: {normal_admin.email}")
    print(f"Cliente ID do usuário: {normal_admin.cliente_id}")
    
    # Simular o que o middleware faria
    set_current_cliente_id(normal_admin.cliente_id)
    print(f"Cliente ID após middleware: {get_current_cliente_id()}")
    
    # Testar queryset
    gts_normal = GT.objects.all()
    print(f"GTs para admin normal: {gts_normal.count()}")
    
    # 4. Testar raw_objects
    print(f"\nTodos os GTs (raw_objects): {GT.raw_objects.filter(is_deleted=False).count()}")
    
    # 5. Verificar se há GTs para o cliente do admin normal
    gts_cliente_3 = GT.raw_objects.filter(cliente_id=3, is_deleted=False)
    print(f"GTs para cliente ID 3 (São miguel dos Campos): {gts_cliente_3.count()}")
    
    # Limpar estado
    set_current_cliente_id(None)

if __name__ == '__main__':
    debug_middleware()