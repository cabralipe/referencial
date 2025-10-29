#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Pergunta, GT
from django.db import connection

def debug_gts_display():
    print("=== Debug: GTs não aparecem no seletor ===\n")
    
    # Verificar se existem perguntas com GTs associados
    perguntas_com_gts = Pergunta.raw_objects.prefetch_related('gts').filter(gts__isnull=False).distinct()
    print(f'Perguntas com GTs: {perguntas_com_gts.count()}')
    
    for pergunta in perguntas_com_gts[:3]:
        print(f'Pergunta {pergunta.id}: {pergunta.texto[:50]}...')
        print(f'  GTs associados: {[gt.nome for gt in pergunta.gts.all()]}')
        print(f'  Cliente: {pergunta.cliente_id}')
        print()
    
    # Verificar a estrutura da tabela many-to-many
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id as pergunta_id, p.texto, g.id as gt_id, g.nome as gt_nome, p.cliente_id
            FROM curriculum_pergunta p
            JOIN curriculum_pergunta_gts pg ON p.id = pg.pergunta_id
            JOIN curriculum_gt g ON pg.gt_id = g.id
            LIMIT 5
        """)
        
        print('Relacionamentos pergunta-gt na base de dados:')
        for row in cursor.fetchall():
            print(f'Pergunta {row[0]} ({row[1][:30]}...) -> GT {row[2]} ({row[3]}) [Cliente: {row[4]}]')
    
    print("\n=== Verificando queryset do formfield_for_manytomany ===")
    
    # Simular o que acontece no admin
    from django.contrib.auth import get_user_model
    from core.models import Usuario
    
    User = get_user_model()
    
    # Testar com super admin
    try:
        super_admin = User.objects.filter(role=Usuario.Role.SUPER_ADMIN).first()
        if super_admin:
            print(f"Super admin encontrado: {super_admin.email}")
            # Simular queryset para super admin
            gts_super_admin = GT.raw_objects.filter(is_deleted=False)
            print(f"GTs disponíveis para super admin: {gts_super_admin.count()}")
            for gt in gts_super_admin[:5]:
                print(f"  - {gt.nome} (Cliente: {gt.cliente_id})")
        else:
            print("Nenhum super admin encontrado")
    except Exception as e:
        print(f"Erro ao buscar super admin: {e}")
    
    # Testar com usuário normal
    try:
        normal_user = User.objects.filter(role=Usuario.Role.ADMIN_CLIENTE).first()
        if normal_user:
            print(f"\nUsuário normal encontrado: {normal_user.email}")
            # Simular queryset para usuário normal
            gts_normal = GT.objects.all()
            print(f"GTs disponíveis para usuário normal: {gts_normal.count()}")
            for gt in gts_normal[:5]:
                print(f"  - {gt.nome} (Cliente: {gt.cliente_id})")
        else:
            print("Nenhum usuário normal encontrado")
    except Exception as e:
        print(f"Erro ao buscar usuário normal: {e}")

if __name__ == "__main__":
    debug_gts_display()