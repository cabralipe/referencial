#!/usr/bin/env python
"""
Script de 'superpopulate' para preencher o banco de dados com dados de teste abrangentes.
Cobre todos os principais modelos da aplicação:
- Core (Clientes, Usuários, Logs, Gamificação)
- Curriculum (GTs, Tarefas, Perguntas, Respostas, Textos Únicos, Textos Colaborativos)
- Reviews (Revisões)
- Library (Mídia, Blocos de Texto)
- Workshop (Quadros)
- Consultas Públicas
- Comentários
- MEB (Chat)
"""

import os
import sys
import random
import datetime
import json
from django.utils import timezone

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

# Importar modelos
from core.models import (
    AuditLog,
    Cliente,
    ClienteConfig,
    ClienteFeatureFlag,
    ClienteTema,
    ScoreEntry,
    ThrottleBlock,
    UserSessionLog,
)
from curriculum.models import Area, Anexo, GT, Pergunta, Resposta, Tarefa, TextoColaborativo, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from reviews.models import Revisao
from library.models import Midia, BlocoTexto
from notifications.models import Notificacao
from workshop.models import CelulaQuadro, Quadro, QuadroColuna, QuadroLinha
from consultas.models import ConsultaPublica, ManifestacaoPublica
from comments.models import Comentario
from meb.models import MebThread, MebMessage

User = get_user_model()

def create_clients():
    print("--- Criando Clientes ---")
    cliente_seduc, _ = Cliente.objects.get_or_create(
        slug='seduc',
        defaults={'nome': 'Secretaria de Educação', 'ativo': True}
    )
    
    # Configurações e Tema
    ClienteConfig.objects.get_or_create(
        cliente=cliente_seduc,
        chave='titulo_sistema',
        defaults={'valor_texto': 'Referencial Curricular SEDUC'}
    )
    
    ClienteTema.objects.get_or_create(
        cliente=cliente_seduc,
        cor_primaria='#0ea5e9',
        cor_secundaria='#10b981',
        defaults={
            'rodape_html': '<p>&copy; 2024 SEDUC. Todos os direitos reservados.</p>',
            'cabecalho_html': '<div><h1>Referencial SEDUC</h1></div>'
        }
    )

    ClienteFeatureFlag.objects.get_or_create(
        cliente=cliente_seduc,
        flag='dynamic_forms',
        defaults={'ativo': True}
    )
    print(f"Cliente criado: {cliente_seduc}")
    return cliente_seduc

def create_users(cliente):
    print("--- Criando Usuários ---")
    users = {}
    
    # Super Admin
    super_admin, _ = User.objects.get_or_create(
        email='super@admin.com',
        defaults={
            'nome': 'Super Admin',
            'role': User.Role.SUPER_ADMIN,
            'is_superuser': True,
            'is_staff': True
        }
    )
    if _: super_admin.set_password('123456'); super_admin.save()
    users['super'] = super_admin

    # Admin Cliente
    admin_cliente, _ = User.objects.get_or_create(
        email='admin@seduc.com',
        defaults={
            'nome': 'Admin Seduc',
            'role': User.Role.ADMIN_CLIENTE,
            'cliente': cliente
        }
    )
    if _: admin_cliente.set_password('123456'); admin_cliente.save()
    users['admin'] = admin_cliente

    # Articulador
    articulador, _ = User.objects.get_or_create(
        email='articulador@seduc.com',
        defaults={
            'nome': 'Articulador Pedagógico',
            'role': User.Role.ARTICULADOR,
            'cliente': cliente
        }
    )
    if _: articulador.set_password('123456'); articulador.save()
    users['articulador'] = articulador

    # Membro GT
    professor, _ = User.objects.get_or_create(
        email='professor@seduc.com',
        defaults={
            'nome': 'Professor Matemática',
            'role': User.Role.MEMBRO_GT,
            'cliente': cliente
        }
    )
    if _: professor.set_password('123456'); professor.save()
    users['professor'] = professor

    # Leitor
    leitor, _ = User.objects.get_or_create(
        email='leitor@seduc.com',
        defaults={
            'nome': 'Consultor Externo',
            'role': User.Role.LEITOR,
            'cliente': cliente
        }
    )
    if _: leitor.set_password('123456'); leitor.save()
    users['leitor'] = leitor

    print("Usuários criados/verificados.")
    return users

def create_curriculum(cliente, users):
    print("--- Criando Currículo (GTs, Tarefas, Perguntas) ---")
    
    # GTs
    gt_mat, _ = GT.objects.get_or_create(
        cliente=cliente,
        nome='Matemática',
        defaults={'etapa': 'Ensino Fundamental'}
    )
    gt_mat.membros.add(users['professor'], users['articulador'])
    
    gt_port, _ = GT.objects.get_or_create(
        cliente=cliente,
        nome='Língua Portuguesa',
        defaults={'etapa': 'Ensino Fundamental'}
    )
    gt_port.membros.add(users['articulador'])

    # Área
    area_base, _ = Area.objects.get_or_create(
        cliente=cliente,
        nome='Ciências da Natureza e Matemática',
        defaults={'descricao_html': '<p>Área integrada de ciências e matemática.</p>'}
    )

    area_base.gts.add(gt_mat, gt_port)

    # Tarefas
    tarefa1, _ = Tarefa.objects.get_or_create(
        cliente=cliente,
        ordem=1,
        tipo=Tarefa.Tipo.PERGUNTAS,
        defaults={'nome': 'Concepção Geral', 'etapa': 'I', 'status': Tarefa.Status.EM_DESENVOLVIMENTO}
    )
    
    tarefa2, _ = Tarefa.objects.get_or_create(
        cliente=cliente,
        ordem=2,
        tipo=Tarefa.Tipo.OFICINA,
        defaults={'nome': 'Diagnóstico Inicial', 'etapa': 'I', 'status': Tarefa.Status.RASCUNHO}
    )

    tarefa3, _ = Tarefa.objects.get_or_create(
        cliente=cliente,
        ordem=3,
        tipo=Tarefa.Tipo.PERGUNTAS,
        defaults={'nome': 'Objetivos de Aprendizagem', 'etapa': 'II', 'status': Tarefa.Status.RASCUNHO}
    )

    tarefa4, _ = Tarefa.objects.get_or_create(
        cliente=cliente,
        ordem=4,
        tipo=Tarefa.Tipo.PERGUNTAS,
        defaults={'nome': 'Competências Específicas', 'etapa': 'II', 'status': Tarefa.Status.RASCUNHO}
    )

    tarefa5, _ = Tarefa.objects.get_or_create(
        cliente=cliente,
        ordem=5,
        tipo=Tarefa.Tipo.PERGUNTAS,
        defaults={'nome': 'Habilidades e Objetos de Conhecimento', 'etapa': 'III', 'status': Tarefa.Status.RASCUNHO}
    )

    # Perguntas
    # Tarefa 1
    p1_t1, _ = Pergunta.objects.get_or_create(
        cliente=cliente,
        tarefa=tarefa1,
        ordem=1,
        defaults={
            'texto': 'Quais são os princípios norteadores do componente curricular?',
            'obrigatoria': True
        }
    )
    
    p2_t1, _ = Pergunta.objects.get_or_create(
        cliente=cliente,
        tarefa=tarefa1,
        ordem=2,
        defaults={
            'texto': 'Como a avaliação deve ser estruturada?',
            'obrigatoria': True
        }
    )

    # Tarefa 3
    p1_t3, _ = Pergunta.objects.get_or_create(
        cliente=cliente,
        tarefa=tarefa3,
        ordem=1,
        defaults={
            'texto': 'Quais são os objetivos de aprendizagem para o 1º ano?',
            'obrigatoria': True
        }
    )

    p2_t3, _ = Pergunta.objects.get_or_create(
        cliente=cliente,
        tarefa=tarefa3,
        ordem=2,
        defaults={
            'texto': 'Quais são os objetivos de aprendizagem para o 2º ano?',
            'obrigatoria': True
        }
    )

    # Tarefa 4
    p1_t4, _ = Pergunta.objects.get_or_create(
        cliente=cliente,
        tarefa=tarefa4,
        ordem=1,
        defaults={
            'texto': 'Defina a competência específica 1.',
            'obrigatoria': True
        }
    )

    # Tarefa 5
    p1_t5, _ = Pergunta.objects.get_or_create(
        cliente=cliente,
        tarefa=tarefa5,
        ordem=1,
        defaults={
            'texto': 'Liste as habilidades essenciais.',
            'obrigatoria': True
        }
    )
    
    # Respostas
    r1, _ = Resposta.objects.get_or_create(
        cliente=cliente,
        gt=gt_mat,
        pergunta=p1_t1,
        defaults={
            'conteudo_html': '<p>Os princípios norteadores incluem o desenvolvimento do pensamento crítico e a resolução de problemas.</p>',
            'autor': users['professor']
        }
    )

    r2, _ = Resposta.objects.get_or_create(
        cliente=cliente,
        gt=gt_mat,
        pergunta=p2_t1,
        defaults={
            'conteudo_html': '<p>A avaliação deve ser formativa, processual e contínua.</p>',
            'autor': users['professor']
        }
    )

    r3, _ = Resposta.objects.get_or_create(
        cliente=cliente,
        gt=gt_port, # Resposta do GT de Português para a mesma pergunta
        pergunta=p1_t1,
        defaults={
            'conteudo_html': '<p>Para Língua Portuguesa, o foco é o letramento e a interação social.</p>',
            'autor': users['articulador']
        }
    )

    Anexo.objects.get_or_create(
        cliente=cliente,
        resposta=r1,
        url='https://example.com/anexo-principios.pdf',
        defaults={'legenda': 'Documento base de princípios'}
    )
    
    # Texto Único
    tu1, _ = TextoUnico.objects.get_or_create(
        cliente=cliente,
        gt=gt_mat,
        tarefa=tarefa1,
        defaults={
            'conteudo_html': '<h1>Concepção de Matemática</h1><p>Texto consolidado da concepção...</p>',
            'responsavel': users['articulador']
        }
    )
    
    # Texto Colaborativo
    tc1, _ = TextoColaborativo.objects.get_or_create(
        cliente=cliente,
        gt=gt_mat,
        pergunta=p1_t1,
        defaults={
            'titulo': 'Rascunho Colaborativo - Princípios',
            'conteudo_html': '<p>Ideias iniciais para os princípios...</p>',
            'autor': users['professor']
        }
    )

    p1_t1.gts.add(gt_mat)

    print("Estrutura curricular criada.")
    return {
        'areas': [area_base],
        'gts': [gt_mat, gt_port],
        'tarefas': [tarefa1, tarefa2, tarefa3, tarefa4, tarefa5],
        'respostas': [r1, r2, r3],
        'textos_unicos': [tu1],
    }

def create_reviews(cliente, users, curriculum_data):
    print("--- Criando Revisões ---")
    r1 = curriculum_data['respostas'][0]
    
    revisao, _ = Revisao.objects.get_or_create(
        cliente=cliente,
        alvo_tipo=Revisao.AlvoTipo.RESPOSTA,
        alvo_id=str(r1.id),
        defaults={
            'status': Revisao.Status.EM_REVISAO,
            'solicitante': users['professor'],
            'revisor': users['articulador'],
            'parecer_html': '<p>Por favor, detalhar mais sobre a resolução de problemas.</p>'
        }
    )
    print("Revisão criada.")

def create_library(cliente, users, curriculum_data):
    print("--- Criando Biblioteca ---")
    gt_mat = curriculum_data['gts'][0]
    pergunta = Pergunta.objects.filter(cliente=cliente).first()
    BlocoTexto.objects.get_or_create(
        cliente=cliente,
        titulo='Introdução Padrão',
        defaults={
            'conteudo_html': '<p>Este documento segue as diretrizes da BNCC.</p>',
            'tags': ['introducao', 'bncc'],
            'gt': gt_mat,
            'pergunta': pergunta,
            'created_by': users['admin']
        }
    )
    
    Midia.objects.get_or_create(
        cliente=cliente,
        url='https://example.com/logo.png',
        defaults={
            'titulo': 'Logo do Projeto',
            'descricao': 'Logo do Projeto',
            'tags': ['logo', 'identidade'],
            'gt': gt_mat,
            'pergunta': pergunta,
            'uploaded_by': users['admin']
        }
    )
    print("Biblioteca populada.")

def create_workshop(cliente, users, curriculum_data):
    print("--- Criando Workshop (Quadros) ---")
    gt_mat = curriculum_data['gts'][0]
    area_base = curriculum_data['areas'][0]
    
    quadro, _ = Quadro.objects.get_or_create(
        cliente=cliente,
        gt=gt_mat,
        template='swot',
        defaults={'area': area_base}
    )

    QuadroLinha.objects.get_or_create(
        cliente=cliente,
        quadro=quadro,
        linha=0,
        defaults={'nome': 'Forças', 'ordem': 1}
    )
    QuadroLinha.objects.get_or_create(
        cliente=cliente,
        quadro=quadro,
        linha=1,
        defaults={'nome': 'Fraquezas', 'ordem': 2}
    )
    QuadroColuna.objects.get_or_create(
        cliente=cliente,
        quadro=quadro,
        coluna=0,
        defaults={'nome': 'Interno', 'ordem': 1}
    )
    QuadroColuna.objects.get_or_create(
        cliente=cliente,
        quadro=quadro,
        coluna=1,
        defaults={'nome': 'Externo', 'ordem': 2}
    )
    
    CelulaQuadro.objects.get_or_create(
        cliente=cliente,
        quadro=quadro,
        linha=0,
        coluna=0,
        defaults={'valor_html': '<ul><li>Equipe engajada</li></ul>'}
    )
    print("Workshop populado.")

def create_consultas(cliente, users):
    print("--- Criando Consultas Públicas ---")
    consulta, _ = ConsultaPublica.objects.get_or_create(
        cliente=cliente,
        slug='consulta-preliminar',
        defaults={
            'titulo': 'Consulta Preliminar do Referencial',
            'descricao': 'Envie suas contribuições para a versão preliminar.',
            'data_publicacao': timezone.now().date(),
            'ativa': True,
            'criada_por': users['admin'],
            # Mock file since we don't want to actually upload
            'pdf': 'consultas/mock.pdf' 
        }
    )
    
    ManifestacaoPublica.objects.get_or_create(
        cliente=cliente,
        consulta=consulta,
        nome_completo='Cidadão Exemplo',
        cpf='123.456.789-00',
        defaults={
            'comentario': 'Excelente iniciativa, mas sugiro rever o capítulo 2.',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'contato_email': 'cidadao@teste.com'
        }
    )
    print("Consultas criadas.")

def create_comments(cliente, users, curriculum_data):
    print("--- Criando Comentários ---")
    r1 = curriculum_data['respostas'][0]
    
    Comentario.objects.get_or_create(
        cliente=cliente,
        alvo_tipo=Comentario.AlvoTipo.RESPOSTA,
        alvo_id=str(r1.id),
        autor=users['articulador'],
        conteudo_html='<p>Precisamos citar a fonte bibliográfica aqui.</p>',
        defaults={
            'anchor_json': {'txt': 'pensamento crítico'}
        }
    )
    print("Comentários criados.")

def create_meb_chat(cliente, users):
    print("--- Criando Chat MEB ---")
    thread, _ = MebThread.objects.get_or_create(
        cliente=cliente,
        usuario=users['professor']
    )
    
    MebMessage.objects.get_or_create(
        cliente=cliente,
        thread=thread,
        conteudo='Como posso melhorar a descrição da competência?',
        origem=MebMessage.Origem.CLIENTE,
        autor=users['professor'],
        defaults={'created_at': timezone.now() - datetime.timedelta(minutes=5)}
    )
    
    MebMessage.objects.get_or_create(
        cliente=cliente,
        thread=thread,
        conteudo='Você pode focar nos verbos de ação da taxonomia de Bloom.',
        origem=MebMessage.Origem.MASCOTE,
        defaults={'created_at': timezone.now()}
    )

    MebMessage.objects.get_or_create(
        cliente=cliente,
        thread=thread,
        conteudo='Encaminhei sua dúvida para a equipe pedagógica.',
        origem=MebMessage.Origem.ADMIN,
        autor=users['admin'],
        defaults={'created_at': timezone.now() + datetime.timedelta(minutes=2)}
    )
    print("Chat MEB populado.")

def create_gamification(cliente, users):
    print("--- Criando Gamificação ---")
    ScoreEntry.objects.get_or_create(
        cliente=cliente,
        usuario=users['professor'],
        origem_tipo='resposta_criada',
        defaults={
            'pontos': 10,
            'descricao': 'Criou uma resposta'
        }
    )
    print("Gamificação populada.")

def create_dynamic_forms(cliente, users, curriculum_data):
    print("--- Criando Formulários Dinâmicos ---")
    gt_mat = curriculum_data['gts'][0]
    resposta = curriculum_data['respostas'][0]
    texto_unico = curriculum_data['textos_unicos'][0]

    formulario, _ = FormularioDinamico.objects.get_or_create(
        cliente=cliente,
        nome='Metadados de Resposta',
        defaults={'descricao': 'Campos adicionais para qualificar uma resposta.'}
    )

    campo_referencia, _ = CampoDinamico.objects.get_or_create(
        cliente=cliente,
        formulario=formulario,
        chave='referencias',
        defaults={
            'tipo': CampoDinamico.Tipo.TEXTO,
            'config_json': {'max': 500},
            'obrigatorio': False,
            'ordem': 1,
        }
    )

    campo_nivel, _ = CampoDinamico.objects.get_or_create(
        cliente=cliente,
        formulario=formulario,
        chave='nivel_prioridade',
        defaults={
            'tipo': CampoDinamico.Tipo.SELECT,
            'config_json': {'opcoes': ['baixo', 'medio', 'alto']},
            'obrigatorio': True,
            'ordem': 2,
        }
    )

    RespostaCampoDinamico.objects.get_or_create(
        cliente=cliente,
        formulario=formulario,
        campo=campo_referencia,
        owner_type=RespostaCampoDinamico.OwnerType.RESPOSTA,
        owner_id=str(resposta.id),
        defaults={'valor_texto': 'Referência BNCC, p. 12-15.'}
    )

    RespostaCampoDinamico.objects.get_or_create(
        cliente=cliente,
        formulario=formulario,
        campo=campo_nivel,
        owner_type=RespostaCampoDinamico.OwnerType.RESPOSTA,
        owner_id=str(resposta.id),
        defaults={'valor_texto': 'medio'}
    )

    RespostaCampoDinamico.objects.get_or_create(
        cliente=cliente,
        formulario=formulario,
        campo=campo_nivel,
        owner_type=RespostaCampoDinamico.OwnerType.TEXTO_UNICO,
        owner_id=str(texto_unico.id),
        defaults={'valor_texto': 'alto'}
    )

    RespostaCampoDinamico.objects.get_or_create(
        cliente=cliente,
        formulario=formulario,
        campo=campo_nivel,
        owner_type=RespostaCampoDinamico.OwnerType.GT,
        owner_id=str(gt_mat.id),
        defaults={'valor_texto': 'baixo'}
    )
    print("Formulários dinâmicos criados.")

def create_exports(cliente, curriculum_data):
    print("--- Criando Exportações ---")
    resposta = curriculum_data['respostas'][0]

    ExportJob.objects.get_or_create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.RESPOSTA,
        alvo_id=str(resposta.id),
        formato=ExportJob.Formato.PDF,
        defaults={
            'status': ExportJob.Status.DONE,
            'payload_json': {'layout': 'padrao', 'idioma': 'pt-BR'},
            'url_resultado': 'https://example.com/exports/resposta-1.pdf',
            'finished_at': timezone.now(),
        }
    )
    print("Exportações criadas.")

def create_notifications(cliente, users, curriculum_data):
    print("--- Criando Notificações ---")
    resposta = curriculum_data['respostas'][0]

    Notificacao.objects.get_or_create(
        cliente=cliente,
        usuario=users['professor'],
        tipo='resposta_comentada',
        defaults={'payload_json': {'resposta_id': str(resposta.id)}}
    )

    Notificacao.objects.get_or_create(
        cliente=cliente,
        usuario=users['articulador'],
        tipo='revisao_pendente',
        defaults={'payload_json': {'alvo_tipo': 'resposta', 'alvo_id': str(resposta.id)}}
    )
    print("Notificações criadas.")

def create_core_extras(cliente, users, curriculum_data):
    print("--- Criando Logs e Segurança ---")
    resposta = curriculum_data['respostas'][0]
    now = timezone.now()

    AuditLog.objects.get_or_create(
        cliente=cliente,
        entidade='Resposta',
        entidade_id=str(resposta.id),
        acao='create',
        defaults={
            'usuario_id': users['professor'].id,
            'diff_json': {'conteudo_html': 'criado via populate'},
            'timestamp': now,
        }
    )

    ThrottleBlock.objects.get_or_create(
        cliente=cliente,
        usuario=users['professor'],
        scope='login',
        cache_key=f'login:{users["professor"].id}',
        defaults={
            'ident': users['professor'].email,
            'wait_seconds': 60,
            'blocked_until': now + datetime.timedelta(minutes=1),
        }
    )

    UserSessionLog.objects.get_or_create(
        usuario=users['professor'],
        cliente=cliente,
        session_key='session_seed_0001',
        defaults={
            'first_seen_at': now - datetime.timedelta(minutes=20),
            'last_seen_at': now,
            'user_agent': 'Mozilla/5.0 (Seed Script)',
            'device': 'desktop',
        }
    )
    print("Logs e segurança criados.")

@transaction.atomic
def run():
    print("Iniciando população do banco de dados...")
    
    cliente = create_clients()
    users = create_users(cliente)
    
    curriculum_data = create_curriculum(cliente, users)
    
    create_reviews(cliente, users, curriculum_data)
    create_library(cliente, users, curriculum_data)
    create_workshop(cliente, users, curriculum_data)
    create_consultas(cliente, users)
    create_comments(cliente, users, curriculum_data)
    create_meb_chat(cliente, users)
    create_gamification(cliente, users)
    create_dynamic_forms(cliente, users, curriculum_data)
    create_exports(cliente, curriculum_data)
    create_notifications(cliente, users, curriculum_data)
    create_core_extras(cliente, users, curriculum_data)
    
    print("\n--- Processo Concluído com Sucesso! ---")
    print(f"Cliente: {cliente.nome} ({cliente.slug})")
    print("Usuários de teste:")
    for role, u in users.items():
        print(f"  - {role}: {u.email} (senha: 123456)")

if __name__ == '__main__':
    run()
