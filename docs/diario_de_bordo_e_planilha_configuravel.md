# Ambiente do Professor — Diário de Bordo e Planilha Configurável

Este documento descreve os dois módulos entregues no app `ava`:

1. **Diário de Bordo** — registro estruturado de cada encontro/aula do professor.
2. **Planilha configurável** — modelos de planilha montados pela interface, sem
   colunas fixas no código, com importação e exportação.

Ambos reaproveitam a arquitetura existente: `TenantModel`/`ClientScopedManager`
para isolamento por município, `private_ava_storage` para arquivos, os papéis de
`core.Usuario` para permissões e `core.AuditLog` para auditoria.

---

## 1. Diário de Bordo

### 1.1 Modelos

| Modelo | Arquivo | Papel |
| --- | --- | --- |
| `DiarioBordo` | `ava/models/diario.py` | O encontro em si |
| `DiarioBordoParticipante` | `ava/models/diario.py` | Lista nominal de presença |
| `DiarioBordoMidia` | `ava/models/diario.py` | Fotografias e comprovantes |

### 1.2 Origem da aula

O campo obrigatório `origem` define quais blocos do formulário aparecem:

| Valor | Rótulo | Exige curso/turma | Exige local e tipo |
| --- | --- | --- | --- |
| `no_sistema` | No sistema | sim | não |
| `presencial_externa` | Presencial externa | não (proibido) | sim |
| `atividade_externa` | Atividade externa | não (proibido) | sim |
| `hibrida` | Híbrida | sim | sim |

Regras aplicadas em `DiarioBordo.clean()`:

- Origem `no_sistema`/`hibrida` **exige** `curso`; `modulo` e `aula` são opcionais
  mas, quando informados, precisam pertencer ao curso/módulo selecionado.
- Origens puramente externas **não aceitam** `curso`, `modulo` ou `aula` — isso
  evita criar uma aula artificial no AVA só para registrar uma atividade externa.
- Origens com componente externo exigem `local_realizacao` e `tipo_atividade`.
- Ao informar apenas a `aula`, `save()` deduz `modulo` e `curso` automaticamente.

Para evitar registros duplicados de uma aula que já existe no AVA, a tela de
criação aceita `?aula=<id>`: o método `aplicar_dados_da_aula()` pré-preenche
curso, módulo, título e conteúdo a partir da aula cadastrada, e o professor
complementa com o que efetivamente aconteceu.

### 1.3 Fluxo de status

```
rascunho ──enviar──> enviado ──revisar──> revisado
                        │                    │
                        └──revisar+bloquear──┴──> bloqueado
                        ▲
                     reabrir (admin/coordenação/direção)
```

- **Rascunho** — único estado em que o professor edita, anexa fotos e mexe na
  frequência.
- **Enviado** — trava a edição do professor. O envio exige frequência > 0.
- **Revisado / Bloqueado** — registrados por admin, coordenação ou direção.
  `bloqueado` trava a edição inclusive para administradores.

Transições ficam em `ava/services/diario_service.py` (`DiarioBordoService`).

### 1.4 Frequência

Ao abrir **Novo registro**, a primeira pergunta é qual curso será registrado.
A seleção carrega título, ementa/descrição, carga horária, módulos, aulas e a
lista de cursistas. Ao selecionar uma aula, o título e o resumo são sugeridos;
textos já editados pelo professor são preservados. A tela de frequências também
oferece **Registrar diário de bordo**, mantendo o curso consultado.

Ao salvar, as matrículas ativas e concluídas de usuários ativos do mesmo
município são incluídas na lista nominal, sem cadastro manual e sem marcar
presença automaticamente. Matrículas canceladas, suspensas e removidas não são
carregadas. Editar novamente o diário não duplica os alunos nem apaga presenças.

A frequência pode ser registrada por **lista presencial**, no checklist da turma,
ou por **link e QR Code**. Ambos atualizam a lista nominal e o total de presentes
do diário. O professor responsável pode acessar o checklist de seu diário mesmo
quando não é gestor do curso. Trocar o curso substitui a turma e limpa as
presenças da chamada anterior. Atividades externas sem curso conservam o
cadastro manual de participantes.

#### Presença retroativa e lista nominal

Selecione **Presença retroativa** na frequência do diário e informe a data real
do encontro (até a data de hoje). Ao salvar, o checklist abre automaticamente com
os matriculados do curso. Marque quem compareceu e salve: a tela exibe a lista
nominal de presentes, e o diário e o percentual de frequência são atualizados.
Os ausentes ficam identificados separadamente. A data de criação e a auditoria
registram quando o lançamento foi feito e quem o fez.

A tela **Frequência dos cursos** também oferece a opção **Registrar presença
retroativa**. Nesse modo, a chamada é marcada como realizada e a confirmação por
link é encerrada. Datas futuras são rejeitadas. Diários comuns com data futura
permanecem fora do cálculo enquanto o encontro não tiver ocorrido.

#### Exclusão de registros

Use **Excluir registro** no diário ou **Excluir registro de presença** na
chamada. A tela de confirmação mostra qual registro será excluído. Cancelar ou
apenas abrir a tela não altera os dados.

Excluir o diário retira sua lista nominal e seus anexos das telas, encerra a
chamada vinculada e seu QR Code e remove o encontro do cálculo da frequência.
Excluir apenas a chamada mantém o diário e limpa sua frequência. Se uma nova
chamada for criada para esse diário, ela recebe outro token; o QR Code excluído
não volta a funcionar. Os registros são removidos logicamente, preservando os
arquivos físicos e a auditoria. Aplicam-se as permissões de edição existentes;
um registro bloqueado precisa ser reaberto antes da exclusão.

Para instalar esta atualização, aplique a migração
`ava.0025_presenca_retroativa` com `python manage.py migrate` antes de iniciar a
nova versão.

### 1.5 Fotos e comprovantes

- Armazenados em `private_ava_storage`, sob
  `ava/diario-bordo/<cliente>/<escola>/<diario>/`.
- Servidos **apenas** pela view `diario_midia_arquivo`, que reaplica o escopo do
  usuário e envia `Cache-Control: private, no-store` e `X-Content-Type-Options:
  nosniff`. Não existe URL pública.
- Validação em três camadas: extensão (`FileExtensionValidator`), tipo MIME
  declarado no upload, e tamanho (máximo de 10 MB por arquivo).
- Fotografias (`tipo=foto`) aceitam apenas JPG, PNG, WEBP e HEIC.
- `consentimento_registrado` documenta a autorização de uso de imagem (LGPD);
  `DiarioBordoParticipante.identificacao` é livre e não deve receber dados
  sensíveis.

### 1.6 Telas e rotas

| Rota | Nome | Função |
| --- | --- | --- |
| `/ava/gestao/diario/` | `ava:diario_lista` | Lista com filtros |
| `/ava/gestao/diario/novo/` | `ava:diario_novo` | Criação |
| `/ava/gestao/diario/<id>/` | `ava:diario_detalhe` | Visualização e revisão |
| `/ava/gestao/diario/<id>/editar/` | `ava:diario_editar` | Edição do rascunho |
| `/ava/gestao/diario/exportar/<formato>/` | `ava:diario_exportar` | XLSX ou CSV |

Filtros disponíveis na lista: busca livre, origem, status, modalidade
(`tipo_atividade`), escola, professor, curso e período (`data_inicio`/`data_fim`).
A exportação respeita exatamente os filtros aplicados e traz uma coluna
**Origem** que distingue aula do sistema, presencial e atividade externa.

### 1.7 Permissões

| Papel | Alcance |
| --- | --- |
| Professor, Coordenador, Diretor | Apenas registros da própria escola |
| Admin do cliente | Todas as escolas do município |
| Super admin | Todos os municípios |
| Demais papéis (ex.: Leitor) | Sem acesso — HTTP 403 |

Revisar, bloquear e reabrir exigem Admin, Super Admin, Coordenador ou Diretor.

---

## 2. Planilha configurável

### 2.1 Modelos

| Modelo | Papel |
| --- | --- |
| `ModeloPlanilha` | Nome, descrição, versão, escopo (escola/curso), ativo |
| `ColunaPlanilha` | Coluna: título, chave, tipo, ordem, obrigatoriedade, opções, validações, visibilidade, valor padrão |
| `RegistroPlanilha` | Uma linha preenchida |
| `ValorRegistroPlanilha` | O valor de uma coluna, gravado no campo tipado correto |
| `ImportacaoPlanilha` | Auditoria de cada importação (arquivo, modo, mapeamento, erros, totais) |

Os valores **não** ficam presos ao XLSX: cada célula vira uma linha de
`ValorRegistroPlanilha`, gravada no campo adequado ao tipo
(`valor_texto`, `valor_numero`, `valor_data`, `valor_booleano`,
`valor_referencia_id`, `arquivo`). Isso é o que permite pesquisar, filtrar,
ordenar, editar, exportar e auditar. O arquivo original fica preservado em
`ImportacaoPlanilha.arquivo`, no storage privado.

### 2.2 Tipos de coluna

| Tipo | Campo de destino | Observação |
| --- | --- | --- |
| Texto / Texto longo | `valor_texto` | Aceita `min_length`, `max_length`, `regex` |
| Data | `valor_data` | Aceita `aaaa-mm-dd`, `dd/mm/aaaa`, `dd-mm-aaaa`, `aaaa/mm/dd`, `dd.mm.aaaa` |
| Número inteiro / decimal | `valor_numero` | Aceita `min` e `max` |
| Sim/Não | `valor_booleano` | Aceita `sim/não`, `1/0`, `true/false`, `x` |
| Seleção | `valor_texto` | Só aceita as opções configuradas (sem diferenciar acentuação de caixa) |
| Professor / Escola / Aluno-Participante | `valor_referencia_id` + rótulo em `valor_texto` | Resolvido por e-mail ou nome, **dentro do município do modelo** |
| Arquivo | `arquivo` | Campo `FileField` no storage privado |

### 2.3 Regras de validação

`ColunaPlanilha.validacoes` é um objeto JSON. Chaves reconhecidas:

```json
{"min": 0, "max": 40}
{"min_length": 3, "max_length": 120}
{"regex": "^[0-9]{11}$"}
{"data_min": "2026-01-01", "data_max": "2026-12-31"}
```

### 2.4 Importação — quatro etapas

1. **Upload** (`ava:planilha_importar`) — o arquivo é gravado no storage privado
   e os cabeçalhos são lidos.
2. **Mapeamento** (`ava:planilha_importar_mapear`) — cada cabeçalho aponta para
   uma coluna configurada. O sistema sugere o casamento automaticamente,
   ignorando acentos, pontuação e caixa.
3. **Pré-visualização** — as primeiras 10 linhas aparecem como foram lidas.
4. **Validação e confirmação** — cada linha é convertida e validada; os erros são
   listados por **linha e coluna**. O botão "Confirmar e gravar" só habilita com
   validação limpa, e `PlanilhaImportService.gravar()` recusa qualquer
   `ResultadoValidacao` inválido. **Nada é gravado silenciosamente.**

Modos de importação:

- **Adicionar novos registros** — cada linha vira um `RegistroPlanilha` novo.
- **Atualizar registros existentes** — exige escolher a *coluna-chave*; linhas
  cuja chave já existe atualizam o registro em vez de duplicá-lo.

A gravação é atômica (`@transaction.atomic`) e produz uma entrada em
`core.AuditLog` com a ação `importacao_concluida`.

### 2.5 Formatos suportados

| Formato | Situação |
| --- | --- |
| XLSX / XLSM | Suportado (`openpyxl`, já em `requirements.txt`) |
| CSV | Suportado (detecta `,`, `;` ou tabulação, e os encodings UTF-8/UTF-8-BOM/Latin-1) |
| XLS | Lido **se** `xlrd` estiver instalado no servidor |
| ODS | Lido **se** `odfpy` estiver instalado no servidor |

`formatos_suportados()` informa o que está habilitado, e a tela de importação
mostra esses selos. Quando a biblioteca falta, a mensagem orienta a converter o
arquivo em vez de falhar de forma obscura. Para habilitar os dois últimos, basta
instalar as bibliotecas — nenhuma alteração de código é necessária:

```bash
pip install xlrd odfpy
```

### 2.6 Exportação

- `ava:planilha_exportar` com formato `xlsx` ou `csv`, respeitando o escopo do
  usuário.
- `ava:planilha_modelo_em_branco` gera um XLSX apenas com os cabeçalhos
  configurados, pronto para o professor preencher e reimportar.

### 2.7 Permissões

- Criar e editar modelos: **Admin do cliente** e **Super admin**.
- Ver dados, importar e exportar: também professores, coordenação e direção,
  desde que o modelo esteja `ativo`, com `permite_professor=True` e o escopo de
  escola seja compatível (modelo sem escola vale para todo o município).
- Modelos de outro município retornam HTTP 404.

---

## 3. Como criar um modelo de planilha (passo a passo)

1. Entre no AVA como **Admin do cliente** e acesse **Planilhas** no menu.
2. Clique em **Novo modelo**.
3. Preencha:
   - **Nome** — ex.: `Frequência mensal`.
   - **Identificador** — pode ficar em branco (gerado a partir do nome).
   - **Versão** — incremente ao mudar a estrutura, preservando o histórico.
   - **Escola / Curso vinculados** — deixe vazio para valer em todo o município.
   - **Ativo** e **Professores podem preencher**.
4. Na tabela **Colunas configuráveis**, preencha uma linha por coluna:
   título, tipo, ordem, obrigatoriedade, visibilidade e, quando fizer sentido,
   opções de seleção (uma por linha) e regras de validação em JSON.
5. **Salvar modelo**. Use **Baixar planilha modelo** para gerar o XLSX com os
   cabeçalhos e distribuir às escolas.
6. Em **Ver dados → Importar dados**, envie a planilha preenchida e siga as
   quatro etapas.

### 3.1 Exemplo de configuração

Modelo `Frequência mensal`, escopo: todo o município, professores podem preencher.

| Ordem | Título | Chave | Tipo | Obrigatório | Opções | Validações |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Turma | `turma` | Texto | sim | — | `{"max_length": 20}` |
| 2 | Data | `data` | Data | sim | — | `{"data_min": "2026-01-01"}` |
| 3 | Presentes | `presentes` | Número inteiro | sim | — | `{"min": 0, "max": 40}` |
| 4 | Turno | `turno` | Seleção | não | `Manhã`, `Tarde` | — |
| 5 | Professor | `professor` | Professor | não | — | — |
| 6 | Houve reposição | `reposicao` | Sim/Não | não | — | — |

Planilha correspondente:

| Turma | Data | Presentes | Turno | Professor | Houve reposição |
| --- | --- | --- | --- | --- | --- |
| 3A | 01/03/2026 | 20 | Manhã | carla@escola.gov.br | Não |
| 3B | 02/03/2026 | 18 | Tarde | Carla Nunes | Sim |

Para atualizações posteriores, reimporte no modo **Atualizar registros
existentes** usando `Turma` como coluna-chave.

---

## 4. Auditoria

`ava/services/audit_service.py` grava em `core.AuditLog`, com `entidade` no
formato `ava.<Modelo>`:

| Ação | Quando |
| --- | --- |
| `criado`, `atualizado` | Diário salvo |
| `enviado`, `revisado`, `bloqueado`, `reaberto` | Transições de status |
| `frequencia_atualizada` | Inclusão/remoção de participante |
| `midia_adicionada`, `midia_removida` | Anexos |
| `exportado` | Exportações de diário e de planilha |
| `modelo_criado`, `modelo_atualizado`, `modelo_ativado`, `modelo_desativado` | Modelos de planilha |
| `importacao_concluida`, `importacao_cancelada` | Importações |

A auditoria é *best-effort*: uma falha ao gravar o log nunca derruba a operação
de negócio, que já está persistida.

---

## 5. Testes

```bash
pytest ava/tests/test_diario_bordo.py
pytest ava/tests/test_planilha_configuravel.py
```

Cobrem: criação nos quatro tipos de origem, edição de rascunho, envio, bloqueio
após revisão, isolamento por escola e por município, upload de múltiplas fotos,
rejeição de extensão/MIME/tamanho, frequência quantitativa e nominal, criação de
modelo de planilha e colunas pela interface, importação válida, importação com
erro (que não grava nada), modo de atualização, exportação XLSX/CSV, tentativa
de acesso indevido e registro de auditoria.
