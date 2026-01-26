# Relatório Final — Refatoração UX/Fluxo MEB Referencial

## O que foi alterado
- Novo fluxo do Membro GT com rotas didáticas: **/inicio**, **/minha-trilha**, **/texto**, **/cadernos**, **/mural**, **/ppp**, **/ajuda**.
- Layout base ajustado para o Membro GT (menu simplificado, breadcrumbs e linguagem pedagógica).
- Página **Minha Trilha** com status e progresso por missão.
- Detalhe da trilha com passo atual + checklist de conclusão.
- Editor de texto com ferramentas didáticas (títulos, listas, tabelas, BNCC), comentários por trecho e histórico de versões.
- Cadernos implementados como agrupamento lógico de textos.
- Mural com CRUD administrativo e exibição em cards para o Membro GT.
- PPP implementado como trilhas reutilizando Tarefa/Pergunta/Resposta, configurado via Admin.
- Guards de acesso por perfil no front + validações de permissão no backend.
- Testes para acesso por perfil, escopo municipal e progresso da trilha.

## O que foi reaproveitado do banco
- **Tarefa/Pergunta/Resposta**: base das trilhas e do PPP.
- **Revisão**: validação de blocos (status aprovado/em revisão/devolvido).
- **Notificação**: base para Mural (posts replicados por usuário, sem nova tabela).
- **BlocoTexto**: base dos Cadernos (tag `caderno:*`).
- **ClienteConfig**: configuração de PPP (lista de tarefas vinculadas).
- **GT**: escopo principal do Membro GT.

## Dívida técnica / limitações conhecidas
- Mural usa notificações replicadas por usuário (pode crescer rápido em clientes grandes).
- Comentários por trecho usam âncora simplificada (parágrafo), sem seleção de texto real.
- Cadernos dependem de tags no BlocoTexto (não há entidade dedicada de Caderno).
- PPP por escola não implementado (ausência de entidade Escola).

## Como ativar/usar os novos fluxos
1. **Membro GT**: acessar **/inicio** e seguir para **/minha-trilha**.
2. **Editor**: abrir **/texto** e selecionar o texto do GT.
3. **Cadernos**: criar em **/cadernos**, depois gerenciar textos em **/cadernos/:id**.
4. **Mural**: Admin publica em **/admin/mural**; Membro GT lê em **/mural**.
5. **PPP**: Admin configura trilhas em **/admin/ppp**; Membro GT acessa em **/ppp**.
