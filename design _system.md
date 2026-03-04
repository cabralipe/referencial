# IDENTIDADE VISUAL — Plataforma PROLUC

## Stack Técnica

- Tailwind CSS para toda estilização (NUNCA criar arquivos .css separados)
- shadcn/ui como base de componentes, customizados via className
- Todos os valores visuais definidos como TOKENS SEMÂNTICOS no tailwind.config
- NUNCA usar valores hardcoded no código — sempre tokens semânticos
- NUNCA usar cores, radius ou sombras padrão do Tailwind
- A IA que implementa é RESPONSÁVEL por criar SVGs originais e composições visuais únicas baseadas nas descrições abaixo
- A paleta usa UMA cor accent forte + neutros institucionais
- LIGHT MODE é o modo principal e obrigatório

---

## A Alma do App

A Plataforma MEB é um **ambiente de percurso formativo**, não um dashboard.
Cada tela comunica **orientação, clareza e avanço consciente**.
O professor nunca “navega perdido” — ele **segue um caminho visível, guiado e validado**.

> A identidade visual não decora o ensino. Ela **ensina enquanto organiza**.

---

## Referências e Princípios Extraídos

### AVAMEC

- **Estrutura:** Percurso formativo modular, com avanço progressivo
- **Linguagem:** Institucional, neutra, sem excesso de efeitos
- **Princípio:** Formação é jornada, não feed
  → Aplicação: Timeline, progresso e checklist como elementos centrais

### GOV.BR

- **Estrutura:** Hierarquia clara, foco em legibilidade
- **Linguagem:** UI funcional, sem ruído visual
- **Princípio:** Interface deve gerar confiança imediata
  → Aplicação: Paleta neutra, tipografia sólida, contraste claro

### Notion (versão institucional)

- **Estrutura:** Conteúdo como protagonista
- **Linguagem:** Espaço em branco como recurso didático
- **Princípio:** Organização transmite inteligência
  → Aplicação: Layouts arejados, cards com função clara, sem sobreposição

---

## Decisões de Identidade

## ESTRUTURA

### Navegação

**O que:** Topbar fixa + navegação contextual lateral apenas quando necessário
**Por que:** Evita sensação de “sistema pesado” e mantém foco no conteúdo
**Como:** Menus horizontais com hierarquia progressiva
**Nunca:** Sidebar permanente estilo SaaS corporativo

### Organização de Conteúdo

**O que:** Conteúdo apresentado como blocos de avanço (cards, etapas, módulos)
**Por que:** O professor pensa em etapas, não em telas
**Como:** Cards com estados (concluído, em andamento, pendente)
**Nunca:** Listas infinitas ou feeds cronológicos

---

## LINGUAGEM

### Tipografia

**O que:** Sans-serif institucional, com hierarquia clara
**Por que:** Leitura prolongada e acessibilidade
**Como:** Títulos fortes, corpo confortável, textos auxiliares suaves
**Nunca:** Tipografia “tech”, condensada ou futurista

### Geometria

**O que:** Cantos suavemente arredondados, proporções estáveis
**Por que:** Transmite acolhimento sem perder formalidade
**Como:** Radius consistente por tipo de componente
**Nunca:** Pills exageradas ou cantos retos agressivos

### Cor

**O que:** UMA cor primária institucional
**Por que:** Identidade forte e reconhecível
**Como:** Accent aparece em progresso, ações principais, estados ativos
**Nunca:** Cores por disciplina, categoria ou módulo

---

## RIQUEZA VISUAL (OBRIGATÓRIA)

### Textura Ambiente

**O que:** Pattern sutil de linhas verticais e horizontais desalinhadas**Temática:** Referência a **grade curricular, planejamento e organização educacional****Tratamento:**

- Monocromático
- Usa neutro escuro ou accent-primary em **3–5% de opacidade**
- Aparece no fundo de páginas-chave (dashboard, certificação)
  **Nunca:** Gradientes coloridos, blobs ou ruído decorativo

---

## Conceitos Visuais por Componente

### 1. Dashboard de Progresso do Curso

**Representa:** A jornada formativa do professor
**Metáfora visual:** Caminho de aprendizagem com marcos claros
**Cena detalhada:**
Uma linha horizontal contínua atravessa o card.
Ela é segmentada em trechos iguais, cada um com um nó circular.
Os nós concluídos são sólidos; os futuros são apenas contorno.
Um marcador maior indica a posição atual do professor no caminho.
A linha é neutra; o marcador ativo usa a cor accent-primary.
**Viabilidade:** CÓDIGO PURO (SVG + layout)
**Alternativa simplificada:** Timeline vertical com nós conectados

---

### 2. Card de Atividade Recente

**Representa:** Continuidade — “retomar de onde parei”
**Metáfora visual:** Página aberta com marcador de leitura
**Cena detalhada:**
Um retângulo representa uma página.
No topo, uma aba dobrada indica “última posição”.
Uma barra horizontal parcial atravessa a página, mostrando progresso.
A barra usa accent-primary; o restante é neutro.
**Viabilidade:** CÓDIGO PURO
**Alternativa:** Barra de progresso integrada ao card

---

### 3. Checklist de Certificação

**Representa:** Validação e segurança
**Metáfora visual:** Trilha vertical de verificação
**Cena detalhada:**
Uma linha vertical conecta itens circulares.
Itens concluídos têm check sólido.
Itens pendentes são círculos vazios.
O último item (certificado) aparece maior, porém bloqueado.
Quando tudo é concluído, a linha inteira muda sutilmente para accent-primary.
**Viabilidade:** CÓDIGO PURO
**Alternativa:** Lista conectada por linhas finas

---

### 4. Player de Vídeo Orientador

**Representa:** Mediação pedagógica
**Metáfora visual:** Quadro de aula
**Cena detalhada:**
O player é envolvido por uma moldura sutil, lembrando um quadro escolar.
Ícones de play e progresso são grandes e calmos, não chamativos.
A barra de tempo usa accent-primary apenas no trecho assistido.
**Viabilidade:** CÓDIGO PURO
**Alternativa:** Player limpo sem moldura temática

---

### 5. Banco Colaborativo de Planos de Aula

**Representa:** Compartilhamento estruturado de saberes
**Metáfora visual:** Biblioteca organizada
**Cena detalhada:**
Cards lembram capas de pastas alinhadas.
Cada card tem uma “aba superior” indicando componente curricular.
Avaliações aparecem como pequenos selos discretos.
Nada parece rede social — tudo parece arquivo institucional.
**Viabilidade:** CÓDIGO PURO
**Alternativa:** Grid de cards com cabeçalho fixo

---

### 6. Empty States (Sem Conteúdo)

**Representa:** Orientação, não erro
**Metáfora visual:** Espaço em preparação
**Cena detalhada:**
Linhas tracejadas formando contornos de cards ainda vazios.
Texto explica o próximo passo de forma didática.
Nenhum ícone triste, nenhum mascote.
**Viabilidade:** CÓDIGO PURO

---

## Tokens de Design

### Cores — Fundos

| Token                | Valor   | Uso                 |
| -------------------- | ------- | ------------------- |
| `surface-page`     | #F8FAFC | Fundo principal     |
| `surface-card`     | #FFFFFF | Cards               |
| `surface-elevated` | #F1F5F9 | Seções destacadas |

### Cores — Texto

| Token              | Valor   | Uso      |
| ------------------ | ------- | -------- |
| `text-primary`   | #0F172A | Títulos |
| `text-secondary` | #334155 | Texto    |
| `text-muted`     | #64748B | Apoio    |

### Cor Accent — IDENTIDADE ÚNICA

| Token              | Valor               | Uso                       |
| ------------------ | ------------------- | ------------------------- |
| `accent-primary` | #2563EB             | Marca, progresso, ações |
| `accent-hover`   | #1D4ED8             | Hover                     |
| `accent-subtle`  | rgba(37,99,235,0.1) | Fundos suaves             |

### Status (Funcional)

| Token              | Valor   |
| ------------------ | ------- |
| `status-success` | #16A34A |
| `status-warning` | #F59E0B |
| `status-error`   | #DC2626 |

### Geometria

| Token             | Valor |
| ----------------- | ----- |
| `radius-card`   | 14px  |
| `radius-button` | 10px  |
| `radius-input`  | 10px  |

### Sombras

| Token            | Valor                                |
| ---------------- | ------------------------------------ |
| `shadow-card`  | sombra suave, ampla, baixa opacidade |
| `shadow-hover` | levemente mais intensa               |
| `shadow-float` | modais                               |

---

## Regra de Ouro

A Plataforma MEB **não impressiona — orienta**.A identidade visual existe para **reduzir esforço cognitivo**, não para competir com o conteúdo.

> Se um card não conta uma história sobre aprendizagem, ele não pertence à interface.

---

## Frase-Síntese da Alma do App

**“Formar é guiar. A interface é o mapa.”**
