## Objetivo
- Mostrar na seção “Presença em tempo real” quem está online agora (cards `li`), atualizando automaticamente.
- Abaixo, exibir uma seção “Histórico de login” com uma lista cronológica dos acessos nos últimos 30 dias: data/hora exata do login, nome do usuário, duração da sessão e dispositivo utilizado.

## Backend
- Extender `core.models.UserSessionLog` para armazenar `user_agent` (texto) e opcionalmente `device` (texto derivado).
- Atualizar `core.activity.touch_user_session(request)` para capturar `request.META['HTTP_USER_AGENT']` e preencher `user_agent` (e `device` se aplicável) na criação/atualização.
- Ampliar `OnlineUserSerializer` em `api/v1/serializers.py` para retornar:
  - `first_seen_at`, `last_seen_at` (já existem)
  - `session_duration_seconds` (computado: `max(last_seen_at - first_seen_at, 0)`, em segundos)
  - `device_label` (derivado de `user_agent` com heurística simples: desktop/mobile/tablet/browser)
- Consolidar o endpoint `GET /api/v1/audit/sessions?days=30&limit=200` para histórico do cliente atual, ordenado por `first_seen_at` (desc), retornando os campos acima.

## Realtime (auto‑atualização)
- Manter o polling atual de `/audit/online` (refetch a cada 60s).
- Opcional (se desejar “tempo real” verdadeiro): criar um `OnlineConsumer` (Channels) com grupo `online.<cliente_id>` para emitir eventos de presença quando `touch_user_session` atualizar `last_seen_at`. O frontend assina e atualiza imediatamente sem esperar o próximo poll.

## Frontend
- Atualizar `AuditLogsPage.tsx`:
  - Cards `li` já exibem nome, e‑mail, entrada e última atividade; manter e destacar estado (ponto verde).
  - Adicionar seção “Histórico de login”: usa `useSessionHistory({ days: 30, limit: 200 })` para renderizar lista cronológica com:
    - `Login`: `first_seen_at` (formatado `pt-BR`)
    - `Usuário`: nome/e‑mail
    - `Duração`: `session_duration_seconds` (humanizado: minutos/horas)
    - `Dispositivo`: `device_label`
  - Responsividade: empilhar colunas em telas pequenas, manter grid em desktop; usar classes existentes (`audit__online-list`, `audit__card`, etc.) com CSS adaptado.
  - Auto‑atualização: manter refetch a cada 60s; se `OnlineConsumer` estiver habilitado, anexar assinatura via hook para aplicar updates incrementais.

## Segurança e Desempenho
- Evitar armazenar dados sensíveis; registrar apenas `user_agent` bruto.
- Limitar histórico por `days` e `limit` com índices já existentes em `UserSessionLog`.
- Rate limit permanece sob DRF throttle padrão.

## Testes e Verificação
- Backend: testes unitários para cálculo de duração e captura de `user_agent`.
- Frontend: verificação visual responsiva e checagem de atualização automática.
- Manual: acessar página Auditoria e confirmar contagem online, cards e a lista de histórico preenchida.

## Observação
- Caso prefira, podemos implementar apenas o polling (sem WebSocket) inicialmente; a experiência já será automática. O canal `OnlineConsumer` pode ser adicionado depois sem quebrar a UI.

Confirma proceder com essas mudanças?