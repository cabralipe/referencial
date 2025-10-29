#!/usr/bin/env python
"""Script para verificar se o usuário super@test.com é super admin."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

def main():
    try:
        super_user = Usuario.objects.get(email='super@test.com')
        print(f"Usuário: {super_user.email}")
        print(f"Role: {super_user.role}")
        print(f"Cliente ID: {super_user.cliente_id}")
        print(f"É super admin: {super_user.role == Usuario.Role.SUPER_ADMIN}")
        print(f"É staff: {super_user.is_staff}")
        print(f"É superuser: {super_user.is_superuser}")
        
        if super_user.role == Usuario.Role.SUPER_ADMIN:
            print("\n✅ O usuário é super_admin e pode usar o header X-Cliente-ID")
            print("Para ver os GTs no Django Admin, você precisa:")
            print("1. Adicionar o header X-Cliente-ID: 2 (para ver GTs do cliente 'jeremias da silva')")
            print("2. Ou associar o usuário a um cliente específico")
        else:
            print("\n❌ O usuário não é super_admin")
            
    except Usuario.DoesNotExist:
        print("Usuário super@test.com não encontrado!")

if __name__ == '__main__':
    main()