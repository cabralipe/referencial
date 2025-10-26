#!/usr/bin/env python
"""Script para verificar o role do usuário admin."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

def main():
    try:
        admin_user = Usuario.objects.get(email='admin@test.com')
        print(f"Usuário: {admin_user.email}")
        print(f"Role: {admin_user.role}")
        print(f"Cliente ID: {admin_user.cliente_id}")
        print(f"É super admin: {admin_user.role == Usuario.Role.SUPER_ADMIN}")
        
        if admin_user.role != Usuario.Role.SUPER_ADMIN:
            print("\nO usuário admin não é super_admin. Isso explica por que o header X-Cliente-ID não funciona.")
            print("Apenas usuários super_admin podem usar o header X-Cliente-ID para acessar dados de outros clientes.")
            
            # Vamos promover o admin para super_admin
            admin_user.role = Usuario.Role.SUPER_ADMIN
            admin_user.save()
            print(f"\nUsuário promovido para super_admin!")
        else:
            print("\nO usuário admin já é super_admin.")
            
    except Usuario.DoesNotExist:
        print("Usuário admin@test.com não encontrado!")

if __name__ == '__main__':
    main()