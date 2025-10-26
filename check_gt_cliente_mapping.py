#!/usr/bin/env python
"""Script para verificar o mapeamento entre GTs e clientes."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import GT

def main():
    print("Mapeamento GT -> Cliente:")
    print("-" * 30)
    
    gts = GT.objects.all()
    for gt in gts:
        print(f"GT {gt.id}: Cliente {gt.cliente_id} ({gt.cliente.nome})")
    
    print("\nEste mapeamento será usado para configurar o header X-Cliente-ID automaticamente.")

if __name__ == '__main__':
    main()