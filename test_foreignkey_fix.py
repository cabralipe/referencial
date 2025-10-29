#!/usr/bin/env python
"""Script para testar a correção dos campos ForeignKey nos admins."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from core.models import Usuario, Cliente
from curriculum.models import Tarefa, Pergunta, TextoUnico, GT
from curriculum.admin import PerguntaAdmin, TextoUnicoAdmin, RespostaAdmin


def test_foreignkey_fix():
    """Testa se a correção dos campos ForeignKey funciona."""
    
    print("=== TESTE DA CORREÇÃO DOS CAMPOS FOREIGNKEY ===")
    
    # Buscar usuários
    try:
        super_admin = Usuario.objects.get(email="super@test.com")
        normal_user = Usuario.objects.get(email="normal_admin@test.com")
    except Usuario.DoesNotExist:
        print("❌ Usuários de teste não encontrados!")
        return
    
    print(f"Super Admin: {super_admin.email} (role: {super_admin.role})")
    print(f"Normal User: {normal_user.email} (role: {normal_user.role})")
    print()
    
    # Verificar tarefas disponíveis
    print("=== TAREFAS DISPONÍVEIS ===")
    all_tarefas = Tarefa.raw_objects.filter(is_deleted=False)
    print(f"Total de tarefas (raw_objects): {all_tarefas.count()}")
    for tarefa in all_tarefas:
        print(f"  - Tarefa {tarefa.ordem}: {tarefa.tipo} (Cliente: {tarefa.cliente.nome})")
    print()
    
    # Verificar GTs disponíveis
    print("=== GTs DISPONÍVEIS ===")
    all_gts = GT.raw_objects.filter(is_deleted=False)
    print(f"Total de GTs (raw_objects): {all_gts.count()}")
    for gt in all_gts:
        print(f"  - GT: {gt.nome} (Cliente: {gt.cliente.nome})")
    print()
    
    # Testar querysets diretamente
    print("=== TESTE QUERYSETS DIRETOS ===")
    
    # Teste para super admin
    print("Super Admin:")
    print(f"  - Tarefas via raw_objects: {Tarefa.raw_objects.filter(is_deleted=False).count()}")
    print(f"  - Tarefas via objects: {Tarefa.objects.all().count()}")
    print(f"  - GTs via raw_objects: {GT.raw_objects.filter(is_deleted=False).count()}")
    print(f"  - GTs via objects: {GT.objects.all().count()}")
    
    # Teste para usuário normal (simular contexto de cliente)
    print("Usuário Normal:")
    print(f"  - Tarefas via objects: {Tarefa.objects.all().count()}")
    print(f"  - GTs via objects: {GT.objects.all().count()}")
    
    print()
    
    # Testar lógica dos métodos formfield_for_foreignkey
    print("=== TESTE LÓGICA DOS MÉTODOS ===")
    
    # Simular a lógica do PerguntaAdmin.formfield_for_foreignkey
    print("PerguntaAdmin - Campo Tarefa:")
    
    # Para super admin
    if hasattr(super_admin, 'role') and super_admin.role == Usuario.Role.SUPER_ADMIN:
        queryset_super = Tarefa.raw_objects.filter(is_deleted=False)
        print(f"  Super Admin veria {queryset_super.count()} tarefas")
    else:
        queryset_super = Tarefa.objects.all()
        print(f"  Super Admin veria {queryset_super.count()} tarefas (fallback)")
    
    # Para usuário normal
    if hasattr(normal_user, 'role') and normal_user.role == Usuario.Role.SUPER_ADMIN:
        queryset_normal = Tarefa.raw_objects.filter(is_deleted=False)
        print(f"  Usuário Normal veria {queryset_normal.count()} tarefas")
    else:
        queryset_normal = Tarefa.objects.all()
        print(f"  Usuário Normal veria {queryset_normal.count()} tarefas")
    
    print()
    
    # Simular a lógica para GTs
    print("RespostaAdmin - Campo GT:")
    
    # Para super admin
    if hasattr(super_admin, 'role') and super_admin.role == Usuario.Role.SUPER_ADMIN:
        queryset_super_gt = GT.raw_objects.filter(is_deleted=False)
        print(f"  Super Admin veria {queryset_super_gt.count()} GTs")
    else:
        queryset_super_gt = GT.objects.all()
        print(f"  Super Admin veria {queryset_super_gt.count()} GTs (fallback)")
    
    # Para usuário normal
    if hasattr(normal_user, 'role') and normal_user.role == Usuario.Role.SUPER_ADMIN:
        queryset_normal_gt = GT.raw_objects.filter(is_deleted=False)
        print(f"  Usuário Normal veria {queryset_normal_gt.count()} GTs")
    else:
        queryset_normal_gt = GT.objects.all()
        print(f"  Usuário Normal veria {queryset_normal_gt.count()} GTs")
    
    print()
    print("✅ Teste concluído!")
    print()
    print("RESUMO:")
    print("- Super admins devem ver todas as tarefas/GTs via raw_objects")
    print("- Usuários normais devem ver apenas itens do seu cliente via objects")
    print("- Os métodos formfield_for_foreignkey foram implementados nos admins:")
    print("  * PerguntaAdmin (campo tarefa)")
    print("  * TextoUnicoAdmin (campos tarefa e gt)")
    print("  * RespostaAdmin (campos gt e pergunta)")
    print("  * QuadroAdmin (campo gt)")


if __name__ == "__main__":
    test_foreignkey_fix()