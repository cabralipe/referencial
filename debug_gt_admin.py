#!/usr/bin/env python3
"""
Script para investigar por que os GTs não aparecem no Django Admin
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import GT
from core.models import Cliente, Usuario

def debug_gt_admin():
    """Investiga problemas com GTs no Django Admin"""
    print("=== Debug GT Admin ===\n")
    
    # Verificar total de GTs no banco
    total_gts = GT.objects.count()
    print(f"📊 Total de GTs no banco: {total_gts}")
    
    if total_gts == 0:
        print("❌ Não há GTs no banco de dados!")
        print("Vou criar alguns dados de teste...\n")
        create_test_data()
        return
    
    # Listar todos os GTs
    print(f"\n📋 Lista de todos os GTs:")
    for gt in GT.objects.all():
        print(f"   ID: {gt.id} | Nome: {gt.nome} | Cliente: {gt.cliente.nome if gt.cliente else 'Sem cliente'}")
    
    # Verificar clientes
    print(f"\n👥 Clientes no sistema:")
    for cliente in Cliente.objects.all():
        gt_count = GT.objects.filter(cliente=cliente).count()
        print(f"   ID: {cliente.id} | Nome: {cliente.nome} | GTs: {gt_count}")
    
    # Verificar usuários super admin
    print(f"\n🔑 Usuários Super Admin:")
    super_admins = Usuario.objects.filter(role=Usuario.Role.SUPER_ADMIN)
    for user in super_admins:
        print(f"   Email: {user.email} | Cliente: {user.cliente.nome if user.cliente else 'Sem cliente'}")
    
    # Verificar se há problemas com soft delete
    print(f"\n🗑️ Verificando soft delete:")
    deleted_gts = GT.objects.filter(is_deleted=True).count()
    active_gts = GT.objects.filter(is_deleted=False).count()
    print(f"   GTs ativos: {active_gts}")
    print(f"   GTs deletados: {deleted_gts}")

def create_test_data():
    """Cria dados de teste se não existirem"""
    print("🔧 Criando dados de teste...")
    
    # Verificar se há pelo menos um cliente
    cliente = Cliente.objects.first()
    if not cliente:
        print("❌ Não há clientes no sistema! Criando cliente de teste...")
        cliente = Cliente.objects.create(
            nome="Cliente Teste",
            slug="cliente-teste"
        )
        print(f"✅ Cliente criado: {cliente.nome}")
    
    # Criar GTs de teste
    for i in range(1, 4):
        gt, created = GT.objects.get_or_create(
            nome=f"GT Teste {i}",
            cliente=cliente,
            defaults={
                'descricao': f'Grupo de Trabalho de teste número {i}',
                'numero': i
            }
        )
        if created:
            print(f"✅ GT criado: {gt.nome}")
        else:
            print(f"ℹ️ GT já existe: {gt.nome}")
    
    print(f"\n📊 Total de GTs após criação: {GT.objects.count()}")

if __name__ == '__main__':
    debug_gt_admin()