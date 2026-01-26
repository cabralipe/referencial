# Login didático (tela única)

## Objetivo
Remodelar a tela de acesso em uma única experiência didática para três perfis (Articulador, Revisor, Redator),
reduzindo erro de perfil e explicando o papel do usuário já no login.

## Experiência
- Duas colunas: informativa à esquerda, formulário à direita.
- Copy alinhada à proposta didática: logo/nome, tagline e benefícios.
- O sistema identifica o perfil do usuário automaticamente após autenticação.
- Erros claros e acessíveis com foco visível e `aria-describedby`.

## Perfis (labels e regras)
- Articulador (membro GT): `membro_gt`
- Revisor: `revisor`
- Redator: `articulador`

As chaves internas seguem o backend atual.

## Validações e erros
- Campos obrigatórios com mensagens inline.
- E-mail valida formato antes de habilitar o botão.
- Falha de credenciais:
  - "E-mail ou senha inválidos. Tente novamente."
- Offline:
  - "Não foi possível conectar. Verifique sua internet."

## Redirecionamento pós-login
- Articulador (membro GT) -> `/inicio`
- Revisor -> `/revisor/inbox`
- Redator -> `/redator/revisoes`

Se houver rota prévia em `state.from`, ela prevalece.

## Telemetria
Eventos disparados (com role selecionada, sem e-mail):
- `login_attempt`
- `login_success`
- `login_failure` (tipo: credenciais/perfil/offline/erro)

Se não houver infra, os eventos aparecem em `console.debug` como fallback.

## Arquivos principais
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/login/RoleSelector.tsx`
- `frontend/src/components/login/RoleInfoCard.tsx`
- `frontend/src/components/login/roles.ts`
- `api/v1/serializers.py` (validação de perfil já existente)

## Testes
Backend:
- `tests/test_login_role.py` garante 403/400 para perfil inválido e 200 para perfil correto.

Frontend:
- Não há infraestrutura de testes React configurada no projeto; validações foram mantidas no componente.
