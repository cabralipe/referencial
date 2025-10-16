# Análise de Funcionalidades Faltantes no Frontend

## 1. Estado Atual do Frontend

### 1.1 Funcionalidades Implementadas
O frontend atual possui uma implementação básica com as seguintes funcionalidades:

- **Autenticação**: Login/logout com sessão
- **Dashboard**: Lista de tarefas com filtros básicos por status
- **Detalhes de Tarefa**: Visualização e edição de perguntas/respostas
- **CRUD Básico**: Criação e edição de respostas para perguntas

### 1.2 Arquitetura Atual
- **Framework**: React 18 + TypeScript + Vite
- **Estado**: React Query para cache e sincronização
- **Roteamento**: React Router v6
- **Estilização**: CSS modules

### 1.3 Páginas Existentes
1. **LoginPage** - Autenticação de usuários
2. **DashboardPage** - Lista de tarefas com filtros
3. **TaskDetailPage** - Detalhes e edição de tarefas

## 2. APIs Disponíveis no Backend

### 2.1 APIs Core
- `GET/POST/PUT/DELETE /api/v1/tarefas/` - Gestão de tarefas
- `GET/POST/PUT/DELETE /api/v1/respostas/` - Gestão de respostas
- `GET/POST/PUT/DELETE /api/v1/texto_unico/` - Textos únicos por GT
- `GET/POST/PUT/DELETE /api/v1/quadro/` - Quadros de oficinas
- `POST /api/v1/quadro/gerar/` - Geração automática de quadros

### 2.2 APIs de Colaboração
- `GET/POST/PUT/DELETE /api/v1/revisoes/` - Sistema de revisões
- `GET/POST/PUT/DELETE /api/v1/comentarios/` - Comentários em linha
- `GET/POST/PUT/DELETE /api/v1/notificacoes/` - Notificações in-app

### 2.3 APIs de Biblioteca
- `GET/POST/PUT/DELETE /api/v1/midias/` - Biblioteca de mídia
- `GET/POST/PUT/DELETE /api/v1/blocos/` - Blocos de texto reutilizáveis

### 2.4 APIs de Sistema
- `GET/POST/PUT/DELETE /api/v1/exports/` - Jobs de exportação
- `GET /api/v1/audit/` - Logs de auditoria
- `GET/POST/PUT/DELETE /api/v1/formularios/` - Formulários dinâmicos

### 2.5 APIs de Autenticação
- `GET /api/v1/cliente/me` - Dados do cliente atual
- `POST /api/v1/auth/login` - Login por sessão
- `POST /api/v1/auth/jwt` - Login por JWT

## 3. Funcionalidades Faltantes por Prioridade

### 3.1 ALTA PRIORIDADE

#### 3.1.1 Sistema de Textos Únicos
**Descrição**: Funcionalidade para criar e editar textos únicos por GT e tarefa.
**APIs**: `/api/v1/texto_unico/`
**Implementação Sugerida**:
- Nova página `TextoUnicoPage` 
- Hook `useTextoUnico` para CRUD
- Editor de texto rico integrado
- Versionamento com ETags

#### 3.1.2 Sistema de Quadros (Oficinas)
**Descrição**: Interface para criação e edição de quadros matriciais.
**APIs**: `/api/v1/quadro/`, `/api/v1/quadro/gerar/`
**Implementação Sugerida**:
- Componente `QuadroEditor` com grid editável
- Funcionalidade de geração automática
- Salvamento automático por célula
- Visualização responsiva

#### 3.1.3 Sistema de Revisões
**Descrição**: Fluxo completo de revisão de conteúdos.
**APIs**: `/api/v1/revisoes/`
**Implementação Sugerida**:
- Modal `RevisaoModal` para solicitar/fazer revisões
- Badge de status de revisão nos conteúdos
- Lista de revisões pendentes no dashboard
- Notificações de mudanças de status

### 3.2 MÉDIA PRIORIDADE

#### 3.2.1 Sistema de Comentários
**Descrição**: Comentários em linha para colaboração.
**APIs**: `/api/v1/comentarios/`
**Implementação Sugerida**:
- Componente `ComentarioInline` para seleção de texto
- Sidebar com lista de comentários
- Sistema de menções (@usuario)
- Resolução de comentários

#### 3.2.2 Sistema de Notificações
**Descrição**: Notificações in-app para usuários.
**APIs**: `/api/v1/notificacoes/`
**Implementação Sugerida**:
- Componente `NotificationBell` no header
- Modal/dropdown com lista de notificações
- Marcação como lida
- Diferentes tipos de notificação

#### 3.2.3 Biblioteca de Mídia
**Descrição**: Gestão centralizada de arquivos e imagens.
**APIs**: `/api/v1/midias/`
**Implementação Sugerida**:
- Página `BibliotecaPage` com grid de mídias
- Upload drag-and-drop
- Sistema de tags para organização
- Busca e filtros

### 3.3 BAIXA PRIORIDADE

#### 3.3.1 Biblioteca de Blocos de Texto
**Descrição**: Blocos reutilizáveis de texto.
**APIs**: `/api/v1/blocos/`
**Implementação Sugerida**:
- Modal `SeletorBlocos` para inserção
- Editor de blocos com preview
- Sistema de tags e categorização

#### 3.3.2 Sistema de Exportação
**Descrição**: Exportação de conteúdos para PDF/DOCX.
**APIs**: `/api/v1/exports/`
**Implementação Sugerida**:
- Modal `ExportModal` com opções
- Lista de jobs de exportação
- Download automático quando pronto
- Notificações de progresso

#### 3.3.3 Formulários Dinâmicos
**Descrição**: Criação de formulários customizados.
**APIs**: `/api/v1/formularios/`
**Implementação Sugerida**:
- Builder visual de formulários
- Diferentes tipos de campo
- Validações customizadas

#### 3.3.4 Logs de Auditoria
**Descrição**: Visualização de histórico de mudanças.
**APIs**: `/api/v1/audit/`
**Implementação Sugerida**:
- Página `AuditoriaPage` com filtros
- Timeline de mudanças
- Diff visual de alterações

## 4. Melhorias de UX/UI Necessárias

### 4.1 Navegação
- **Sidebar expandível** com menu de módulos
- **Breadcrumbs** para navegação hierárquica
- **Busca global** por conteúdos

### 4.2 Interface de Usuário
- **Design system** consistente com componentes reutilizáveis
- **Tema escuro/claro** configurável
- **Responsividade** para tablets e mobile
- **Loading states** e skeleton screens

### 4.3 Experiência do Usuário
- **Salvamento automático** com indicadores visuais
- **Undo/Redo** para editores
- **Atalhos de teclado** para ações frequentes
- **Tooltips e ajuda contextual**

### 4.4 Performance
- **Lazy loading** de componentes pesados
- **Virtualização** para listas grandes
- **Otimização de imagens** na biblioteca
- **Cache inteligente** com React Query

## 5. Considerações Técnicas

### 5.1 Gerenciamento de Estado
- Expandir uso do React Query para todas as APIs
- Implementar cache otimista para melhor UX
- Sincronização em tempo real com WebSockets

### 5.2 Componentes Reutilizáveis
- Editor de texto rico (TinyMCE/Quill)
- Componente de upload de arquivos
- Sistema de modais e overlays
- Componentes de formulário padronizados

### 5.3 Tipos TypeScript
- Expandir `types.ts` com todas as entidades
- Tipos para payloads de API
- Validação de runtime com Zod

### 5.4 Testes
- Testes unitários para hooks
- Testes de integração para fluxos
- Testes E2E para funcionalidades críticas

## 6. Roadmap de Implementação

### Fase 1 (2-3 semanas)
1. Sistema de Textos Únicos
2. Sistema de Quadros básico
3. Melhorias de navegação

### Fase 2 (3-4 semanas)
1. Sistema de Revisões
2. Sistema de Comentários
3. Notificações básicas

### Fase 3 (2-3 semanas)
1. Biblioteca de Mídia
2. Sistema de Exportação
3. Melhorias de UX/UI

### Fase 4 (2-3 semanas)
1. Formulários Dinâmicos
2. Biblioteca de Blocos
3. Logs de Auditoria
4. Otimizações finais

## 7. Conclusão

O backend possui uma arquitetura robusta com APIs bem estruturadas, mas o frontend atual utiliza apenas uma pequena fração das funcionalidades disponíveis. A implementação das funcionalidades faltantes transformará a aplicação em uma plataforma completa de colaboração para construção de referenciais curriculares.

As prioridades sugeridas focam primeiro nas funcionalidades core (textos únicos e quadros), depois nos sistemas de colaboração (revisões e comentários), e por último nas funcionalidades de suporte (biblioteca e exportação).