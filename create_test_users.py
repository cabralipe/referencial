#!/usr/bin/env python
"""Script para criar usuários de teste para desenvolvimento."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Cliente, Usuario

def create_test_users():
    """Cria usuários de teste para cada role."""
    
    # 1. Criar cliente de teste
    cliente_teste, created = Cliente.objects.get_or_create(
        slug='cliente-teste',
        defaults={
            'nome': 'Cliente de Teste',
            'ativo': True
        }
    )
    
    if created:
        print(f"✅ Cliente criado: {cliente_teste.nome}")
    else:
        print(f"ℹ️  Cliente já existe: {cliente_teste.nome}")
    
    # 2. Definir usuários para criar
    usuarios_teste = [
        {
            'email': 'super@test.com',
            'nome': 'Super Admin Teste',
            'role': Usuario.Role.SUPER_ADMIN,
            'cliente': None,  # Super admin não tem cliente
            'is_staff': True,
            'is_superuser': True
        },
        {
            'email': 'admin@test.com',
            'nome': 'Admin Cliente Teste',
            'role': Usuario.Role.ADMIN_CLIENTE,
            'cliente': cliente_teste,
            'is_staff': False,
            'is_superuser': False
        },
        {
            'email': 'articulador@test.com',
            'nome': 'Articulador Teste',
            'role': Usuario.Role.ARTICULADOR,
            'cliente': cliente_teste,
            'is_staff': False,
            'is_superuser': False
        },
        {
            'email': 'membro@test.com',
            'nome': 'Membro GT Teste',
            'role': Usuario.Role.MEMBRO_GT,
            'cliente': cliente_teste,
            'is_staff': False,
            'is_superuser': False
        },
        {
            'email': 'leitor@test.com',
            'nome': 'Leitor Teste',
            'role': Usuario.Role.LEITOR,
            'cliente': cliente_teste,
            'is_staff': False,
            'is_superuser': False
        }
    ]
    
    # 3. Criar cada usuário
    senha_padrao = '123456'
    
    for user_data in usuarios_teste:
        email = user_data['email']
        
        # Verificar se usuário já existe
        if Usuario.objects.filter(email=email).exists():
            print(f"ℹ️  Usuário já existe: {email}")
            continue
        
        # Criar usuário
        try:
            usuario = Usuario.objects.create_user(
                email=email,
                password=senha_padrao,
                nome=user_data['nome'],
                role=user_data['role'],
                cliente=user_data['cliente'],
                is_staff=user_data['is_staff'],
                is_superuser=user_data['is_superuser']
            )
            print(f"✅ Usuário criado: {email} ({user_data['role']})")
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário {email}: {e}")
    
    print("\n📋 Resumo dos usuários de teste:")
    print("=" * 50)
    print("Email: super@test.com | Role: SUPER_ADMIN | Senha: 123456")
    print("Email: admin@test.com | Role: ADMIN_CLIENTE | Senha: 123456")
    print("Email: articulador@test.com | Role: ARTICULADOR | Senha: 123456")
    print("Email: membro@test.com | Role: MEMBRO_GT | Senha: 123456")
    print("Email: leitor@test.com | Role: LEITOR | Senha: 123456")
    print("=" * 50)
    print("🎉 Usuários de teste criados com sucesso!")

if __name__ == '__main__':
    create_test_users()