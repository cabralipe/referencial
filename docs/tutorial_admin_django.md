# Tutorial do Painel Administrativo (Django Admin)

Acesse o painel em **`/admin/`** com uma conta de `SUPER_ADMIN` ou `ADMIN_CLIENTE`.

---

## Sumário

1. [Níveis de acesso](#1-níveis-de-acesso)
2. [Gestão de Clientes e Configurações](#2-gestão-de-clientes-e-configurações)
3. [Usuários e Tipos de Cadastro](#3-usuários-e-tipos-de-cadastro)
4. [AVA — Ambiente Virtual de Aprendizagem](#4-ava--ambiente-virtual-de-aprendizagem)
5. [Currículo — GTs, Tarefas e Perguntas](#5-currículo--gts-tarefas-e-perguntas)
6. [Escolas e PPP](#6-escolas-e-ppp)
7. [Consultas Públicas](#7-consultas-públicas)
8. [Notificações e Mensagens](#8-notificações-e-mensagens)
9. [Exportações e Revisões](#9-exportações-e-revisões)
10. [Perguntas Frequentes](#10-perguntas-frequentes)

---

## 1. Níveis de acesso

| Role | O que pode fazer no admin |
|------|--------------------------|
| **SUPER_ADMIN** | Acessa todos os dados de todos os clientes. Único que pode copiar estruturas de curso entre municípios. |
| **ADMIN_CLIENTE** | Acessa apenas os dados do seu município (cliente). Pode gerenciar usuários, AVA e currículo do seu cliente. |
| Demais roles | Não têm acesso ao `/admin/` por padrão. |

> O sistema filtra automaticamente todos os registros pelo `cliente_id` do usuário logado. Um `ADMIN_CLIENTE` nunca verá dados de outro município.

---

## 2. Gestão de Clientes e Configurações

### 2.1 Clientes (`Core > Clientes`)

Cada **Cliente** representa um município ou organização independente.

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome do município/organização |
| `slug` | Identificador único em URL (ex: `sao-paulo`). Gerado automaticamente a partir do nome. |
| `ativo` | Desativar impede login de todos os usuários desse cliente. |

### 2.2 Configurações do Cliente (`Core > Configurações de Clientes`)

Pares chave-valor que personalizam o comportamento da plataforma para cada cliente.

**Chaves para personalizar o formulário de Criar Conta:**

| Chave | Valor esperado | Efeito |
|-------|---------------|--------|
| `cadastro_titulo` | texto livre | Título da página de cadastro |
| `cadastro_subtitulo` | texto livre | Subtítulo da página de cadastro |
| `cadastro_label_nome` | texto livre | Label do campo "Nome Completo" |
| `cadastro_placeholder_nome` | texto livre | Placeholder do campo Nome |
| `cadastro_label_email` | texto livre | Label do campo "E-mail" |
| `cadastro_placeholder_email` | texto livre | Placeholder do campo E-mail |
| `cadastro_label_senha` | texto livre | Label do campo "Senha" |
| `cadastro_label_confirmar_senha` | texto livre | Label do campo "Confirmar Senha" |
| `cadastro_label_municipio` | texto livre | Label do campo "Município" |
| `cadastro_placeholder_municipio` | texto livre | Placeholder do campo Município |
| `cadastro_label_escola` | texto livre | Label do campo "Escola" |
| `cadastro_placeholder_escola` | texto livre | Placeholder do campo Escola |
| `cadastro_label_tipo_usuario` | texto livre | Label do seletor "Eu sou um(a)" |

**Como adicionar uma configuração:**
1. Acesse `Core > Configurações de Clientes > Adicionar`
2. Selecione o **Cliente**
3. Preencha a **Chave** (ex: `cadastro_titulo`)
4. Preencha o **Valor** (ex: `Cadastre-se na Plataforma`)
5. Salve — a mudança aparece imediatamente no formulário público.

### 2.3 Tema do Cliente (`Core > Temas de Clientes`)

Personaliza a aparência da plataforma para cada cliente.

| Campo | Descrição |
|-------|-----------|
| `logo_url` | URL da logo exibida no topo |
| `cor_primaria` | Cor principal em hex (ex: `#004aad`) |
| `cor_secundaria` | Cor de destaque em hex (ex: `#00b4d8`) |
| `cabecalho_html` | HTML personalizado para o cabeçalho |
| `rodape_html` | HTML personalizado para o rodapé |
| `meb_avatar_url` | Avatar do assistente IA (MEB) |

### 2.4 Feature Flags (`Core > Feature Flags de Clientes`)

Ativam ou desativam funcionalidades específicas por cliente.

| Campo | Descrição |
|-------|-----------|
| `flag` | Nome da funcionalidade |
| `ativo` | Liga/desliga a funcionalidade para esse cliente |

---

## 3. Usuários e Tipos de Cadastro

### 3.1 Usuários (`Core > Usuários`)

**Criar um usuário:**
1. Acesse `Core > Usuários > Adicionar`
2. Preencha `email`, `nome`, `senha`
3. Selecione o **Cliente** (município)
4. Selecione a **Escola** (quando aplicável)
5. Selecione o **Tipo de Cadastro** — isso define automaticamente a `role` e o `seguimento`
6. Salve

**Campos importantes:**

| Campo | Descrição |
|-------|-----------|
| `email` | Login do usuário (único no sistema) |
| `role` | Permissão do usuário. Definida automaticamente pelo Tipo de Cadastro. |
| `seguimento` | Segmento de ensino (Anos Iniciais, Anos Finais, EJA etc.) |
| `tipo_cadastro` | Vínculo com o tipo de cadastro público |
| `escola` | Escola à qual o usuário pertence |
| `is_active` | Desativar bloqueia o login sem deletar o usuário |

**Roles disponíveis:**

| Role | Perfil |
|------|--------|
| `super_admin` | Acesso total ao sistema |
| `admin_cliente` | Administrador do município |
| `articulador` | Articulador curricular |
| `revisor` | Revisor de documentos |
| `diretor` | Diretor de escola |
| `coordenador_pedagogico` | Coordenador pedagógico |
| `professor` | Professor |
| `membro_gt` | Membro de Grupo de Trabalho |
| `leitor` | Apenas leitura |

**Ação em massa — Enviar mensagem de chat:**
1. Selecione um ou mais usuários na lista
2. No menu "Ação", escolha **"Enviar mensagem de chat"**
3. Digite a mensagem — ela chegará no chat interno de cada usuário selecionado.

### 3.2 Tipos de Cadastro (`Core > Tipos de Usuário para Cadastro`)

Definem as opções que aparecem no formulário público de "Criar Conta".

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome exibido no formulário (ex: "Professor") |
| `cliente` | Município ao qual este tipo pertence |
| `role_interno` | Role que o usuário receberá ao se cadastrar |
| `seguimento` | Seguimento padrão para esse tipo |
| `acesso_ppp` | Se marcado, libera acesso ao módulo PPP |
| `exibir_no_cadastro` | Se desmarcado, o tipo fica oculto no formulário público |
| `ativo` | Desativar oculta o tipo do formulário |
| `ordem_exibicao` | Ordem dos cards no formulário de cadastro |

---

## 4. AVA — Ambiente Virtual de Aprendizagem

### 4.1 Estrutura hierárquica

```
Trilha Formativa
└── Curso
    └── Módulo
        └── Aula
            ├── Conteúdo (vídeo, texto, PDF...)
            └── Atividade (Quiz, Tarefa, Envio de Arquivo...)
```

### 4.2 Trilhas Formativas (`Ava > Trilhas Formativas`)

Agrupam cursos em uma sequência de aprendizagem.

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome da trilha |
| `is_active` | Liga/desliga a trilha para os alunos |
| `ordem_exibicao` | Ordem de exibição na plataforma |

### 4.3 Cursos (`Ava > Cursos`)

**Criar um curso:**
1. Acesse `Ava > Cursos > Adicionar`
2. Preencha `titulo` e `slug` (o slug é gerado automaticamente)
3. Selecione o `cliente` (município) — obrigatório
4. Defina o `status`: `rascunho`, `publicado` ou `arquivado`
5. Marque `is_aberto` se qualquer pessoa pode se matricular sem convite
6. Salve

**Copiar estrutura de curso entre municípios** *(apenas SUPER_ADMIN)*:
1. Acesse `Ava > Cursos`
2. Clique no botão **"Copiar Estrutura de Curso"** no topo da lista
3. Selecione o curso de origem e o cliente de destino
4. Confirme — módulos, aulas e atividades são duplicados para o novo cliente.

### 4.4 Módulos (`Ava > Módulos de Curso`)

| Campo | Descrição |
|-------|-----------|
| `titulo` | Nome do módulo |
| `ordem` | Posição no curso |
| `is_active` | Visível para os alunos? |
| `data_liberacao_programada` | Data/hora para liberar automaticamente |
| `pre_requisito_modulo` | Módulo que precisa ser concluído antes |

### 4.5 Aulas (`Ava > Aulas`)

Dentro de cada aula é possível adicionar (via inline):
- **Conteúdos**: vídeos, textos, PDFs, links externos
- **Atividades**: quizzes, tarefas, envio de arquivo, fóruns

### 4.6 Atividades (`Ava > Atividades`)

**Tipos de atividade:**

| Tipo | Descrição |
|------|-----------|
| `quiz` | Quiz com alternativas (correção automática opcional) |
| `tarefa` | Resposta discursiva em texto |
| `envio_arquivo` | Aluno envia um ou mais arquivos |
| `questionario` | Pesquisa simples (sem nota) |
| `reflexao` | Reflexão guiada |
| `forum` | Fórum interativo com anexos |

**Campos comuns:**

| Campo | Descrição |
|-------|-----------|
| `nota_maxima` | Valor máximo da atividade (padrão: 100) |
| `peso` | Peso na composição da média |
| `is_obrigatoria` | Se obrigatória para concluir a aula |
| `prazo_envio` | Prazo fatal (opcional) |
| `tentativas_permitidas` | Máximo de tentativas (0 = ilimitadas) |
| `correcao_automatica` | Para quizzes e questionários |
| `criterio_aprovacao` | Nota mínima para aprovação |

**Atividade de Envio de Arquivo — múltiplos uploads:**
- O aluno pode enviar **vários arquivos** de uma vez — o input já tem `multiple` habilitado.
- Cada arquivo é salvo separadamente em `AtividadeTentativaArquivo`.
- Os arquivos ficam acessíveis em `Ava > Arquivos de Tentativas`.

### 4.7 Questões de Quiz (`Ava > Questões de Quiz`)

1. Crie a atividade do tipo `quiz` primeiro
2. Acesse `Ava > Questões de Quiz > Adicionar`
3. Selecione a atividade (apenas atividades do tipo quiz/questionário aparecem)
4. Adicione as alternativas via inline (marque a correta com `is_correta = Sim`)
5. Preencha feedbacks opcionais para acerto/erro

### 4.8 Matrículas (`Ava > Matrículas em Cursos`)

| Campo | Descrição |
|-------|-----------|
| `aluno` | Usuário matriculado |
| `curso` | Curso |
| `status` | `ativa`, `concluída`, `cancelada` |
| `progresso_percentual` | Calculado automaticamente |

### 4.9 Certificados (`Ava > Certificados`)

Gerados automaticamente ao concluir um curso. O campo `codigo_validacao` é único e pode ser consultado publicamente.

**Configurar layout do certificado:** `Ava > Configurações de Certificado`

---

## 5. Currículo — GTs, Tarefas e Perguntas

### 5.1 Grupos de Trabalho — GTs (`Curriculum > Grupos de Trabalho`)

Os GTs são as equipes que trabalham juntas na construção curricular.

**Criar um GT:**
1. Acesse `Curriculum > Grupos de Trabalho > Adicionar`
2. Preencha o `nome`
3. Selecione o `cliente`
4. Selecione a `etapa` (série/ano)
5. Em **Membros**, adicione os usuários que farão parte do grupo
6. Salve

**Enviar mensagem para um GT:**
1. Selecione um ou mais GTs na lista
2. No menu "Ação", escolha **"Enviar mensagem de chat"**
3. A mensagem chegará a todos os membros do GT.

### 5.2 Áreas (`Curriculum > Áreas`)

Agrupam os GTs por área do conhecimento (ex: Linguagens, Matemática).

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome da área |
| `gts` | GTs vinculados a esta área |
| `descricao` | Texto rico com descrição (suporta HTML) |

### 5.3 Tarefas (`Curriculum > Tarefas`)

Estruturam o trabalho do GT em etapas.

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome da tarefa |
| `ordem` | Sequência de execução |
| `tipo` | Tipo da tarefa |
| `status` | `rascunho`, `ativo`, `arquivado` |

> A combinação `(cliente, ordem, tipo)` deve ser única — o sistema valida e avisa se houver conflito.

### 5.4 Perguntas (`Curriculum > Perguntas`)

Perguntas dentro de uma tarefa que os membros do GT precisam responder.

| Campo | Descrição |
|-------|-----------|
| `tarefa` | Tarefa pai |
| `ordem` | Posição dentro da tarefa |
| `obrigatoria` | Resposta obrigatória para avançar? |
| `permite_upload` | Permite anexar arquivos na resposta? |
| `gts` | GTs específicos que veem esta pergunta (vazio = todos) |

### 5.5 Respostas (`Curriculum > Respostas`)

Respostas dos GTs às perguntas. São versionadas — cada edição cria uma nova versão.

| Campo | Descrição |
|-------|-----------|
| `gt` | GT que respondeu |
| `pergunta` | Pergunta respondida |
| `version` | Versão (somente leitura — incrementada automaticamente) |
| `autor` | Último usuário que editou |

---

## 6. Escolas e PPP

### 6.1 Escolas (`Curriculum > Escolas`)

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome da escola |
| `cliente` | Município ao qual pertence |

> As escolas são exibidas no formulário público de cadastro, filtradas pelo município selecionado.

### 6.2 PPP — Projeto Político-Pedagógico (`Curriculum > PPPs`)

Cada escola tem um PPP vinculado (relação 1:1).

| Campo | Descrição |
|-------|-----------|
| `escola` | Escola dona do PPP |
| `status` | `em_elaboracao`, `em_revisao`, `aprovado` |
| `ultima_edicao_por` | Último editor (somente leitura) |
| `concluido_por` | Quem aprovou (somente leitura) |

---

## 7. Consultas Públicas

### 7.1 Consultas (`Consultas > Consultas Públicas`)

Formulários abertos à população para coleta de opiniões.

| Campo | Descrição |
|-------|-----------|
| `titulo` | Título da consulta |
| `cliente` | Município |
| `data_publicacao` | Data/hora de abertura |
| `data_fechamento` | Data/hora de encerramento |
| `ativa` | Ligar/desligar manualmente |
| `token_acesso` | Token único gerado automaticamente para o link público |

### 7.2 Manifestações (`Consultas > Manifestações Públicas`)

Respostas recebidas das consultas. Somente leitura no admin.

| Campo visível | Descrição |
|--------------|-----------|
| `nome_completo` | Nome do respondente |
| `cidade` / `estado` | Localização |
| `ip_address` | IP de origem (para moderação) |
| `created_at` | Data/hora do envio |

---

## 8. Notificações e Mensagens

### 8.1 Notificações (`Notifications > Notificações`)

Notificações geradas pelo sistema para os usuários.

| Campo | Descrição |
|-------|-----------|
| `usuario` | Destinatário |
| `tipo` | Tipo da notificação |
| `lida` | Se o usuário já visualizou |
| `payload_json` | Dados adicionais da notificação |

### 8.2 Assistente MEB (`Meb > Threads`, `Meb > Mensagens`)

Histórico de conversas com o assistente IA.

- **Threads**: cada conversa de um usuário com o MEB
- **Mensagens**: mensagens individuais (origem `usuario` ou `assistente`)

---

## 9. Exportações e Revisões

### 9.1 Jobs de Exportação (`Exports > Jobs de Exportação`)

Geração assíncrona de documentos (PDF, DOCX etc.).

| Campo | Descrição |
|-------|-----------|
| `alvo_tipo` | Tipo do objeto exportado (GT, Curso etc.) |
| `alvo_id` | ID do objeto |
| `formato` | `pdf`, `docx` etc. |
| `status` | `pendente`, `processando`, `concluído`, `erro` |
| `finished_at` | Quando terminou |

### 9.2 Revisões (`Reviews > Revisões`)

Fluxo de aprovação de documentos.

| Campo | Descrição |
|-------|-----------|
| `alvo_tipo` | Tipo do documento em revisão |
| `status` | `solicitada`, `em_andamento`, `aprovada`, `rejeitada` |
| `revisor` | Usuário revisor |
| `solicitante` | Quem pediu a revisão |
| `parecer_html` | Parecer do revisor |

---

## 10. Perguntas Frequentes

**P: Como desativar um usuário sem deletá-lo?**
> Edite o usuário e desmarque o campo `is_active`. Ele não conseguirá fazer login, mas todos os seus dados são preservados.

**P: Como personalizar os textos do formulário de cadastro de um município?**
> Acesse `Core > Configurações de Clientes`, adicione entradas com prefixo `cadastro_` para o cliente desejado. Veja a tabela completa na [seção 2.2](#22-configurações-do-cliente-core--configurações-de-clientes).

**P: Como permitir que alunos enviem vários arquivos em uma atividade?**
> Crie (ou edite) a atividade com o tipo **"Envio de Arquivo"**. O formulário já permite múltiplos arquivos automaticamente — nenhuma configuração extra é necessária.

**P: Como copiar um curso de um município para outro?**
> Somente `SUPER_ADMIN`. Na lista de cursos (`Ava > Cursos`), clique em **"Copiar Estrutura de Curso"**, selecione o curso de origem e o cliente de destino.

**P: Como ocultar um tipo de usuário do formulário de cadastro público?**
> Edite o tipo em `Core > Tipos de Usuário para Cadastro` e desmarque **"Exibir no cadastro"** ou desative o campo `ativo`.

**P: O que acontece ao desativar um Cliente?**
> Todos os usuários daquele cliente ficam impossibilitados de fazer login. Os dados não são excluídos.

**P: Como ver os arquivos enviados por um aluno em uma atividade?**
> Acesse `Ava > Arquivos de Tentativas` e filtre pelo aluno ou atividade. Cada arquivo tem link direto para download.

**P: Como enviar um aviso para todos os membros de um GT?**
> Em `Curriculum > Grupos de Trabalho`, selecione os GTs desejados, escolha a ação **"Enviar mensagem de chat"** e escreva o texto.

---

*Dúvidas ou problemas? Contate o suporte técnico.*
