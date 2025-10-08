# Backend Referencial Curricular

Plataforma Django multicliente para construção de referenciais curriculares com API REST, Channels, Celery e arquitetura configurável por plugins.

## Requisitos

- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- (Opcional) MinIO/S3 para armazenamento de mídia

## Setup rápido (WSL/Linux)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
```

Serviços úteis:

- Servidor Django: `python manage.py runserver`
- Channels via Daphne: `daphne -b 0.0.0.0 -p 8001 config.asgi:application`
- Worker Celery: `celery -A config worker -l info`
- Celery Beat: `celery -A config beat -l info`

Use `make up`, `make worker`, `make sockets` ou `make beat` como atalhos.

## Frontend (React + Vite)

O SPA fica em `frontend/` e consome a API REST.

```bash
cd frontend
npm install
npm run dev      # Vite em http://localhost:5173
npm run build    # Gera artifacts em static/frontend/
```

- Ajuste `VITE_API_BASE_URL` se a API estiver em outro host (padrão `/api/v1`).
- Após `npm run build`, o Django serve o bundle via rota catch-all em `config/urls.py`.
- Em desenvolvimento, rode Vite separado e mantenha o backend em `localhost:8000`.

## Variáveis de ambiente

Configure o arquivo `.env` (exemplo em `.env.example`). Principais chaves:

- `REFERENCIAL_DATABASE_URL`: URL do PostgreSQL (fallback para SQLite em dev)
- `REFERENCIAL_REDIS_URL`: broker/result do Celery + Channels
- `MEDIA_BACKEND`: `local` ou `s3`
- `DEFAULT_*_PLUGIN`: plugins ativos por cliente (padrão `default`)

## Plugins

Plugins ficam em `plugins/` e expõem funções padrão:

- `plugins/exports/<nome>/provider.py`: `render_pdf(ctx)` / `render_docx(ctx)`
- `plugins/synthesis/<nome>/provider.py`: `preprocess(ctx)` / `postprocess(ctx)`
- `plugins/hooks/<nome>/provider.py`: `dispatch(evento, payload)`

Ative plugins por cliente ajustando `ClienteConfig` (`chave=export_plugin`) ou variáveis de ambiente.

## Principais rotas

- `POST /api/v1/auth/login` — login por sessão
- `POST /api/v1/auth/jwt` — tokens JWT (SimpleJWT)
- `GET /api/v1/cliente/me` — contexto do cliente (tema, flags, configs)
- `GET /api/v1/tarefas/` — lista de tarefas por cliente
- `POST /api/v1/respostas` — upsert com controle de versão via `If-Match`
- `POST /api/v1/texto_unico/gerar` — agenda geração via Celery
- `PUT /api/v1/quadro/{id}/celula` — salva células idempotentes
- `POST /api/v1/exports` — agenda exportações PDF/DOCX
- `GET /api/v1/audit` — trilha de auditoria
- `POST /api/v1/revisoes` / `PUT /api/v1/revisoes/{id}` — fluxo de revisão/aprovação com ETag
- `POST /api/v1/comentarios` / `PUT /api/v1/comentarios/{id}` — comentários em linha, resolução e menções
- `GET /api/v1/diff?alvo_tipo=&alvo_id=&from=&to=` — diff HTML entre versões de respostas/texto único
- `GET /api/v1/notificacoes` / `PUT /api/v1/notificacoes/{id}/lida` — inbox in-app
- `POST /api/v1/midias` e `POST /api/v1/blocos` — biblioteca de mídia/blocos reutilizáveis

WebSockets disponíveis em `/ws/presence/{docType}/{id}` para presença/locks leves.
Streams adicionais:
- `/ws/stream/{alvo_tipo}/{alvo_id}` para eventos de comentários e revisões
- `/ws/notifications/` para notificações em tempo real por usuário

## Testes e QA

```bash
pytest --cov=.
ruff check .
```

GitHub Actions (`.github/workflows/ci.yml`) executa lint, checks, migrations e testes com cobertura mínima recomendada (80%).

## Feature flags

Ative/desative funcionalidades de curto prazo via `ClienteFeatureFlag`:

```
ff.comments.enabled
ff.reviews.enabled
ff.diff.enabled
ff.notifications.enabled
ff.library.enabled
```

## Estrutura

```
config/            # settings, ASGI, Celery
core/              # modelos centrais, autenticação, auditoria, plugins
curriculum/        # GTs, tarefas, perguntas, respostas, texto único
workshop/          # quadros e células
dynamicforms/      # formulários e campos dinâmicos
exports/           # exportações e serviços auxiliares
api/v1/            # serializers, viewsets, urls
sockets/           # Channels consumers
tasks/             # tarefas Celery (exports, síntese, limpeza)
plugins/           # providers default
tests/             # suíte pytest (API, permissões, síntese, exportações)
```

## Notas

- `AUTH_USER_MODEL = core.Usuario` com suporte a multi-cliente (`cliente_id`) e perfis (`role`).
- Soft delete padrão (`is_deleted`) e filtros automáticos por `cliente_id` via middleware/manager.
- Exportações armazenadas via `default_storage`; configure S3/MinIO definindo `MEDIA_BACKEND=s3`.
- Rate limiting configurável via `.env` (`DEFAULT_THROTTLE_RATES_*`).
