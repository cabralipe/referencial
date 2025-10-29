#!/usr/bin/env python
"""Script para verificar dados de Tarefa no banco."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Tarefa

def check_tarefas():
    """Verifica se existem tarefas no banco de dados."""
    
    print("=== VERIFICAÇÃO DE TAREFAS NO BANCO ===")
    
    # Verificar total de tarefas
    total_tarefas = Tarefa.objects.all().count()
    print(f"Total de tarefas (com filtro): {total_tarefas}")
    
    # Verificar com raw_objects
    total_raw = Tarefa.raw_objects.filter(is_deleted=False).count()
    print(f"Total de tarefas (raw_objects): {total_raw}")
    
    if total_raw > 0:
        print("\n✅ Tarefas encontradas:")
        for tarefa in Tarefa.raw_objects.filter(is_deleted=False):
            print(f"  - Tarefa {tarefa.id}: {tarefa.tipo}-{tarefa.ordem}")
            print(f"    Cliente: {tarefa.cliente.nome if tarefa.cliente else 'Sem cliente'}")
            print(f"    Status: {tarefa.status}")
            print(f"    Etapa: {tarefa.etapa}")
    else:
        print("❌ Nenhuma tarefa encontrada")

if __name__ == '__main__':
    check_tarefas()