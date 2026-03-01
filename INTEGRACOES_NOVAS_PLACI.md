# Novas Integracoes da PLACI

Este documento explica as novas integracoes implementadas na reformulacao da plataforma para o modelo PLACI.

## 1. Visao Geral

A PLACI agora passa a operar com tres eixos integrados:

1. Ambiente de Cursos
2. Ambiente de Construcao Documental (PPP e Referencial)
3. Banco Colaborativo Institucional

Esses eixos conversam por API REST, servicos de dominio, notificacoes e analytics, mantendo isolamento por cliente (multi-tenant).

## 2. Integracao Courses + Plano Estruturado

Foi criado o modelo `PlanoAula` estruturado no dominio de cursos para suportar editor multi-step e salvamento parcial:

- Escola, etapa/modalidade, componente e unidade tematica
- Habilidades (JSON)
- Objetivos, conteudos, metodologia, recursos e avaliacao
- Estrategias de recomposicao e inclusivas
- Referencias
- Vinculos com PPP e referencial (`metas_ppp` e `habilidades_referencial`)

### Endpoints novos

- `GET/POST /api/v1/planos-estruturados`
- `GET/PATCH/DELETE /api/v1/planos-estruturados/{id}`
- `PATCH /api/v1/planos-estruturados/{id}/autosave`
- `POST /api/v1/planos-estruturados/{id}/submit`

### Fluxo

1. Usuario cria/edita plano no frontend.
2. Frontend envia `autosave` por debounce.
3. Plano muda de status ao enviar para revisao.
4. Evento de notificacao e disparado no envio.

## 3. Integracao Rubrica + Avaliacao Formativa

Foi adicionado um subsistema de rubricas no modulo de cursos:

- `Rubrica`
- `RubricaCriterio`
- `AvaliacaoPlano`

### Endpoints novos

- `GET/POST /api/v1/rubricas`
- `GET/POST /api/v1/rubricas-criterios`
- `GET/POST /api/v1/avaliacoes-planos`

### Fluxo

1. Administracao define rubrica por curso.
2. Avaliador registra pontuacao por criterio.
3. Autor do plano recebe notificacao de plano avaliado.

## 4. Integracao Motor de Certificacao

A logica de certificacao foi isolada em servico de dominio:

- Arquivo: `courses/services/certification_service.py`

Regras avaliadas por curso:

- Percentual minimo de conclusao
- Numero minimo de planos
- Presenca obrigatoria
- Entrega final obrigatoria
- Publicacao no banco (opcional/configuravel)

### Endpoints novos

- `GET /api/v1/certificacao/{curso_id}`
- `POST /api/v1/certificacao/{curso_id}/emit`

### Fluxo

1. Servico avalia checks.
2. Se aprovado, certificado e emitido.
3. Notificacao de certificacao liberada e enviada.

## 5. Integracao Banco Colaborativo

Foi criado o modulo `bank` com:

- `PlanoPublicado`
- `PlanoPublicadoComentario`
- `PlanoPublicadoAvaliacao`

### Endpoints novos

- `GET/POST /api/v1/banco/publicacoes`
- `POST /api/v1/banco/publicacoes/{id}/curadoria`
- `GET/POST /api/v1/banco/comentarios`
- `GET/POST /api/v1/banco/avaliacoes`

### Fluxo

1. Plano publicado entra em curadoria.
2. Curadoria aprova/rejeita.
3. Comentarios e avaliacoes institucionais podem ser adicionados.
4. Autor recebe notificacoes de eventos do banco.

## 6. Integracao Documentos (PPP e Referencial)

Foi criado o modulo `documents` com subcontextos:

- `ppp` (`PlanoMetaPPP`)
- `referencial` (`ReferencialHabilidade`)
- `versioning` (`DocumentoVersao`)
- `publication` (`DocumentoPublicacao`)

### Endpoints novos

- `GET/POST /api/v1/documentos/ppp-metas`
- `GET /api/v1/documentos/ppp-metas/{id}/relatorio`
- `GET/POST /api/v1/documentos/referencial-habilidades`
- `GET/POST /api/v1/documentos/versoes`
- `GET/POST /api/v1/documentos/publicacoes`

### Fluxo

1. Metas PPP e habilidades de referencial sao cadastradas.
2. Plano estruturado referencia essas chaves.
3. Relatorio por meta PPP agrega planos relacionados.

## 7. Integracao Analytics

Foi criado o modulo `analytics` com dashboards:

- Dashboard de usuario
- Dashboard admin municipal

### Endpoints novos

- `GET /api/v1/analytics/dashboard`
- `GET /api/v1/analytics/admin`

### Indicadores

- Cursos ativos e percentual medio
- Planos enviados
- Engajamento por escola
- Producao por componente
- Media de avaliacao por rubrica
- Certificados emitidos

## 8. Integracao Notificacoes e Eventos

As novas acoes foram integradas ao servico de notificacoes in-app e websocket:

- Plano enviado
- Plano avaliado
- Curadoria no banco
- Comentario no banco
- Certificacao liberada

As notificacoes passam por:

1. Registro em banco (`notifications.Notificacao`)
2. Broadcast realtime (`ws/notifications`)
3. Tarefa assincrona de email (Celery)

## 9. Integracao Frontend (Rotas Novas)

Rotas adicionadas para a nova experiencia:

- `/dashboard`
- `/cursos/:id/modulo/:moduloId`
- `/plano/:id/editar`
- `/banco`
- `/documentos/ppp`
- `/documentos/referencial`
- `/analytics`

Destaque:

- Novo editor de plano multi-step com autosave por debounce.

## 10. Integracao de Documentacao OpenAPI

Foi disponibilizado schema OpenAPI em:

- `GET /api/v1/schema`

Isso habilita documentacao e integracoes futuras com geradores de cliente e ferramentas de QA.

## 11. Multi-tenant e Seguranca

Todas as novas entidades seguem o padrao `TenantModel` com:

- Escopo automatico por `cliente_id`
- Soft delete
- Compatibilidade com alternancia de cliente por `super_admin` (header `X-Cliente-ID`)

Assim, as novas integracoes mantem isolamento por cliente de ponta a ponta.

