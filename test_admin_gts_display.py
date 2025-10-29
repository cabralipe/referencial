#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from curriculum.models import Pergunta, GT
from curriculum.admin import PerguntaAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from core.models import Usuario

def test_admin_gts_display():
    print("=== Testando exibição de GTs no Django Admin ===\n")
    
    User = get_user_model()
    factory = RequestFactory()
    
    # Criar uma instância do admin
    admin_site = AdminSite()
    pergunta_admin = PerguntaAdmin(Pergunta, admin_site)
    
    # Buscar uma pergunta que tem GTs associados
    pergunta_com_gts = Pergunta.raw_objects.prefetch_related('gts').filter(gts__isnull=False).first()
    
    if not pergunta_com_gts:
        print("❌ Nenhuma pergunta com GTs encontrada!")
        return
    
    print(f"📝 Testando pergunta: {pergunta_com_gts.id} - {pergunta_com_gts.texto[:50]}...")
    print(f"   Cliente: {pergunta_com_gts.cliente_id}")
    print(f"   GTs salvos: {[gt.nome for gt in pergunta_com_gts.gts.all()]}")
    
    # Testar com usuário normal
    normal_user = User.objects.filter(role=Usuario.Role.ADMIN_CLIENTE).first()
    if normal_user:
        print(f"\n👤 Testando com usuário normal: {normal_user.email}")
        print(f"   Cliente do usuário: {normal_user.cliente_id}")
        
        # Simular request
        request = factory.get('/admin/curriculum/pergunta/')
        request.user = normal_user
        
        # Testar formfield_for_manytomany
        gts_field = Pergunta._meta.get_field('gts')
        
        formfield = pergunta_admin.formfield_for_manytomany(gts_field, request)
        queryset = formfield.queryset
        
        print(f"   Queryset disponível: {queryset.count()} GTs")
        for gt in queryset:
            print(f"     - {gt.nome} (Cliente: {gt.cliente_id})")
        
        # Verificar se os GTs salvos estão no queryset
        gts_salvos = pergunta_com_gts.gts.all()
        gts_no_queryset = []
        gts_fora_queryset = []
        
        for gt in gts_salvos:
            if gt in queryset:
                gts_no_queryset.append(gt.nome)
            else:
                gts_fora_queryset.append(gt.nome)
        
        print(f"   ✅ GTs salvos que estão no queryset: {gts_no_queryset}")
        print(f"   ❌ GTs salvos que NÃO estão no queryset: {gts_fora_queryset}")
        
        if gts_fora_queryset:
            print(f"\n🔍 PROBLEMA IDENTIFICADO: GTs salvos não estão no queryset disponível!")
            print(f"   Isso explica por que não aparecem no seletor.")
            print(f"   Motivo: O usuário normal só vê GTs do seu cliente ({normal_user.cliente_id})")
            print(f"   Mas a pergunta tem GTs de outro cliente ({pergunta_com_gts.cliente_id})")
    
    # Criar um super admin temporário para testar
    print(f"\n👑 Criando super admin temporário para teste...")
    try:
        super_admin, created = User.objects.get_or_create(
            email='temp_super@test.com',
            defaults={
                'nome': 'Super Admin Temporário',
                'role': Usuario.Role.SUPER_ADMIN,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            super_admin.set_password('123456')
            super_admin.save()
            print(f"   Super admin criado: {super_admin.email}")
        else:
            print(f"   Super admin já existe: {super_admin.email}")
        
        # Simular request com super admin
        request = factory.get('/admin/curriculum/pergunta/')
        request.user = super_admin
        
        # Testar formfield_for_manytomany
        formfield = pergunta_admin.formfield_for_manytomany(gts_field, request)
        queryset = formfield.queryset
        
        print(f"   Queryset disponível para super admin: {queryset.count()} GTs")
        for gt in queryset:
            print(f"     - {gt.nome} (Cliente: {gt.cliente_id})")
        
        # Verificar se os GTs salvos estão no queryset
        gts_no_queryset = []
        gts_fora_queryset = []
        
        for gt in gts_salvos:
            if gt in queryset:
                gts_no_queryset.append(gt.nome)
            else:
                gts_fora_queryset.append(gt.nome)
        
        print(f"   ✅ GTs salvos que estão no queryset: {gts_no_queryset}")
        print(f"   ❌ GTs salvos que NÃO estão no queryset: {gts_fora_queryset}")
        
    except Exception as e:
        print(f"   Erro ao criar super admin: {e}")

if __name__ == "__main__":
    test_admin_gts_display()