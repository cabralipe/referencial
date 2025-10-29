#!/usr/bin/env python
"""Script para testar se a correção do GTAdmin está funcionando."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from core.models import Usuario
from curriculum.models import GT
from curriculum.admin import GTAdmin

def test_gt_admin_queryset():
    """Testa se o GTAdmin retorna todos os GTs para super admin."""
    
    # Criar uma requisição fake
    factory = RequestFactory()
    request = factory.get('/admin/curriculum/gt/')
    
    # Buscar o usuário super admin
    super_user = Usuario.objects.get(email='super@test.com')
    request.user = super_user
    
    # Criar instância do GTAdmin
    gt_admin = GTAdmin(GT, site)
    
    # Testar o queryset
    queryset = gt_admin.get_queryset(request)
    
    print(f"Usuário: {super_user.email}")
    print(f"Role: {super_user.role}")
    print(f"É super admin: {super_user.role == Usuario.Role.SUPER_ADMIN}")
    print(f"Queryset count: {queryset.count()}")
    
    if queryset.count() > 0:
        print("\n✅ GTs encontrados:")
        for gt in queryset:
            print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")
    else:
        print("\n❌ Nenhum GT encontrado")
    
    # Testar também com um usuário normal
    print("\n" + "="*50)
    print("Testando com usuário admin normal...")
    
    try:
        admin_user = Usuario.objects.get(email='admin@test.com')
        request.user = admin_user
        
        queryset_admin = gt_admin.get_queryset(request)
        
        print(f"Usuário: {admin_user.email}")
        print(f"Role: {admin_user.role}")
        print(f"Cliente ID: {admin_user.cliente_id}")
        print(f"Queryset count: {queryset_admin.count()}")
        
        if queryset_admin.count() > 0:
            print("\n✅ GTs encontrados para admin:")
            for gt in queryset_admin:
                print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")
        else:
            print("\n❌ Nenhum GT encontrado para admin (esperado se não tiver GTs do seu cliente)")
            
    except Usuario.DoesNotExist:
        print("Usuário admin@test.com não encontrado")

if __name__ == '__main__':
    test_gt_admin_queryset()