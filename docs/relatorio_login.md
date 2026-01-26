# Relatório - Login didático

## O que foi entregue
- Tela de login em duas colunas com copy didática.
- Identificação automática de perfil após autenticação.
- Validações e erros específicos para perfil não autorizado.
- Redirecionamento por perfil após login.
- Telemetria básica de eventos de login.

## Onde foi alterado
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/login/RoleSelector.tsx`
- `frontend/src/components/login/RoleInfoCard.tsx`
- `frontend/src/components/login/roles.ts`
- `tests/test_login_role.py`
- `docs/login_didatico.md`

## Como testar (manual)
1. Acesse `/login`.
2. Tente enviar com e-mail inválido ou sem perfil selecionado.
3. Faça login e confirme redirecionamento:
   - `membro_gt` -> `/inicio`
   - `revisor` -> `/revisor/inbox`
   - `articulador` -> `/redator/revisoes`

## Como testar (backend)
- Rodar `pytest tests/test_login_role.py`.

## Observações
- A validação de perfil já existia no backend e foi preservada.
- Não foi incluído “Lembrar-me” por não haver confirmação de suporte no fluxo atual de auth.
