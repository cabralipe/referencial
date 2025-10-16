#!/usr/bin/env python
"""Script para criar dados de teste para o sistema de textos únicos."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Cliente, Usuario
from curriculum.models import GT, Tarefa

def create_test_data():
    """Cria dados de teste para o sistema."""
    
    # Obter cliente de teste
    try:
        cliente_teste = Cliente.objects.get(slug='cliente-teste')
    except Cliente.DoesNotExist:
        print("❌ Cliente de teste não encontrado. Execute create_test_users.py primeiro.")
        return
    
    print(f"📋 Criando dados de teste para: {cliente_teste.nome}")
    
    # 1. Criar GTs de teste
    gts_data = [
        {"nome": "GT 1 - Educação Infantil", "etapa": "Etapa 1"},
        {"nome": "GT 2 - Ensino Fundamental I", "etapa": "Etapa 2"},
        {"nome": "GT 3 - Ensino Fundamental II", "etapa": "Etapa 3"},
        {"nome": "GT 4 - Ensino Médio", "etapa": "Etapa 4"},
    ]
    
    for gt_data in gts_data:
        gt, created = GT.objects.get_or_create(
            cliente=cliente_teste,
            nome=gt_data["nome"],
            defaults={"etapa": gt_data["etapa"]}
        )
        if created:
            print(f"✅ GT criado: {gt.nome}")
        else:
            print(f"ℹ️  GT já existe: {gt.nome}")
    
    # 2. Criar Tarefas de teste
    tarefas_data = [
        {"ordem": 1, "etapa": "Etapa 1", "tipo": Tarefa.Tipo.PERGUNTAS},
        {"ordem": 2, "etapa": "Etapa 1", "tipo": Tarefa.Tipo.OFICINA},
        {"ordem": 3, "etapa": "Etapa 2", "tipo": Tarefa.Tipo.PERGUNTAS},
        {"ordem": 4, "etapa": "Etapa 2", "tipo": Tarefa.Tipo.OFICINA},
        {"ordem": 5, "etapa": "Etapa 3", "tipo": Tarefa.Tipo.PERGUNTAS},
    ]
    
    for tarefa_data in tarefas_data:
        tarefa, created = Tarefa.objects.get_or_create(
            cliente=cliente_teste,
            ordem=tarefa_data["ordem"],
            tipo=tarefa_data["tipo"],
            defaults={"etapa": tarefa_data["etapa"]}
        )
        if created:
            print(f"✅ Tarefa criada: {tarefa}")
        else:
            print(f"ℹ️  Tarefa já existe: {tarefa}")
    
    print("\n🎉 Dados de teste criados com sucesso!")
    print("\n📊 Resumo:")
    print(f"   • GTs: {GT.objects.filter(cliente=cliente_teste).count()}")
    print(f"   • Tarefas: {Tarefa.objects.filter(cliente=cliente_teste).count()}")

if __name__ == '__main__':
    create_test_data()