#!/usr/bin/env python
"""Script para criar um usuário admin normal (não super admin) para teste."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Cliente, Usuario

def create_normal_admin():
    """Cria um usuário admin normal para teste."""
    
    # Buscar o cliente "São miguel dos Campos"
    cliente_sao_miguel = Cliente.objects.get(nome="Saõ miguel dos Campos")
    
    # Criar usuário admin normal
    normal_admin, created = Usuario.objects.get_or_create(
        email='normal_admin@test.com',
        defaults={
            'nome': 'Admin Normal Teste',
            'role': Usuario.Role.ADMIN_CLIENTE,
            'cliente': cliente_sao_miguel,
            'is_staff': True,
            'is_superuser': False
        }
    )
    
    if created:
        normal_admin.set_password('123456')
        normal_admin.save()
        print(f"✅ Usuário criado: {normal_admin.email}")
    else:
        print(f"ℹ️  Usuário já existe: {normal_admin.email}")
    
    print(f"Role: {normal_admin.role}")
    print(f"Cliente: {normal_admin.cliente.nome}")
    print(f"É super admin: {normal_admin.role == Usuario.Role.SUPER_ADMIN}")

if __name__ == '__main__':
    create_normal_admin()