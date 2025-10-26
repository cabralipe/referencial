#!/usr/bin/env python
"""Script para verificar dados da resposta."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Resposta
from django.contrib.auth import get_user_model

def main():
    User = get_user_model()
    
    # Buscar o usuário admin
    admin = User.objects.get(email='admin@test.com')
    print(f"Admin cliente ID: {admin.cliente_id}")
    
    # Verificar respostas para cliente 1
    respostas_cliente_1 = Resposta.objects.filter(cliente_id=1)
    print(f"Respostas para cliente 1: {list(respostas_cliente_1.values('id', 'pergunta__texto'))}")
    
    # Verificar se resposta ID 1 existe
    resposta_1_exists = Resposta.objects.filter(id=1).exists()
    print(f"Resposta ID 1 existe? {resposta_1_exists}")
    
    if resposta_1_exists:
        r1 = Resposta.objects.get(id=1)
        print(f"Resposta ID 1 - Cliente: {r1.cliente_id}")
        print(f"Resposta ID 1 - GT: {r1.gt_id}")
        print(f"Resposta ID 1 - Pergunta: {r1.pergunta_id}")
    
    # Verificar todas as respostas
    todas_respostas = Resposta.objects.all()
    print(f"Total de respostas: {todas_respostas.count()}")
    for r in todas_respostas:
        print(f"  - Resposta ID {r.id}: Cliente {r.cliente_id}, GT {r.gt_id}, Pergunta {r.pergunta_id}")

if __name__ == '__main__':
    main()