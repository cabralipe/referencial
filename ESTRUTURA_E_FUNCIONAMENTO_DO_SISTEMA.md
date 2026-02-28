# Estrutura e Funcionamento do Sistema

## 1. Visão Geral

Este repositório implementa uma plataforma multi-tenant para construção de referenciais curriculares, com:

- Backend em Django + Django REST Framework
- Frontend SPA em React + Vite
- WebSockets com Django Channels
- Processamento assíncrono com Celery + Redis
- Extensibilidade por plugins (exportação, síntese e hooks)

O sistema organiza dados por **cliente** (`core.Cliente`) e aplica isolamento lógico por tenant em praticamente todos os modelos de domínio.

## 2. Arquitetura em Camadas

## 2.1 Backend (Django)

- Entrada HTTP: `config/urls.py`
- Configuração geral: `config/settings.py`
- API REST: `api/v1/`
- Regras de domínio: apps Django (`curriculum`, `workshop`, `reviews`, etc.)
- Tempo real: `sockets/` (Channels)
- Assíncrono: `tasks/` + `config/celery.py`
- Plugins: `plugins/` com carregamento em `core/plugins.py`
cri
## 2.2 Frontend (React)

- Código SPA: `frontend/src/`

- Roteamento: `frontend/src/router.tsx`
- Proteção de rotas por autenticação e papel: `ProtectedRoute` e `RoleRoute`
- Consumo da API em `/api/v1` e WebSockets em `/ws/...`

## 2.3 Infra e execução

- Banco principal: PostgreSQL (com fallback para SQLite em desenvolvimento)
- Fila/canal: Redis (Celery + Channels)
- Mídia: armazenamento local ou S3 (`MEDIA_BACKEND`)
- Estáticos: WhiteNoise

## 3. Estrutura de Pastas (Resumo)

- `config/`: settings, urls, ASGI, Celery
- `core/`: multi-tenant, usuário, permissões, auditoria, plugins, middleware
- `api/v1/`: serializers, viewsets, rotas públicas e admin console
- `curriculum/`: GTs, áreas, tarefas, perguntas, respostas, texto único e colaborativo
- `workshop/`: quadros, linhas, colunas e células
- `dynamicforms/`: formulários/campos dinâmicos e respostas genéricas por owner
- `reviews/`: revisões, designações de revisores e decisões
- `comments/`: comentários em linha com menções e resolução
- `notifications/`: notificações in-app
- `library/`: biblioteca de mídias e blocos de texto reutilizáveis
- `consultas/`: consultas públicas e manifestações abertas
- `courses/`: trilhas/cursos, módulos, itens, progresso e banco de planos
- `meb/`: threads e mensagens do chat do mascote MEB
- `exports/`: jobs de exportação e serviços PDF/DOCX
- `diffs/`: geração de diff HTML entre versões
- `sockets/`: consumers WebSocket (presença, stream e notificações)
- `tasks/`: tarefas Celery (síntese, exportação, limpeza, etc.)
- `plugins/`: providers versionáveis para export/synthesis/hooks
- `frontend/`: aplicação React
- `tests/`: suíte de testes automatizados

## 4. Núcleo Multi-tenant e Segurança

### 4.1 Isolamento por cliente

No `core/mixins.py`:

- `TenantModel`: base para entidades com `cliente`
- `SoftDeleteModel`: soft delete (`is_deleted`)
- `ClientScopedManager`: aplica filtro automático por `cliente_id` do contexto atual

No `core/middleware.py`:

- `ClienteScopeMiddleware` define `request.cliente_id` a partir do usuário autenticado
- `super_admin` pode trocar escopo via header `X-Cliente-ID`

Resultado: consultas padrão já vêm filtradas por cliente e sem registros removidos logicamente.

### 4.2 Usuários e papéis

Modelo: `core.Usuario` (AUTH_USER_MODEL customizado). Papéis:

- `super_admin`
- `admin_cliente`
- `articulador`
- `revisor`
- `membro_gt`
- `leitor`

Permissões DRF reutilizáveis em `core/permissions.py` controlam ações por papel e por vínculo com GT.

### 4.3 Auditoria e proteção

- Auditoria: `core.AuditLog`
- Bloqueios de throttle: `core.ThrottleBlock`
- CSRF, CORS, autenticação por sessão e JWT configurados em `config/settings.py`

## 5. Módulos de Domínio e Como se Conectam

## 5.1 Currículo (`curriculum`)

Entidades centrais:

- `GT` (grupo de trabalho) com membros
- `Area`
- `Tarefa` (tipo PERGUNTAS/OFICINA, com status)
- `Pergunta`
- `Resposta` (por `GT + Pergunta`, versionada)
- `TextoUnico` (por `GT + Tarefa`, versionado)
- `TextoColaborativo` (versionado, opcionalmente vinculado a pergunta)
- `Anexo`

Fluxo principal:

1. Admin estrutura tarefas/perguntas/GTs.
2. GT responde perguntas (`Resposta`).
3. Síntese gera `TextoUnico` a partir das respostas.
4. Conteúdo passa por comentários/revisão, pode ser exportado e auditado.

## 5.2 Oficina/Quadros (`workshop`)

- `Quadro` (template por GT)
- `CelulaQuadro` (matriz de conteúdo)
- `QuadroLinha` e `QuadroColuna` (metadados estruturais)

Uso: atividades de oficina com edição tabular versionada.

## 5.3 Formulários dinâmicos (`dynamicforms`)

- `FormularioDinamico`
- `CampoDinamico`
- `RespostaCampoDinamico` com `owner_type/owner_id`

Permite anexar formulários configuráveis a diferentes entidades (resposta, texto único, quadro, GT, plano de curso).

## 5.4 Revisão, comentários e notificações

- Revisões: `reviews.Revisao`, `ReviewerAssignment`, `ReviewDecision`
- Comentários em linha: `comments.Comentario` (âncora em JSON, menções, resolução)
- Notificações: `notifications.Notificacao`

Juntas, essas apps suportam fluxo editorial com ida/volta entre redatores e revisores.

## 5.5 Biblioteca de referência (`library`)

- `Midia`: assets reutilizáveis
- `BlocoTexto`: fragmentos de texto reaproveitáveis

Uso típico: acelerar produção de conteúdo com acervo interno.

## 5.6 Consulta pública (`consultas`)

- `ConsultaPublica`: documento PDF público com token e janela de validade
- `ManifestacaoPublica`: contribuições externas (inclusive votos por pergunta)

Há endpoints públicos (sem autenticação de usuário interno) para leitura e submissão.

## 5.7 Cursos/Trilhas (`courses`)

Modela ambiente formativo (estilo AVAMEC):

- `Curso`, `CursoModulo`, `CursoItem`
- `CursoProgresso` e `CursoProgressoItem`
- `CursoParticipacao`
- `PlanoAulaResposta`, `PlanoAulaPublicacao`
- `CursoCertificadoEmitido`

## 5.8 Chat MEB (`meb`)

- `MebThread`: canal por usuário
- `MebMessage`: mensagens de cliente/admin/mascote/sistema

## 5.9 Exportações e diffs

- `exports.ExportJob`: fila/status para geração PDF/DOCX
- `diffs/services.py`: comparação de versões HTML com base em snapshots de auditoria

## 6. API REST (v1)

Entrada principal: `api/v1/urls.py`, com roteamento em `api/v1/routers.py`.

### 6.1 Endpoints de autenticação e sessão

- `POST /api/v1/auth/login` (sessão)
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/jwt`
- `POST /api/v1/auth/jwt/refresh`
- `GET /api/v1/auth/csrf`

### 6.2 Endpoints funcionais (router)

Incluem recursos como:

- `tarefas`, `perguntas`, `gts`, `areas`, `respostas`, `texto_unico`, `textos_colaborativos`
- `quadro`, `formularios`, `exports`, `audit`, `throttle_blocks`, `score`
- `revisoes`, `comentarios`, `notificacoes`, `mural`, `midias`, `blocos`
- `consultas_publicas`, `ppp`, `cursos`, `planos-aula`, `banco-planos`
- `meb/threads`, `meb/mensagens`, `ai/assist`

Também há rotas de **Admin Console** sob prefixo `admin/...` dentro da própria API.

### 6.3 Endpoints utilitários extras

- `GET /api/v1/cliente/me`
- `GET /api/v1/diff`
- `GET /api/v1/diff/aprovado`
- `GET /api/v1/continuar`
- Rotas públicas de consulta: `/api/v1/consultas_publicas/public/<token>`

## 7. WebSockets e Tempo Real

Definidos em `sockets/routing.py`:

- `ws/presence/{docType}/{id}/`: presença/atividade no documento
- `ws/stream/{alvo_tipo}/{alvo_id}/`: eventos de fluxo (comentários/revisões)
- `ws/notifications/`: notificações em tempo real por usuário autenticado

Implementação em `sockets/consumers.py` via grupos do channel layer Redis.

## 8. Processamento Assíncrono (Celery)

Configuração em `config/celery.py` e `config/settings.py`.

Principais tarefas:

- `tasks.synthesis.generate_texto_unico`: gera texto único
- `tasks.exports.build_pdf` e `tasks.exports.build_docx`: exportação
- `tasks.cleanup.purge_soft_deleted`: limpeza de soft delete
- `tasks.cleanup.cleanup_exports`: limpeza de arquivos/export jobs antigos

## 9. Sistema de Plugins

Carregamento central em `core/plugins.py`:

- `plugins/exports/<nome>/provider.py`
- `plugins/synthesis/<nome>/provider.py`
- `plugins/hooks/<nome>/provider.py`

Plugin padrão:

- Export: renderização PDF/DOCX
- Synthesis: pré/pós-processamento de conteúdo
- Hooks: ponto de extensão para integrações externas

Seleção por cliente via `ClienteConfig` ou variáveis padrão em settings.

## 10. Frontend: navegação e perfis

O arquivo `frontend/src/router.tsx` organiza as páginas por papel.

Exemplos:

- Usuário GT: início, trilha, texto, cadernos, ppp, cursos
- Articulador/Admin: tarefas, texto único, quadros, revisões, biblioteca, exportações
- Admin/Super admin: console administrativo, auditoria, relatórios, bloqueios, consultas públicas, gestão de cursos

A rota `/consultas-publicas/:token` é pública para participação externa.

## 11. Ciclos de Funcionamento (Ponta a Ponta)

### 11.1 Produção de conteúdo curricular

1. Admin define estrutura (GTs, tarefas, perguntas).
2. Membros/Articuladores produzem respostas e textos.
3. Sistema gera texto único (on-demand/assíncrono).
4. Revisões/comentários refinam o conteúdo.
5. Conteúdo final pode ser exportado e publicado.

### 11.2 Revisão editorial

1. Conteúdo vira alvo de revisão (`Revisao`).
2. Revisor registra decisão e parecer.
3. Redator ajusta conteúdo e reenfileira.
4. Diffs e auditoria suportam rastreabilidade de mudanças.

### 11.3 Consulta pública

1. Admin publica documento com token.
2. Público acessa link e envia manifestações.
3. Equipe interna acompanha contribuições via painel/API.

## 12. Configuração e Operação

Variáveis-chave:

- `REFERENCIAL_DATABASE_URL`
- `REFERENCIAL_REDIS_URL`
- `MEDIA_BACKEND`
- `DEFAULT_EXPORT_PLUGIN`, `DEFAULT_SYNTHESIS_PLUGIN`, `DEFAULT_HOOK_PLUGIN`
- `DEFAULT_THROTTLE_RATES_*`

Comandos comuns:

- Backend: `python manage.py runserver`
- Frontend: `cd frontend && npm run dev`
- Worker Celery: `celery -A config worker -l info`
- Beat: `celery -A config beat -l info`
- WebSockets (ASGI): `daphne -b 0.0.0.0 -p 8001 config.asgi:application`

## 13. Qualidade e testes

- Testes com `pytest`
- Lint com `ruff`
- Cobertura e checks automatizados em CI (`.github/workflows/ci.yml`)

---

Este documento descreve a estrutura atual do sistema com base no código do repositório. Para evoluções, o ideal é manter este arquivo atualizado junto com mudanças de modelos, rotas e fluxos.
