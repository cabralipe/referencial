# Relatório do Módulo de Revisores

## 1) Mapeamento do escopo do revisor
O escopo é definido por `ReviewerAssignment`:
- `scope_type`: `trail`, `etapa`, `componente`, `ppp`
- `scope_id`: identifica a trilha/tarefa, etapa, área ou tarefa de PPP
- `cliente_id`: isolamento por município

Regras aplicadas:
- Revisor só enxerga revisões do seu município.
- Revisor só enxerga itens do escopo atribuído.
- Revisor sem atribuição não vê itens.

## 2) Tabelas auxiliares
Criadas/ativadas no módulo:
- `reviews.ReviewerAssignment`: define escopo do revisor por município.
- `reviews.ReviewDecision`: registra recomendações e marcações de “em andamento”.

Justificativa:
- Não existem tabelas prévias para atribuição e recomendação.
- Evitam alterar modelos principais e preservam o histórico.

## 3) Como ativar o perfil Revisor
1. Crie o usuário com papel `revisor`.
2. Atribua escopos em **Admin Console** → “Atribuições de revisor”.
3. O revisor acessa `/revisor/inbox` para iniciar as análises.

## 4) Observações de implementação
- As recomendações não alteram o status final.
- O redator/admin recebe notificações quando a recomendação é registrada.
- Comentários novos geram notificação para membros GT vinculados ao conteúdo.
