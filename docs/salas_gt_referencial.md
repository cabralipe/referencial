# Salas dos Grupos de Trabalho do Referencial

Área do AVA que organiza o trabalho dos GTs responsáveis pelos objetivos do
Referencial: uma sala por objetivo, por ciclo, concentrando inscrição,
capacidade, diagnóstico, quadro do objetivo (metas e estratégias), reuniões,
frequência, ata e documentos DOCX (individuais e consolidado).

Rotas: `/ava/gts/` (lista), `/ava/gts/<id>/` (sala), `/ava/gts/admin/`
(administração do Referencial), `/ava/gts/acompanhamento/` (visão institucional).

## O que foi reaproveitado

| Necessidade | O que já existia e foi usado |
| --- | --- |
| Grupos de trabalho e membros | `curriculum.GT` e `GT.membros` — nenhum cadastro paralelo de GT ou de pessoas |
| Usuários, papéis e escopo por município | `core.Usuario` (`role`), `TenantModel`, soft delete, `get_ava_clientes_queryset()` |
| Trilha de auditoria | `core.AuditLog` via `ava.services.AVAAuditService` |
| Exportação | `exports.ExportJob` como registro de cada documento gerado e `exports/services/docx.py` (python-docx) |
| Armazenamento protegido | `storages["private"]` (`ava.storage.private_ava_storage`) e o padrão de download por view do Diário de Bordo |
| Notificações | o inbox in-app `notifications.Notificacao` (lido por `GET /api/v1/notificacoes`), respeitando `ff.notifications.enabled` — gravado direto, sem depender de Redis/SMTP |
| Comentários e pedidos de ajuste | `comments.Comentario` (genérico por `alvo_tipo`/`alvo_id`/`anchor_json`), com o novo alvo `trabalho_gt` — respeita `ff.comments.enabled` |
| Identidade visual e UX | `ava/templates/ava/base.html`, Bootstrap 5, padrões de lista/filtro/formulário do Diário de Bordo |

Não foi criada nenhuma app nova: os modelos ficam no app `ava`
(`ava/models/gt_sala.py`), com chaves estrangeiras para `curriculum.GT` e
`core.Usuario`.

## Modelo de dados

```
CicloReferencial ─┬─< SalaGT >─── ObjetivoReferencial
                  │        │
                  │        ├─< InscricaoSalaGT >── core.Usuario
                  │        ├─── TrabalhoGT ─┬─< MetaGT
                  │        │                ├─< EstrategiaGT >── MetaGT (M2M)
                  │        │                └─< VersaoTrabalhoGT
                  │        └─< ReuniaoGT ─┬─< PresencaReuniaoGT >── core.Usuario
                  │                       └─── AtaReuniaoGT ─── ModeloAtaGT
                  └─ (configurações de inscrição e de aprovação)
                                 curriculum.GT ──┘ (reaproveitado)
```

- **`CicloReferencial`** — edição/ano do trabalho. Guarda a janela de inscrição,
  `confirmacao_automatica`, `max_salas_por_participante`, `permite_lista_espera`
  e os mínimos para aprovação (`min_metas_para_aprovacao`,
  `min_estrategias_para_aprovacao`, `exige_ata_para_aprovacao`).
- **`ObjetivoReferencial`** — objetivo oficial cadastrado/importado. `codigo` é o
  identificador estável; `ordem` define a sequência da consolidação. Nenhum
  texto de objetivo está fixado em código.
- **`SalaGT`** — liga ciclo + objetivo + GT. `capacidade`, `vagas_ocupadas`
  (mantido pelo sistema), janela própria opcional, `permite_lista_espera`,
  `participantes_editam_conteudo` e `situacao`
  (planejamento/em andamento/concluída/arquivada). Restrições de unicidade:
  um objetivo por ciclo e um GT por ciclo.
- **`InscricaoSalaGT`** — vínculo pessoa↔sala com `estado`
  (solicitada/confirmada/lista de espera/recusada/cancelada), `papel`
  (coordenação/relatoria/participante/leitor), `ordem_espera`, datas e
  responsável pela decisão. Unicidade por (cliente, sala, usuário) — pedir
  novamente reabre o mesmo vínculo em vez de duplicar.
- **`TrabalhoGT`** — diagnóstico e quadro do objetivo, com `estado`
  (rascunho → em revisão → ajustes solicitados → aprovado → publicado/arquivado),
  `version` e `etag`.
- **`MetaGT` / `EstrategiaGT`** — metas com indicador/prazo e estratégias com
  responsável, prazo, recursos, indicador e vínculo (M2M) com metas.
- **`VersaoTrabalhoGT`** — retrato imutável (JSON) do conteúdo em cada transição;
  é o que mantém a versão aprovada recuperável.
- **`ReuniaoGT` / `PresencaReuniaoGT`** — reunião (data/hora, pauta, modalidade,
  local/link, responsável pelo registro) e presença por membro do GT, com
  `registrado_por`/`alterado_por` e validação/fechamento pela coordenação.
- **`ModeloAtaGT` / `AtaReuniaoGT`** — modelo institucional versionado e a
  minuta/ata da reunião, que guarda o retrato do modelo (`estrutura_json`) para
  que publicar nova versão do modelo não altere atas já geradas.

## Perfis e capacidades

A autorização é resolvida em `ava/services/gt_access.py` (`acesso_a_sala`) e
exigida nos serviços e nas views antes de qualquer efeito. Os templates apenas
refletem as capacidades — esconder botão não é controle de acesso.

| Capacidade | Quem tem |
| --- | --- |
| Configurar ciclo, objetivos, salas, capacidade, períodos; reabrir conteúdo; definir/retirar coordenação; arquivar | `super_admin`, `admin_cliente` |
| Ver todas as salas (inclusive rascunhos), acompanhar e exportar | acima + `articulador` (Redator) e `revisor` |
| Gerir inscrições/papéis, validar e reabrir frequência, aprovar/publicar conteúdo, validar ata | coordenação **daquela sala** + administração |
| Editar diagnóstico, metas, estratégias e minuta; submeter para revisão | relatoria/coordenação **daquela sala** (e participantes, quando `participantes_editam_conteudo`) |
| Consultar a sala, materiais e a própria frequência | participantes confirmados daquela sala |
| Consultar apenas versões aprovadas/publicadas | qualquer usuário do município, pela lista de salas |

Por padrão nega: sem vínculo ativo e sem papel de visão global, o usuário vê a
vitrine das salas (objetivo, ocupação, situação, coordenação) e o conteúdo
publicado — nunca rascunhos, frequência de terceiros ou documentos restritos.

## Inscrição e capacidade

- O participante solicita inscrição na lista de salas. Com
  `confirmacao_automatica` ligada, a vaga é reservada na hora; desligada, o
  pedido fica `solicitada` até a coordenação aprovar.
- **A vaga é reservada por `UPDATE ... WHERE vagas_ocupadas < capacidade`**
  (`SalaGTService._reservar_vaga`). Duas requisições simultâneas disputam o mesmo
  UPDATE e apenas uma ocupa a última vaga, em PostgreSQL e em SQLite — por isso
  não se usa `SELECT ... FOR UPDATE`, não suportado no SQLite de
  desenvolvimento/teste.
- Sem vaga, a inscrição vai para a lista de espera com posição; a promoção é
  **sempre manual** (`promover_lista_espera`) e só ocorre quando há vaga livre.
  Nada é prometido antes da confirmação.
- `max_salas_por_participante` limita a participação em vários GTs no ciclo
  (vazio = sem limite).
- Confirmar/cancelar mantém `GT.membros` alinhado: a sala reflete no cadastro do
  GT quem está confirmado, sem criar um segundo cadastro de membros.
- Cada mudança de estado gera uma notificação no inbox in-app quando a flag
  `ff.notifications.enabled` está ativa. A gravação é direta no modelo
  `notifications.Notificacao`: o fluxo de inscrição **não** publica em Channels
  nem enfileira e-mail no Celery, para não ficar preso esperando Redis/SMTP —
  nenhum serviço externo é obrigatório.

## Fluxo do conteúdo

`rascunho → em revisão → ajustes solicitados → aprovado → publicado`
(`arquivado` fica disponível para encerramento).

- Salvamento explícito com mensagem de sucesso/erro e **detecção de conflito**:
  o formulário envia a `version` carregada e uma edição concorrente recebe aviso
  para recarregar em vez de sobrescrever silenciosamente.
- Cada transição grava uma `VersaoTrabalhoGT` com o conteúdo completo; conteúdo
  aprovado fica congelado e só volta a ser editável por reabertura
  **da administração, com justificativa**, registrada em auditoria.
- A aprovação exige: objetivo vinculado, diagnóstico preenchido ou marcado
  explicitamente como não aplicável, os mínimos de metas/estratégias do ciclo e —
  se o ciclo exigir — ata validada. Os mínimos são configuráveis (0 desliga).
- O objetivo oficial nunca é sobrescrito: a proposta do GT fica em
  `TrabalhoGT.objetivo_proposto`, ao lado da redação oficial.
- **Comentários por campo** reaproveitam `comments.Comentario` com
  `alvo_tipo="trabalho_gt"`, `alvo_id` do trabalho e `anchor_json` guardando o
  campo comentado, a versão e o estado do conteúdo naquele momento — assim o
  pedido de ajuste fica ligado ao GT, à versão e ao trecho. Comenta quem tem
  vínculo ativo na sala (ou visão institucional); resolve a coordenação, a
  administração ou quem escreveu. A seção respeita `ff.comments.enabled` e a
  exibição remove marcação do texto (`striptags|linebreaksbr`).

## Reuniões, frequência e ata

- A lista de presença vem dos membros confirmados do GT, todos como **ausentes**,
  até alguém responsável registrar o que ocorreu — presença nunca é inferida de
  login ou de acesso à sala.
- Coordenação e relatoria lançam; **somente coordenação/administração valida**.
  Depois de validada, a frequência só muda por reabertura com justificativa, e
  tanto a reabertura quanto as correções ficam na auditoria (`frequencia_reaberta`,
  `frequencia_lancada`).
- O participante consulta apenas a própria frequência.
- A ata nasce do modelo institucional vigente, pré-preenchida só com dados
  seguros já existentes (GT, objetivo, ciclo, reunião, participantes, data). A
  minuta é claramente distinguida da ata validada, no sistema e no DOCX. Não há
  simulação de assinatura digital: o documento gera linhas de assinatura/ciência
  manual.

## Documentos DOCX

Gerados por `ava/services/gt_documento_service.py` com python-docx — arquivo
DOCX real, com títulos, tabelas, cabeçalho/rodapé da identidade visual do
cliente (`ClienteTema`), numeração de páginas, idioma pt-BR e acentuação
preservada.

1. **Documento do objetivo do GT** — objetivo oficial + proposta do GT,
   diagnóstico, metas e estratégias (em tabelas).
2. **Ata da reunião** — ficha da reunião, participantes com presença/ausência
   (sem justificativas pessoais) e as seções do modelo.
3. **Consolidação institucional** — todos os objetivos do ciclo na ordem oficial,
   com sumário (campo TOC: atualize no Word com F9), quebra de página por
   objetivo e um quadro final de situação. Entram apenas conteúdos aprovados ou
   publicados; os demais aparecem como **“Pendente de consolidação”**, sem
   conteúdo inventado. A exportação parcial existe, mas exige seleção explícita —
   o padrão é a consolidação completa.

Cada geração cria um `ExportJob` (`gt_objetivo`, `gt_ata`, `gt_consolidado`) com
`status=done`, o arquivo vai para o **storage privado** e o download passa por
`/ava/gts/documentos/<job>/arquivo/`, que revalida a autorização a cada acesso
(`url_resultado` fica vazio de propósito — não há URL pública). Os nomes seguem
o padrão `referencial_<ciclo>_obj-<codigo>_<tipo>_v<versao>_<data>.docx`, sem
dados pessoais.

## Administração dos 19 GTs

1. **Cadastrar/importar os objetivos** em `/ava/gts/admin/objetivos/`: CSV
   (`codigo;titulo;texto;ordem`) ou JSON, colado na tela ou por arquivo. Também
   pelo terminal:

   ```bash
   python manage.py importar_objetivos_referencial --cliente <id|slug> objetivos.csv
   python manage.py importar_objetivos_referencial --cliente <id|slug> objetivos.json --desativar-ausentes --dry-run
   ```

   O `codigo` é a chave estável: reimportar atualiza título/texto/ordem sem
   duplicar. `--desativar-ausentes` apenas desativa (nada é apagado).
2. **Criar o ciclo** em `/ava/gts/admin/ciclos/novo/` com período, janela de
   inscrição, regras de inscrição e mínimos de aprovação.
3. **Gerar as salas** no painel: cria uma sala por objetivo ativo. Com “criar o
   GT quando ainda não existir”, os GTs ausentes são criados no cadastro do
   Referencial (`curriculum.GT`, nome `GT <codigo> - <titulo>`, etapa = nome do
   ciclo); sem a opção, os objetivos sem GT ficam pendentes para vínculo manual.
   Objetivos que já têm sala no ciclo são ignorados — nada é duplicado.
4. **Definir coordenação** por sala em *Inscrições* (apenas a administração
   concede/retira coordenação; a coordenação distribui relatoria e participação).
5. **Publicar o modelo de ata** em `/ava/gts/admin/modelo-ata/` (opcional: sem
   modelo, as minutas usam as seções padrão do sistema).
6. **Consolidar** no painel do ciclo, quando os GTs estiverem aprovados.

## Tutorial guiado (aba do administrador)

`/ava/gts/admin/tutorial/` — aba **Tutorial guiado**, visível no menu do AVA para
`admin_cliente` e `super_admin` e destacada no painel de administração e na lista
de salas.

A tela traz um roteiro de **dez passos na ordem correta**; cada passo mostra:

- o **objetivo** do passo e **quem faz** (administração, coordenação ou relatoria);
- o **como fazer**, em instruções curtas e numeradas;
- um **exemplo pronto para copiar** (ex.: a linha de CSV de um objetivo);
- a **situação agora**, calculada com os dados reais do município (quantos
  objetivos ativos, quantas salas, quantas com coordenação, quantas com
  diagnóstico, quantas reuniões, quantas atas validadas, quantos documentos);
- um **botão que leva à página exata** daquele passo, já com município e ciclo no
  contexto — e, quando falta um pré-requisito, o aviso do que concluir antes.

Os passos são: (1) cadastrar/importar os objetivos oficiais; (2) criar o ciclo;
(3) gerar uma sala por objetivo; (4) definir coordenação e relatoria; (5) abrir as
inscrições; (6) preencher diagnóstico e quadro do objetivo; (7) registrar reunião
e lançar/validar frequência; (8) publicar o modelo de ata e validar a primeira
ata; (9) enviar para revisão, aprovar e publicar; (10) gerar os documentos e a
consolidação.

### Exemplo de demonstração

O botão **“Criar exemplo de demonstração”** monta, em um clique, um
`Ciclo de demonstração (exemplo)` com dois objetivos de código `DEMO-01`/`DEMO-02`
(ordem 901/902, para não se misturarem à ordem oficial), as salas
correspondentes, o próprio administrador como coordenação e uma reunião com a
lista de presença pronta. Serve para percorrer o fluxo inteiro — diagnóstico,
metas, estratégias, frequência, ata e DOCX — sem encostar nos dados oficiais.
Clicar duas vezes não duplica nada, e **“Remover o exemplo”** retira (soft
delete) ciclo, salas, inscrições, reuniões, atas e os objetivos `DEMO-`,
preservando todo o cadastro oficial. As duas ações ficam na trilha de auditoria
(`exemplo_tutorial_criado` / `exemplo_tutorial_removido`).

## Testes

`ava/tests/test_gt_salas.py` cobre comportamento, não implementação:
autorização por papel/GT/operação (inclusive POST direto na API e download de
arquivo), limite de vagas com reserva atômica, lista de espera e prevenção de
duplicidade, limite de GTs por participante, lançamento/validação/correção
auditada de frequência, transições de fluxo e proteção da versão aprovada,
edição concorrente, modelo de ata versionado, DOCX válido com acentuação e
seções obrigatórias, consolidação com todos os objetivos na ordem oficial e
isolamento entre ciclos e municípios.

`ava/tests/test_gt_comentarios.py` cobre os comentários por campo (âncora de
campo/versão, quem comenta, quem resolve, flag desligada e isolamento entre GTs).

`ava/tests/test_gt_tutorial.py` cobre o roteiro do tutorial (estado calculado,
links dos passos, pré-requisitos) e o exemplo de demonstração (criação
idempotente, remoção completa e restrição ao perfil administrativo).

```bash
python -m pytest ava/tests/test_gt_salas.py ava/tests/test_gt_tutorial.py ava/tests/test_gt_comentarios.py
```
