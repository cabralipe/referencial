#!/usr/bin/env python
"""Script para testar se o filtro funciona para usuário admin normal."""

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

def test_normal_admin_queryset():
    """Testa se o GTAdmin filtra corretamente para admin normal."""
    
    # Criar uma requisição fake
    factory = RequestFactory()
    request = factory.get('/admin/curriculum/gt/')
    
    # Buscar o usuário admin normal
    normal_admin = Usuario.objects.get(email='normal_admin@test.com')
    request.user = normal_admin
    
    # Criar instância do GTAdmin
    gt_admin = GTAdmin(GT, site)
    
    # Testar o queryset
    queryset = gt_admin.get_queryset(request)
    
    print(f"Usuário: {normal_admin.email}")
    print(f"Role: {normal_admin.role}")
    print(f"Cliente: {normal_admin.cliente.nome}")
    print(f"É super admin: {normal_admin.role == Usuario.Role.SUPER_ADMIN}")
    print(f"Queryset count: {queryset.count()}")
    
    if queryset.count() > 0:
        print("\n✅ GTs encontrados:")
        for gt in queryset:
            print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")
    else:
        print("\n❌ Nenhum GT encontrado (esperado, pois não há GTs para 'São miguel dos Campos')")
    
    # Comparar com todos os GTs no banco
    all_gts = GT.raw_objects.filter(is_deleted=False)
    print(f"\nTotal de GTs no banco: {all_gts.count()}")
    print("Todos os GTs:")
    for gt in all_gts:
        print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")

if __name__ == '__main__':
    test_normal_admin_queryset()