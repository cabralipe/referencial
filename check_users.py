#!/usr/bin/env python
"""Script para verificar usuários disponíveis."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.models import Usuario

def check_users():
    """Verifica usuários disponíveis."""
    
    print("=== USUÁRIOS DISPONÍVEIS ===")
    
    users = Usuario.objects.all()
    print(f"Total de usuários: {users.count()}")
    
    for user in users:
        print(f"  - {user.email} (role: {user.role})")
    
    print()
    
    # Verificar super admins
    super_admins = Usuario.objects.filter(role=Usuario.Role.SUPER_ADMIN)
    print(f"Super Admins: {super_admins.count()}")
    for user in super_admins:
        print(f"  - {user.email}")
    
    print()
    
    # Verificar usuários normais
    normal_users = Usuario.objects.exclude(role=Usuario.Role.SUPER_ADMIN)
    print(f"Usuários Normais: {normal_users.count()}")
    for user in normal_users:
        print(f"  - {user.email} (role: {user.role})")


if __name__ == "__main__":
    check_users()