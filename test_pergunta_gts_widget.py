#!/usr/bin/env python
"""Script para testar o widget de GTs no PerguntaAdmin."""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from core.models import Usuario
from curriculum.models import GT, Pergunta
from curriculum.admin import PerguntaAdmin

def test_pergunta_gts_widget():
    """Testa se o widget de GTs funciona no PerguntaAdmin."""
    
    print("=== TESTE DO WIDGET DE GTs NO PERGUNTAADMIN ===")
    
    # Criar uma requisição fake
    factory = RequestFactory()
    request = factory.get('/admin/curriculum/pergunta/add/')
    
    # Testar com super admin
    super_user = Usuario.objects.get(email='super@test.com')
    request.user = super_user
    
    # Criar instância do PerguntaAdmin
    pergunta_admin = PerguntaAdmin(Pergunta, site)
    
    print(f"Usuário: {super_user.email}")
    print(f"Role: {super_user.role}")
    print(f"É super admin: {super_user.role == Usuario.Role.SUPER_ADMIN}")
    
    # Verificar o queryset padrão do campo gts
    form_class = pergunta_admin.get_form(request)
    form = form_class()
    
    if 'gts' in form.fields:
        gts_field = form.fields['gts']
        queryset = gts_field.queryset
        print(f"Queryset do campo gts: {queryset.count()} GTs")
        
        if queryset.count() > 0:
            print("✅ GTs encontrados no widget:")
            for gt in queryset:
                print(f"  - GT {gt.id}: {gt.nome} (Cliente: {gt.cliente.nome})")
        else:
            print("❌ Nenhum GT encontrado no widget")
            
        # Verificar se é o queryset padrão do modelo
        default_queryset = GT.objects.all()
        print(f"Queryset padrão do modelo GT: {default_queryset.count()} GTs")
        
        # Verificar raw_objects
        raw_queryset = GT.raw_objects.filter(is_deleted=False)
        print(f"Raw queryset do modelo GT: {raw_queryset.count()} GTs")
    else:
        print("❌ Campo 'gts' não encontrado no formulário")

if __name__ == '__main__':
    test_pergunta_gts_widget()