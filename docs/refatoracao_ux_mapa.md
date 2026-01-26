# Mapa de Integração - Refatoração UX Plataforma MEB Referencial

## 1) Entidades atuais -> papel na nova UX

- `core.Usuario` (role)
  - `super_admin` -> Superadmin
  - `admin_cliente` -> Admin SEMED
  - `articulador` -> Redator (revisor/editor)
  - `membro_gt` -> Membro GT (perfil foco)
  - `leitor` -> Leitor (somente consulta)
- `curriculum.GT` -> Grupo de Trabalho (escopo principal do Membro GT)
- `curriculum.Tarefa` -> Trilha (passos principais por etapa/modo)
- `curriculum.Pergunta` -> Bloco/Missão dentro da Trilha (pergunta orientadora)
- `curriculum.Resposta` -> Resposta do bloco + base de progresso
- `curriculum.TextoColaborativo` -> Texto colaborativo (editor principal do Membro GT)
- `curriculum.TextoUnico` -> Texto consolidado (síntese/revisão do Redator)
- `reviews.Revisao` -> Validação/parecer do Redator (status do bloco)
- `comments.Comentario` -> Comentários por trecho (ancoras por parágrafo)
- `library.BlocoTexto` -> Texto reutilizável (base para Cadernos)
- `library.Midia` -> Links/anexos de apoio
- `workshop.Quadro` -> Quadros/oficinas (apoio, não exibido para Membro GT)
- `notifications.Notificacao` -> Base para Mural (posts replicados por usuário)
- `consultas.ConsultaPublica` -> Consulta pública (permanece como área administrativa)

## 2) Rotas antigas -> rotas novas (ou reorganizadas)

### Fluxo Membro GT (novo)
- `/` (Dashboard atual) -> `/inicio`
- `/tarefas` -> `/minha-trilha` (lista de trilhas do GT)
- `/tarefas/:tarefaId` -> `/minha-trilha/:trilha_id` (blocos da trilha)
- `/texto-unico` -> `/texto/:id` (editor colaborativo do texto)
- `/biblioteca` -> `/cadernos` (cadernos como agrupamento de textos)
- `/biblioteca` (detalhe) -> `/cadernos/:id`
- `/notificacoes` -> `/mural` (avisos)
- `/` (área de ajuda atual via MEB chat) -> `/ajuda`
- (novo) -> `/ppp` (lista de trilhas PPP)
- (novo) -> `/ppp/:id` (blocos + editor PPP)

### Fluxo Redator/Admin
- `/revisoes` -> `/redator/revisoes`
- `/tarefas` -> `/admin/trilhas` (visão geral e progresso por GT)
- `/notificacoes` + (novo) -> `/admin/mural` (CRUD de avisos)
- (novo) -> `/admin/ppp` (gestão das trilhas PPP)

### Rotas técnicas (mantidas, porém ocultas para Membro GT)
- `/quadros`
- `/formularios`
- `/comentarios`
- `/diff`
- `/auditoria`
- `/relatorios`
- `/consultas-publicas`
- `/exportacoes`
- `/gamificacao`
- `/bloqueios`

## 3) O que será escondido do Membro GT e o que será exposto

### Expor para Membro GT (menu didático)
- Início
- Minha Trilha
- Construção de Texto
- Cadernos
- Mural
- Ajuda
- PPP

### Esconder do Membro GT (mantido para Admin/Redator)
- Relatórios
- Consultas públicas
- Exportações
- Diff
- Auditoria
- Gamificação
- Bloqueios
- Formulários técnicos
- Quadros/oficinas
- Configuração de tarefas/perguntas (admin)

## 4) Escopo municipal e GT

- Escopo municipal: `cliente_id` via middleware + `HasClientScope` em API.
- Escopo por GT: `curriculum.GT.membros` filtra respostas, textos e revisões para Membro GT.
- Admin/Redator têm visão ampla do cliente; Membro GT vê apenas seus GTs.
