#!/usr/bin/env python
"""Script para criar dados de teste para o cliente 1."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Resposta, Pergunta, GT, Tarefa
from django.contrib.auth import get_user_model

def main():
    User = get_user_model()
    
    # Buscar o usuário admin
    admin = User.objects.get(email='admin@test.com')
    print(f"Admin user: {admin.email}, Cliente ID: {admin.cliente_id}")
    
    # Criar GT para o cliente 1
    gt, gt_created = GT.objects.get_or_create(
        cliente_id=1, 
        nome='GT Teste',
        defaults={'etapa': 'I'}
    )
    print(f"GT criado: {gt_created}, ID: {gt.id}")
    
    # Criar Tarefa para o cliente 1
    tarefa, tarefa_created = Tarefa.objects.get_or_create(
        cliente_id=1,
        ordem=1,
        defaults={'etapa': 'I', 'tipo': 'PERGUNTAS'}
    )
    print(f"Tarefa criada: {tarefa_created}, ID: {tarefa.id}")
    
    # Criar Pergunta para o cliente 1
    pergunta, pergunta_created = Pergunta.objects.get_or_create(
        cliente_id=1,
        tarefa=tarefa,
        ordem=1,
        defaults={'texto': 'Pergunta de teste para cliente 1'}
    )
    print(f"Pergunta criada: {pergunta_created}, ID: {pergunta.id}")
    
    # Criar Resposta para o cliente 1
    resposta, resposta_created = Resposta.objects.get_or_create(
        cliente_id=1,
        gt=gt,
        pergunta=pergunta,
        defaults={
            'conteudo_html': 'Resposta de teste para cliente 1',
            'autor': admin
        }
    )
    print(f"Resposta criada: {resposta_created}, ID: {resposta.id}")
    
    # Verificar respostas disponíveis para o cliente 1
    respostas_cliente_1 = Resposta.objects.filter(cliente_id=1)
    print(f"Total de respostas para cliente 1: {respostas_cliente_1.count()}")
    for r in respostas_cliente_1:
        print(f"  - Resposta ID {r.id}: {r.pergunta.texto}")

if __name__ == '__main__':
    main()