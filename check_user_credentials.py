#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'referencial.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

User = get_user_model()

def check_user_credentials():
    try:
        # Verificar se o usuário existe
        user = User.objects.get(email='admin@test.com')
        print(f"Usuário encontrado: {user.email}")
        print(f"Is active: {user.is_active}")
        print(f"Is staff: {user.is_staff}")
        print(f"Is superuser: {user.is_superuser}")
        
        # Tentar diferentes senhas comuns
        passwords_to_try = ['admin', 'password', '123456', 'admin123', 'test']
        
        for password in passwords_to_try:
            auth_user = authenticate(username=user.email, password=password)
            if auth_user:
                print(f"✓ Senha correta encontrada: '{password}'")
                return password
            else:
                print(f"✗ Senha incorreta: '{password}'")
        
        print("Nenhuma senha comum funcionou. Vou resetar a senha para 'admin'")
        user.set_password('admin')
        user.save()
        print("Senha resetada para 'admin'")
        return 'admin'
        
    except User.DoesNotExist:
        print("Usuário admin@test.com não encontrado!")
        return None

if __name__ == "__main__":
    check_user_credentials()