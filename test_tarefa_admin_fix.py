#!/usr/bin/env python
"""Script para testar a correção do TarefaAdmin."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from core.models import Usuario
from curriculum.models import Tarefa
from curriculum.admin import TarefaAdmin

def test_tarefa_admin_fix():
    """Testa se a correção do TarefaAdmin funciona."""
    
    print("=== TESTE DA CORREÇÃO DO TAREFAADMIN ===")
    
    # Criar uma requisição fake
    factory = RequestFactory()
    
    # Testar com super admin
    print("\n1. TESTANDO COM SUPER ADMIN (super@test.com):")
    super_user = Usuario.objects.get(email='super@test.com')
    request = factory.get('/admin/curriculum/tarefa/')
    request.user = super_user
    
    tarefa_admin = TarefaAdmin(Tarefa, site)
    
    print(f"Usuário: {super_user.email}")
    print(f"Role: {super_user.role}")
    print(f"Cliente ID: {super_user.cliente_id}")
    
    # Testar o método get_queryset
    queryset = tarefa_admin.get_queryset(request)
    
    print(f"Queryset do TarefaAdmin: {queryset.count()} tarefas")
    if queryset.count() > 0:
        print("✅ Tarefas encontradas:")
        for tarefa in queryset:
            print(f"  - Tarefa {tarefa.id}: {tarefa.tipo}-{tarefa.ordem} (Cliente: {tarefa.cliente.nome})")
    else:
        print("❌ Nenhuma tarefa encontrada")
    
    # Testar com usuário normal
    print("\n2. TESTANDO COM USUÁRIO NORMAL (normal_admin@test.com):")
    normal_user = Usuario.objects.get(email='normal_admin@test.com')
    request2 = factory.get('/admin/curriculum/tarefa/')
    request2.user = normal_user
    
    print(f"Usuário: {normal_user.email}")
    print(f"Role: {normal_user.role}")
    print(f"Cliente ID: {normal_user.cliente_id}")
    
    queryset_normal = tarefa_admin.get_queryset(request2)
    
    print(f"Queryset do TarefaAdmin: {queryset_normal.count()} tarefas")
    if queryset_normal.count() > 0:
        print("✅ Tarefas encontradas:")
        for tarefa in queryset_normal:
            print(f"  - Tarefa {tarefa.id}: {tarefa.tipo}-{tarefa.ordem} (Cliente: {tarefa.cliente.nome})")
    else:
        print("❌ Nenhuma tarefa encontrada (esperado para cliente sem tarefas)")

if __name__ == '__main__':
    test_tarefa_admin_fix()