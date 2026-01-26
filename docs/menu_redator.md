# Menu do Redator (simplificado)

## Objetivo
Oferecer um menu curto e didático para o redator, mantendo rotas antigas e reunindo itens técnicos dentro das telas.

## Novo menu (5 itens)
1) **Painel** — `/redator/painel`
2) **Revisões** — `/redator/revisoes`
3) **Conteúdos** — `/redator/conteudos`
4) **Mural** — `/redator/mural`
5) **Exportações** — `/redator/exportacoes`

## Onde ficaram os itens técnicos
- Diff, Comentários, Pareceres e Referências: agora são abas dentro do detalhe de revisão.
- Trilhas, Texto único, Quadros e Formulários: centralizados na página **Conteúdos** com links para rotas existentes.

## Redirecionamentos mantidos
- `/redator/fila` -> `/redator/revisoes`
- `/redator/diff` -> `/redator/revisoes?tab=diff`
- `/redator/comentarios` -> `/redator/revisoes?tab=comentarios`
- `/redator/pareceres` -> `/redator/revisoes?tab=parecer`
- `/redator/referencias` -> `/redator/revisoes?tab=referencias`

## Mural (acesso do redator)
- O redator pode criar, editar e remover posts no mural.
- Membro GT continua com acesso somente leitura.

## Identidade do menu
- Exibe apenas o nome do cliente.
- Papel do usuário: **Redação**.
