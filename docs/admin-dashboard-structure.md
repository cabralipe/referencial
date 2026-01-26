# Estrutura do Dashboard Admin (atual)

## Rotas principais

- `/admin/console` — Catálogo de módulos do Admin Console (cards por categoria).
- `/admin/console/:moduleId` — CRUD genérico para cada módulo.

Rotas admin existentes (anteriores ao console):
- `/admin/mural` — Administração de mural.
- `/admin/trilhas` — Administração de trilhas.
- `/admin/ppp` — Configurações do PPP.

## Navegação (sidebar)

- Entrada adicional para admins:
  - **Admin Console** (`/admin/console`)
- Entradas antigas mantidas:
  - **Admin: Trilhas** (`/admin/trilhas`)
  - **Admin: Mural** (`/admin/mural`)
  - **Admin: PPP** (`/admin/ppp`)

## Páginas do Admin Console

### 1) Catálogo de módulos
Arquivo: `frontend/src/pages/AdminConsolePage.tsx`

- Header com título e descrição.
- Campo de busca por módulo.
- (Super admin) seletor de cliente (escopo global via `X-Cliente-ID`).
- Listagem de módulos por **categoria**.

### 2) CRUD genérico por módulo
Arquivo: `frontend/src/pages/AdminModulePage.tsx`

- Tabela com colunas geradas dinamicamente a partir dos dados.
- Busca local por texto.
- Paginação simples (page/page_size).
- Botões de **Novo**, **Editar**, **Remover**.
- Drawer lateral com formulário dinâmico.
- Modo avançado **JSON** (edição direta).
- Compatível com ETag (usa `If-Match` quando disponível no item).

## Escopo de cliente

- Hook: `frontend/src/hooks/useAdminScope.ts`
- Super admin pode selecionar cliente (header `X-Cliente-ID`).
- Admin cliente opera apenas no próprio `cliente_id`.

## Módulos disponíveis (Admin Console)

Fonte: `frontend/src/pages/adminModules.ts`

### Core
- clientes
- clientes-config
- clientes-feature-flags
- clientes-temas
- usuarios
- audit-logs
- throttle-blocks
- score-entries
- session-logs

### Currículo
- gts
- areas
- tarefas
- perguntas
- respostas
- anexos
- textos-unicos
- textos-colaborativos

### Quadros
- quadros
- quadros-linhas
- quadros-colunas
- quadros-celulas

### Formulários
- formularios
- campos-dinamicos
- respostas-campos

### Revisões
- revisoes
- exports

### Comunicação
- notificacoes
- comentarios

### Biblioteca
- midias
- blocos

### Consultas
- consultas-publicas
- manifestacoes-publicas

### MEB
- meb-threads
- meb-mensagens

## Endpoints do Admin Console

Prefixo: `/api/v1/admin/*`

- `/admin/clientes`
- `/admin/clientes-config`
- `/admin/clientes-feature-flags`
- `/admin/clientes-temas`
- `/admin/usuarios`
- `/admin/audit-logs`
- `/admin/throttle-blocks`
- `/admin/score-entries`
- `/admin/session-logs`
- `/admin/gts`
- `/admin/areas`
- `/admin/tarefas`
- `/admin/perguntas`
- `/admin/respostas`
- `/admin/anexos`
- `/admin/textos-unicos`
- `/admin/textos-colaborativos`
- `/admin/quadros`
- `/admin/quadros-linhas`
- `/admin/quadros-colunas`
- `/admin/quadros-celulas`
- `/admin/formularios`
- `/admin/campos-dinamicos`
- `/admin/respostas-campos`
- `/admin/revisoes`
- `/admin/exports`
- `/admin/notificacoes`
- `/admin/comentarios`
- `/admin/midias`
- `/admin/blocos`
- `/admin/consultas-publicas`
- `/admin/manifestacoes-publicas`
- `/admin/meb-threads`
- `/admin/meb-mensagens`

## Permissões

- Permissão geral: `IsAdminConsole` (admin_cliente + super_admin).
- Restrições especiais:
  - **Clientes**: criar/remover apenas super_admin.
  - **Usuários**: admin_cliente não cria super_admin e não muda cliente.

## Arquivos-chave

Backend:
- `api/v1/admin_serializers.py`
- `api/v1/admin_viewsets.py`
- `api/v1/routers.py`
- `core/permissions.py`

Frontend:
- `frontend/src/pages/AdminConsolePage.tsx`
- `frontend/src/pages/AdminConsolePage.css`
- `frontend/src/pages/AdminModulePage.tsx`
- `frontend/src/pages/AdminModulePage.css`
- `frontend/src/pages/adminModules.ts`
- `frontend/src/hooks/useAdminScope.ts`
- `frontend/src/router.tsx`
- `frontend/src/components/layout/AppLayout.tsx`
