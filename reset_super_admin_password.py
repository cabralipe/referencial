#!/usr/bin/env python3
"""
Script para verificar e resetar a senha do usuário super@test.com
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario
from django.contrib.auth import authenticate

def reset_super_admin_password():
    """Verifica e reseta a senha do usuário super@test.com para 123456"""
    print("=== Reset de Senha do Super Admin ===\n")
    
    try:
        # Verificar se o usuário existe
        user = Usuario.objects.get(email='super@test.com')
        print(f"✅ Usuário encontrado:")
        print(f"   Email: {user.email}")
        print(f"   Nome: {user.nome}")
        print(f"   Role: {user.role}")
        print(f"   Ativo: {user.is_active}")
        print(f"   Cliente: {user.cliente.nome if user.cliente else 'Sem cliente'}")
        
        # Testar a senha atual
        print(f"\n🔐 Testando senha atual '123456'...")
        auth_user = authenticate(email='super@test.com', password='123456')
        
        if auth_user:
            print("✅ Senha '123456' já está funcionando!")
            return
        else:
            print("❌ Senha '123456' não funciona. Resetando...")
            
        # Resetar a senha
        user.set_password('123456')
        user.save()
        print("✅ Senha resetada para '123456'")
        
        # Verificar se a nova senha funciona
        print(f"\n🔐 Testando nova senha...")
        auth_user = authenticate(email='super@test.com', password='123456')
        
        if auth_user:
            print("✅ Login funcionando! Senha '123456' confirmada.")
        else:
            print("❌ Erro: Ainda não consegue fazer login após reset.")
            
    except Usuario.DoesNotExist:
        print("❌ Usuário super@test.com não encontrado!")
        print("Criando usuário super@test.com...")
        
        # Criar o usuário se não existir
        user = Usuario.objects.create_user(
            email='super@test.com',
            password='123456',
            nome='Super Admin Teste',
            role=Usuario.Role.SUPER_ADMIN
        )
        print("✅ Usuário super@test.com criado com sucesso!")
        print(f"   Email: {user.email}")
        print(f"   Nome: {user.nome}")
        print(f"   Role: {user.role}")
        print(f"   Senha: 123456")
        
        # Testar login
        auth_user = authenticate(email='super@test.com', password='123456')
        if auth_user:
            print("✅ Login funcionando!")
        else:
            print("❌ Erro: Não consegue fazer login após criação.")
    
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == '__main__':
    reset_super_admin_password()