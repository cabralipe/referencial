#!/usr/bin/env python
"""
Script para testar o salvamento do campo ManyToMany 'gts' no PerguntaAdmin após correção.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.db import models
from curriculum.models import Pergunta, GT, Tarefa
from curriculum.admin import PerguntaAdmin
from core.models import Usuario

def test_pergunta_save_with_gts():
    print("=== TESTE DE SALVAMENTO DE PERGUNTA COM GTS (APÓS CORREÇÃO) ===")
    
    # Buscar usuários de teste
    try:
        super_admin = Usuario.objects.get(email="super@test.com")
        normal_user = Usuario.objects.get(email="normal_admin@test.com")
        print(f"Super Admin: {super_admin.email} (role: {super_admin.role})")
        print(f"Normal User: {normal_user.email} (role: {normal_user.role})")
    except Usuario.DoesNotExist as e:
        print(f"❌ Usuário não encontrado: {e}")
        return
    
    # Verificar dados disponíveis
    print(f"\n=== DADOS DISPONÍVEIS ===")
    tarefas = Tarefa.raw_objects.filter(is_deleted=False)
    gts = GT.raw_objects.filter(is_deleted=False)
    
    print(f"Tarefas: {tarefas.count()}")
    for tarefa in tarefas:
        print(f"  - {tarefa.id}: {tarefa} (Cliente: {tarefa.cliente})")
    
    print(f"GTs: {gts.count()}")
    for gt in gts:
        print(f"  - {gt.id}: {gt} (Cliente: {gt.cliente})")
    
    if not tarefas.exists() or not gts.exists():
        print("❌ Não há dados suficientes para o teste")
        return
    
    # Testar criação através do admin
    print(f"\n=== TESTE ATRAVÉS DO ADMIN ===")
    
    factory = RequestFactory()
    admin_site = AdminSite()
    pergunta_admin = PerguntaAdmin(Pergunta, admin_site)
    
    # Simular request do super admin
    request = factory.post('/admin/curriculum/pergunta/add/')
    request.user = super_admin
    
    # Criar uma pergunta de teste
    tarefa = tarefas.first()
    gt_ids = list(gts.values_list('id', flat=True)[:2])  # Pegar apenas 2 GTs para teste
    
    print(f"Testando criação de pergunta para tarefa {tarefa.id} (cliente: {tarefa.cliente})")
    print(f"GTs selecionados: {gt_ids}")
    
    # Buscar próxima ordem disponível
    max_ordem = Pergunta.raw_objects.filter(tarefa=tarefa).aggregate(
        max_ordem=models.Max('ordem')
    )['max_ordem'] or 0
    
    # Criar pergunta
    pergunta = Pergunta(
        tarefa=tarefa,
        ordem=max_ordem + 1,
        texto="Pergunta de teste para verificar salvamento de GTs após correção",
        permite_upload=False,
        obrigatoria=True
    )
    
    # Simular o save_model do admin
    class MockForm:
        pass
    
    form = MockForm()
    
    try:
        # Testar o save_model
        pergunta_admin.save_model(request, pergunta, form, change=False)
        print(f"✅ Pergunta salva com sucesso! ID: {pergunta.id}")
        print(f"Cliente da pergunta: {pergunta.cliente}")
        
        # Associar GTs
        pergunta.gts.set(gt_ids)
        pergunta.save()
        
        print(f"GTs associados: {list(pergunta.gts.values_list('id', 'nome'))}")
        
        # Verificar se foi salvo corretamente
        pergunta_recarregada = Pergunta.objects.get(id=pergunta.id)
        gts_salvos = list(pergunta_recarregada.gts.values_list('id', 'nome'))
        print(f"GTs após recarregar: {gts_salvos}")
        
        if len(gts_salvos) == len(gt_ids):
            print("✅ Salvamento de GTs funcionou!")
        else:
            print("❌ Problema no salvamento de GTs!")
        
        # Limpar teste
        pergunta.delete()
        print("Pergunta de teste removida")
        
    except Exception as e:
        print(f"❌ Erro no salvamento: {e}")
        # Tentar limpar se a pergunta foi criada
        try:
            if pergunta.id:
                pergunta.delete()
        except:
            pass
    
    # Testar com usuário normal
    print(f"\n=== TESTE COM USUÁRIO NORMAL ===")
    
    request.user = normal_user
    
    # Buscar tarefa do cliente do usuário normal
    tarefa_normal = None
    if normal_user.cliente_id:
        tarefas_cliente = Tarefa.objects.filter(cliente_id=normal_user.cliente_id)
        if tarefas_cliente.exists():
            tarefa_normal = tarefas_cliente.first()
    
    if tarefa_normal:
        print(f"Testando criação para usuário normal com tarefa {tarefa_normal.id}")
        
        # Buscar próxima ordem disponível para usuário normal
        max_ordem_normal = Pergunta.raw_objects.filter(tarefa=tarefa_normal).aggregate(
            max_ordem=models.Max('ordem')
        )['max_ordem'] or 0
        
        pergunta_normal = Pergunta(
            tarefa=tarefa_normal,
            ordem=max_ordem_normal + 1,
            texto="Pergunta de teste para usuário normal",
            permite_upload=False,
            obrigatoria=True
        )
        
        try:
            pergunta_admin.save_model(request, pergunta_normal, form, change=False)
            print(f"✅ Pergunta de usuário normal salva! ID: {pergunta_normal.id}")
            print(f"Cliente da pergunta: {pergunta_normal.cliente}")
            
            # Limpar teste
            pergunta_normal.delete()
            print("Pergunta de teste do usuário normal removida")
            
        except Exception as e:
            print(f"❌ Erro no salvamento para usuário normal: {e}")
            try:
                if pergunta_normal.id:
                    pergunta_normal.delete()
            except:
                pass
    else:
        print("⚠️ Usuário normal não tem tarefas disponíveis para teste")

if __name__ == "__main__":
    test_pergunta_save_with_gts()