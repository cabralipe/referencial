#!/usr/bin/env python
"""Script para testar a correção do PerguntaAdmin."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from core.models import Usuario
from curriculum.models import GT, Pergunta
from curriculum.admin import PerguntaAdmin

def test_pergunta_admin_fix():
    """Testa se a correção do PerguntaAdmin funciona."""
    
    print("=== TESTE DA CORREÇÃO DO PERGUNTAADMIN ===")
    
    # Criar uma requisição fake
    factory = RequestFactory()
    
    # Testar com super admin
    print("\n1. TESTANDO COM SUPER ADMIN (super@test.com):")
    super_user = Usuario.objects.get(email='super@test.com')
    request = factory.get('/admin/curriculum/pergunta/add/')
    request.user = super_user
    
    pergunta_admin = PerguntaAdmin(Pergunta, site)
    
    print(f"Usuário: {super_user.email}")
    print(f"Role: {super_user.role}")
    print(f"Cliente ID: {super_user.cliente_id}")
    
    # Testar o método formfield_for_manytomany
    gts_field = pergunta_admin.formfield_for_manytomany(
        Pergunta._meta.get_field('gts'), 
        request
    )
    
    print(f"Queryset do campo gts: {gts_field.queryset.count()} GTs")
    if gts_field.queryset.count() > 0:
        print("✅ GTs encontrados:")
        for gt in gts_field.queryset:
            print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")
    else:
        print("❌ Nenhum GT encontrado")
    
    # Testar com usuário normal
    print("\n2. TESTANDO COM USUÁRIO NORMAL (normal_admin@test.com):")
    normal_user = Usuario.objects.get(email='normal_admin@test.com')
    request2 = factory.get('/admin/curriculum/pergunta/add/')
    request2.user = normal_user
    
    print(f"Usuário: {normal_user.email}")
    print(f"Role: {normal_user.role}")
    print(f"Cliente ID: {normal_user.cliente_id}")
    
    gts_field_normal = pergunta_admin.formfield_for_manytomany(
        Pergunta._meta.get_field('gts'), 
        request2
    )
    
    print(f"Queryset do campo gts: {gts_field_normal.queryset.count()} GTs")
    if gts_field_normal.queryset.count() > 0:
        print("✅ GTs encontrados:")
        for gt in gts_field_normal.queryset:
            print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")
    else:
        print("❌ Nenhum GT encontrado (esperado para cliente sem GTs)")

if __name__ == '__main__':
    test_pergunta_admin_fix()