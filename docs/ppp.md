# PPP (Projeto Politico-Pedagogico)

## Visao geral
O modulo PPP reutiliza a mesma estrutura de trilhas do sistema (Tarefa -> Pergunta -> Resposta) para organizar a escrita do Projeto Politico-Pedagogico.

Na pratica, o PPP nao possui modelos exclusivos para "trilha PPP". Em vez disso:
- cada trilha do PPP e uma `Tarefa` ja existente;
- cada bloco da trilha e uma `Pergunta` da tarefa;
- o texto produzido fica em `Resposta` (por `GT` + `Pergunta`);
- revisoes e pareceres podem ser vinculados ao conteudo produzido (fluxo de revisao do sistema).

## Objetivo funcional
O PPP funciona como uma curadoria de trilhas ja cadastradas no cliente:
- o Admin escolhe quais `Tarefa`s entram no PPP;
- o frontend `/ppp` consome essa configuracao;
- os usuarios veem somente as trilhas permitidas, respeitando escopo de cliente e regras de perfil/GT.

## Rotas principais

### Frontend
- `/ppp`: tela do modulo PPP (lista de trilhas PPP e fluxo de edicao).
- `/admin/ppp`: tela de configuracao do PPP no frontend admin.

Observacao:
- `config/urls.py` mapeia `/admin/ppp` para o frontend React (nao para o Django Admin classico).

### API
- `GET /api/v1/ppp`: retorna configuracao PPP + trilhas configuradas.
- `GET /api/v1/ppp/config`: retorna somente a configuracao PPP do cliente.
- `PATCH /api/v1/ppp/config`: atualiza a configuracao PPP (admin do cliente).

## Como a configuracao e armazenada
A configuracao do PPP e salva em `ClienteConfig` usando a chave:
- `ppp.trilhas`

Formato normalizado atual:

```json
{
  "tarefa_ids": [1, 2, 3],
  "descricao": "texto opcional"
}
```

### Regras de normalizacao
- `tarefa_ids` aceita lista/tupla e converte os itens para inteiro.
- IDs invalidos sao ignorados.
- IDs duplicados sao removidos.
- a lista final e ordenada.
- `descricao` e opcional e sofre `trim()`.
- payload invalido (ou JSON invalido quando salvo como texto) volta para padrao.

Padrao:

```json
{
  "tarefa_ids": [],
  "descricao": ""
}
```

## Fluxo funcional (fim a fim)

### 1. Configuracao pelo Admin
1. Acessa `/admin/ppp`.
2. Seleciona as tarefas que compoem o PPP.
3. Salva via `PATCH /api/v1/ppp/config`.

Validacoes importantes:
- apenas tarefas do mesmo `cliente` podem ser gravadas na configuracao;
- se o payload enviar IDs de outro cliente, eles sao descartados;
- o endpoint exige perfil de admin do cliente (ou super admin, conforme regra geral de papeis).

### 2. Consumo pelo usuario no PPP
1. O frontend chama `GET /api/v1/ppp`.
2. A API carrega a configuracao `ppp.trilhas`.
3. Busca `Tarefa`s com os IDs configurados.
4. Ordena por `ordem`.
5. Aplica filtro por perfil/GT quando necessario.
6. Retorna `config` + `trilhas`.

Resposta (estrutura resumida):

```json
{
  "config": {
    "tarefa_ids": [10, 12],
    "descricao": "PPP municipal"
  },
  "trilhas": [
    {
      "id": 10,
      "nome": "Diagnostico",
      "ordem": 1,
      "etapa": "I",
      "tipo": "PERGUNTAS",
      "status": "rascunho",
      "created_at": "..."
    }
  ]
}
```

## Regras de acesso e filtragem

### Escopo por cliente (multi-tenant)
- o PPP e sempre carregado por `cliente`;
- a configuracao e as tarefas sao isoladas por cliente.

### Filtro por perfil (trilhas visiveis)
Para perfis `MEMBRO_GT` e `ARTICULADOR`, a listagem de trilhas PPP passa por filtro adicional:
- mostra tarefas com perguntas associadas aos GTs do usuario;
- tambem mostra tarefas com perguntas sem GT definido (globais);
- tambem pode mostrar tarefas sem perguntas.

Se o usuario nao pertence a nenhum GT, a lista pode ficar vazia para esses perfis.

### Filtro opcional por GT
`GET /api/v1/ppp?gt_id=<id>`
- filtra trilhas que tenham respostas para o `gt_id` informado.

## Modelos reutilizados pelo PPP

### `Tarefa` (curriculum)
Representa a trilha configurada no PPP.
Campos relevantes para PPP:
- `id`, `nome`, `ordem`, `etapa`, `tipo`, `status`

### `Pergunta` (curriculum)
Representa os blocos/questoes dentro da trilha PPP.
Campos relevantes:
- `tarefa`, `ordem`, `texto`, `permite_upload`, `obrigatoria`, `gts`

### `Resposta` (curriculum)
Representa o texto produzido para uma pergunta por GT.
Caracteristicas relevantes:
- unicidade por (`cliente`, `gt`, `pergunta`);
- versionamento incremental (`version`);
- `etag` para controle de concorrencia/cache;
- autor atualizado na criacao/edicao.

## Revisao e acompanhamento
O conteudo do PPP usa o fluxo geral de revisao da plataforma:
- revisoes sao registradas sobre os alvos de conteudo (ex.: respostas);
- existe escopo `PPP` em atribuicoes de revisor (`ReviewerAssignment.ScopeType.PPP`), permitindo organizacao de trabalho de revisao por contexto PPP.

## Reuso de textos
- Textos dos Cadernos podem ser vinculados a perguntas do PPP para reaproveitamento.
- Isso evita duplicacao de escrita quando a mesma discussao alimenta cadernos e PPP.

## Limitacoes atuais (implementacao)
- O PPP e municipal (escopo por cliente).
- Ja existe entidade `Escola` no dominio de curriculum (com escopo por cliente), mas o PPP ainda nao possui fluxo nativo de segmentacao por escola.
- O modulo PPP e uma "visao/configuracao" de trilhas existentes, nao um conjunto de entidades exclusivas.

## Referencias de implementacao (codigo)
- Configuracao e endpoints PPP: `api/v1/viewsets.py`
- Registro de rota API: `api/v1/routers.py`
- Mapeamento de rotas frontend (`/ppp`, `/admin/ppp`): `config/urls.py`
- Modelos reutilizados (`Tarefa`, `Pergunta`, `Resposta`): `curriculum/models.py`
- Teste de filtro por cliente em `PATCH /api/v1/ppp/config`: `tests/test_mural_ppp.py`
