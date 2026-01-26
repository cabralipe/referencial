# Relatório - Menu do Redator

## O que foi entregue
- Sidebar do redator com 5 itens (Painel, Revisões, Conteúdos, Mural, Exportações).
- Página agregadora `/redator/conteudos`.
- Revisões com abas internas (Texto, Comentários, Parecer, Diff, Referências).
- Acesso do redator ao Mural com CRUD.
- Redirecionamentos das rotas antigas.

## Arquivos principais
- `frontend/src/components/layout/AppLayout.tsx`
- `frontend/src/router.tsx`
- `frontend/src/pages/RedatorConteudosPage.tsx`
- `frontend/src/pages/RedatorMuralPage.tsx`
- `frontend/src/pages/RedatorInboxPage.tsx`
- `frontend/src/pages/RedatorReviewDetailPage.tsx`
- `api/v1/viewsets.py`
- `core/permissions.py`
- `tests/test_mural_permissions.py`
- `docs/menu_redator.md`

## Como testar (manual)
1. Logar como redator e validar o novo menu.
2. Acessar `/redator/revisoes` e alternar entre abas.
3. Abrir um item de revisão e navegar entre Texto / Comentários / Parecer / Diff / Referências.
4. Acessar `/redator/conteudos` e abrir os módulos disponíveis.
5. Acessar `/redator/mural` e publicar um aviso.

## Como testar (backend)
- `pytest tests/test_mural_permissions.py`

## Observações
- Rotas antigas continuam funcionando via redirect.
- O mural mantém escopo por cliente; membros de GT seguem com leitura somente.
