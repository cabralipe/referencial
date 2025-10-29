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

def test_final_gts_fix():
    """Teste final para verificar se a correção dos GTs salvos está funcionando."""
    print("=== TESTE FINAL: Correção de GTs salvos no Django Admin ===\n")
    
    # Buscar uma pergunta com GTs salvos
    pergunta_com_gts = Pergunta.raw_objects.filter(gts__isnull=False).first()
    
    if not pergunta_com_gts:
        print("❌ Nenhuma pergunta com GTs salvos encontrada!")
        return
    
    print(f"📝 Testando pergunta: {pergunta_com_gts.id} - {pergunta_com_gts.texto[:50]}...")
    print(f"   Cliente: {pergunta_com_gts.cliente_id}")
    
    gts_salvos = list(pergunta_com_gts.gts.all())
    print(f"   GTs salvos: {[gt.nome for gt in gts_salvos]}")
    print()
    
    # Criar instância do admin
    admin_site = AdminSite()
    pergunta_admin = PerguntaAdmin(Pergunta, admin_site)
    
    # Criar factory para requests
    factory = RequestFactory()
    
    # Teste 1: Usuário normal
    print("👤 TESTE 1: Usuário normal")
    normal_user = Usuario.objects.filter(role=Usuario.Role.ADMIN_CLIENTE).first()
    
    if normal_user:
        # Simular request de edição
        edit_url = f"/admin/curriculum/pergunta/{pergunta_com_gts.id}/change/"
        request = factory.get(edit_url)
        request.user = normal_user
        
        # Testar formfield_for_manytomany
        from django.db import models
        gts_field = Pergunta._meta.get_field('gts')
        
        formfield_kwargs = {}
        pergunta_admin.formfield_for_manytomany(gts_field, request, **formfield_kwargs)
        
        queryset = formfield_kwargs.get('queryset', GT.objects.all())
        gts_disponiveis = list(queryset)
        
        print(f"   Usuário: {normal_user.email} (Cliente: {normal_user.cliente_id})")
        print(f"   GTs disponíveis no queryset: {len(gts_disponiveis)}")
        
        # Verificar se os GTs salvos estão no queryset
        gts_salvos_ids = [gt.id for gt in gts_salvos]
        gts_disponiveis_ids = [gt.id for gt in gts_disponiveis]
        
        gts_encontrados = []
        gts_perdidos = []
        
        for gt in gts_salvos:
            if gt.id in gts_disponiveis_ids:
                gts_encontrados.append(gt.nome)
            else:
                gts_perdidos.append(gt.nome)
        
        print(f"   ✅ GTs salvos encontrados: {gts_encontrados}")
        print(f"   ❌ GTs salvos perdidos: {gts_perdidos}")
        
        if not gts_perdidos:
            print("   🎉 SUCESSO: Todos os GTs salvos estão visíveis!")
        else:
            print("   ⚠️  PROBLEMA: Alguns GTs salvos não estão visíveis!")
    else:
        print("   ❌ Nenhum usuário normal encontrado!")
    
    print()
    
    # Teste 2: Super admin
    print("👑 TESTE 2: Super admin")
    super_admin = Usuario.objects.filter(role=Usuario.Role.SUPER_ADMIN).first()
    
    if not super_admin:
        # Criar um super admin temporário
        super_admin = Usuario.objects.create_user(
            email="temp_super_final@test.com",
            password="test123",
            role=Usuario.Role.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True
        )
        print("   📝 Super admin temporário criado")
    
    # Simular request de edição
    edit_url = f"/admin/curriculum/pergunta/{pergunta_com_gts.id}/change/"
    request = factory.get(edit_url)
    request.user = super_admin
    
    # Testar formfield_for_manytomany
    formfield_kwargs = {}
    pergunta_admin.formfield_for_manytomany(gts_field, request, **formfield_kwargs)
    
    queryset = formfield_kwargs.get('queryset', GT.objects.all())
    gts_disponiveis = list(queryset)
    
    print(f"   Usuário: {super_admin.email}")
    print(f"   GTs disponíveis no queryset: {len(gts_disponiveis)}")
    
    # Verificar se os GTs salvos estão no queryset
    gts_disponiveis_ids = [gt.id for gt in gts_disponiveis]
    
    gts_encontrados = []
    gts_perdidos = []
    
    for gt in gts_salvos:
        if gt.id in gts_disponiveis_ids:
            gts_encontrados.append(gt.nome)
        else:
            gts_perdidos.append(gt.nome)
    
    print(f"   ✅ GTs salvos encontrados: {gts_encontrados}")
    print(f"   ❌ GTs salvos perdidos: {gts_perdidos}")
    
    if not gts_perdidos:
        print("   🎉 SUCESSO: Todos os GTs salvos estão visíveis!")
    else:
        print("   ⚠️  PROBLEMA: Alguns GTs salvos não estão visíveis!")
    
    print()
    
    # Teste 3: Verificar método auxiliar
    print("🔧 TESTE 3: Método auxiliar _get_pergunta_id_from_request")
    
    test_urls = [
        f"/admin/curriculum/pergunta/{pergunta_com_gts.id}/change/",
        f"/admin/curriculum/pergunta/{pergunta_com_gts.id}/",
        "/admin/curriculum/pergunta/add/",
        "/admin/curriculum/pergunta/"
    ]
    
    for url in test_urls:
        request = factory.get(url)
        pergunta_id = pergunta_admin._get_pergunta_id_from_request(request)
        expected = pergunta_com_gts.id if '/change/' in url else None
        status = "✅" if pergunta_id == expected else "❌"
        print(f"   {status} URL: {url} -> ID: {pergunta_id} (esperado: {expected})")
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    test_final_gts_fix()