#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario
from curriculum.models import GT

def fix_gt_membership():
    # Buscar o usuário admin
    admin_user = Usuario.objects.filter(email="admin@test.com").first()
    if not admin_user:
        print("Usuário admin não encontrado")
        return
    
    print(f"Admin user ID: {admin_user.id}")
    print(f"Admin cliente ID: {admin_user.cliente_id}")
    print(f"Admin role: {admin_user.role}")
    
    # Buscar GT ID 1
    gt1 = GT.objects.filter(id=1).first()
    if not gt1:
        print("GT ID 1 não encontrado")
        return
    
    print(f"GT 1 - Nome: {gt1.nome}")
    print(f"GT 1 - Cliente: {gt1.cliente_id}")
    print(f"GT 1 - Etapa: {gt1.etapa}")
    
    # Verificar se admin é membro do GT 1
    is_member = gt1.membros.filter(id=admin_user.id).exists()
    print(f"Admin é membro do GT 1? {is_member}")
    
    if not is_member:
        print("Adicionando admin como membro do GT 1...")
        gt1.membros.add(admin_user)
        print("Admin adicionado como membro do GT 1")
    else:
        print("Admin já é membro do GT 1")
    
    # Verificar membros do GT 1
    membros = gt1.membros.all()
    print(f"Membros do GT 1: {[m.email for m in membros]}")

if __name__ == "__main__":
    fix_gt_membership()