# Fluxo do Revisor

Este documento descreve como o perfil **Revisor** trabalha dentro do módulo de revisões.

## 1) O que o revisor faz
- Recebe itens atribuídos por escopo (trilha, etapa, componente ou PPP).
- Analisa textos e quadros submetidos.
- Registra comentários e orientações.
- Conclui a revisão registrando uma **recomendação** (validar, devolver ou ajustes menores).
- **Não** altera o status final da etapa (a decisão final é do redator/admin).

## 2) Inbox do Revisor
Rota: `/revisor/inbox`

Abas principais:
- **Para revisar**: itens recém submetidos.
- **Em andamento**: itens marcados pelo revisor.
- **Revisado por mim**: itens com recomendação registrada.
- **Devolvido**: itens já devolvidos pelo redator.
- **Validado**: itens já validados pelo redator.

Cada item mostra:
- trilha/etapa (quando disponível),
- bloco/título,
- autor (Membro GT),
- data de envio,
- status,
- indicadores (comentários pendentes, alterações desde a última revisão, devoluções).

## 3) Painel de revisão
Ao abrir um item:
- Conteúdo atual do bloco/texto/quadro.
- Orientação do bloco (quando disponível).
- Materiais do mural relacionados ao GT.
- Comentários abertos e resolvidos.
- Diff entre versões (se disponível).
- Checklist de revisão.

## 4) Recomendação do revisor
Ao concluir:
- **Recomendar validação**
- **Recomendar devolução**
- **Recomendar ajustes menores**

A recomendação é registrada e notifica o redator/admin. O redator decide validar/devolver.

## 5) Como o redator consome a recomendação
Na Inbox do Redator:
- Itens revisados recebem badge de recomendação.
- No detalhe da revisão, o redator visualiza checklist e nota do revisor.
- A decisão final ocorre em “Validar” ou “Devolver”.
