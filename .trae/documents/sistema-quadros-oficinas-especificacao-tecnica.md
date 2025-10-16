# Sistema de Quadros (Oficinas) - Especificação Técnica

## 1. Visão Geral do Sistema

O **Sistema de Quadros (Oficinas)** é uma interface matricial colaborativa que permite a criação e edição de quadros estruturados para workshops, brainstorming e atividades de grupo. O sistema oferece uma experiência visual e intuitiva para organizar informações em formato de grade dinâmica.

### 1.1 Objetivos Principais
- Facilitar workshops colaborativos com interface matricial
- Permitir edição em tempo real de células individuais
- Suportar diferentes templates de quadros
- Integrar-se perfeitamente ao sistema existente de tarefas e GTs
- Oferecer experiência responsiva em diferentes dispositivos

### 1.2 Casos de Uso
- **Matriz SWOT**: Forças, Fraquezas, Oportunidades, Ameaças
- **Canvas de Modelo de Negócio**: 9 blocos estruturados
- **Quadros de Brainstorming**: Ideias organizadas por categorias
- **Matrizes de Decisão**: Critérios vs. Alternativas
- **Quadros de Retrospectiva**: O que funcionou, o que melhorar, ações

## 2. Arquitetura Backend (Existente)

### 2.1 Modelos de Dados

```python
# Quadro Principal
class Quadro(TenantModel):
    gt = models.ForeignKey(GT, on_delete=models.CASCADE)
    template = models.CharField(max_length=120)  # Nome do template
    version = models.PositiveIntegerField(default=1)  # Controle de versão

# Células Individuais
class CelulaQuadro(TenantModel):
    quadro = models.ForeignKey(Quadro, on_delete=models.CASCADE)
    linha = models.PositiveIntegerField()  # Posição Y
    coluna = models.PositiveIntegerField()  # Posição X
    valor_html = models.TextField(blank=True)  # Conteúdo HTML
```

### 2.2 APIs Disponíveis

```typescript
// Endpoints principais
GET /api/v1/quadros/?gt_id={id}&template={template}
GET /api/v1/quadros/{id}/
PUT /api/v1/quadros/{id}/celula/  // Atualizar célula específica

// Estrutura de resposta
interface QuadroResponse {
  id: number;
  gt: number;
  template: string;
  version: number;
  celulas: CelulaQuadro[];
}

interface CelulaQuadro {
  id: number;
  quadro: number;
  linha: number;
  coluna: number;
  valor_html: string;
}
```

## 3. Arquitetura Frontend

### 3.1 Estrutura de Componentes

```
src/
├── components/
│   ├── quadros/
│   │   ├── QuadroGrid.tsx           # Grid principal
│   │   ├── QuadroCell.tsx           # Célula editável
│   │   ├── TemplateSelector.tsx     # Seletor de templates
│   │   ├── QuadroToolbar.tsx        # Barra de ferramentas
│   │   └── QuadroStatusBar.tsx      # Barra de status
├── hooks/
│   ├── useQuadros.ts                # Buscar quadros
│   ├── useQuadro.ts                 # Buscar quadro específico
│   ├── useUpdateCelula.ts           # Atualizar célula
│   └── useQuadroTemplates.ts        # Templates disponíveis
├── pages/
│   └── QuadroPage.tsx               # Página principal
├── types/
│   └── quadro.ts                    # Interfaces TypeScript
└── utils/
    └── quadroTemplates.ts           # Configurações de templates
```

### 3.2 Interfaces TypeScript

```typescript
// Tipos principais
interface Quadro {
  id: number;
  gt: number;
  template: string;
  version: number;
  celulas: CelulaQuadro[];
  created_at: string;
  updated_at: string;
}

interface CelulaQuadro {
  id: number;
  quadro: number;
  linha: number;
  coluna: number;
  valor_html: string;
}

// Configuração de templates
interface QuadroTemplate {
  id: string;
  nome: string;
  descricao: string;
  linhas: number;
  colunas: number;
  cabecalhos?: {
    linhas?: string[];
    colunas?: string[];
  };
  configuracao?: {
    celulasFixas?: Array<{
      linha: number;
      coluna: number;
      valor: string;
      editavel: boolean;
    }>;
    estilos?: {
      [key: string]: React.CSSProperties;
    };
  };
}

// Estados do componente
interface QuadroState {
  quadro: Quadro | null;
  loading: boolean;
  error: string | null;
  editingCell: { linha: number; coluna: number } | null;
  unsavedChanges: boolean;
}
```

## 4. Implementação Detalhada

### 4.1 Hooks React Query

```typescript
// useQuadros.ts - Buscar quadros por GT e template
export const useQuadros = (gtId: number, template?: string) => {
  return useQuery({
    queryKey: ['quadros', gtId, template],
    queryFn: () => api.get('/quadros/', { 
      params: { gt_id: gtId, template } 
    }),
    enabled: !!gtId,
  });
};

// useQuadro.ts - Buscar quadro específico
export const useQuadro = (quadroId: number) => {
  return useQuery({
    queryKey: ['quadro', quadroId],
    queryFn: () => api.get(`/quadros/${quadroId}/`),
    enabled: !!quadroId,
  });
};

// useUpdateCelula.ts - Atualizar célula com debounce
export const useUpdateCelula = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      quadroId, 
      linha, 
      coluna, 
      valor_html 
    }: UpdateCelulaParams) => {
      return api.put(`/quadros/${quadroId}/celula/`, {
        linha,
        coluna,
        valor_html,
      });
    },
    onSuccess: (data, variables) => {
      // Atualizar cache local
      queryClient.setQueryData(
        ['quadro', variables.quadroId],
        (old: Quadro) => {
          if (!old) return old;
          
          const celulas = old.celulas.map(celula => 
            celula.linha === variables.linha && 
            celula.coluna === variables.coluna
              ? { ...celula, valor_html: variables.valor_html }
              : celula
          );
          
          return { ...old, celulas };
        }
      );
    },
  });
};
```

### 4.2 Componente Principal - QuadroGrid

```typescript
// QuadroGrid.tsx
interface QuadroGridProps {
  quadro: Quadro;
  template: QuadroTemplate;
  onCellUpdate: (linha: number, coluna: number, valor: string) => void;
  readonly?: boolean;
}

export const QuadroGrid: React.FC<QuadroGridProps> = ({
  quadro,
  template,
  onCellUpdate,
  readonly = false,
}) => {
  const [editingCell, setEditingCell] = useState<{
    linha: number;
    coluna: number;
  } | null>(null);

  // Criar matriz de células
  const criarMatriz = () => {
    const matriz: (CelulaQuadro | null)[][] = [];
    
    for (let linha = 0; linha < template.linhas; linha++) {
      matriz[linha] = [];
      for (let coluna = 0; coluna < template.colunas; coluna++) {
        const celula = quadro.celulas.find(
          c => c.linha === linha && c.coluna === coluna
        );
        matriz[linha][coluna] = celula || null;
      }
    }
    
    return matriz;
  };

  const matriz = criarMatriz();

  return (
    <div className="quadro-grid">
      {/* Cabeçalhos de colunas */}
      {template.cabecalhos?.colunas && (
        <div className="grid-header-row">
          <div className="grid-corner"></div>
          {template.cabecalhos.colunas.map((cabecalho, index) => (
            <div key={index} className="grid-header-cell">
              {cabecalho}
            </div>
          ))}
        </div>
      )}

      {/* Linhas da matriz */}
      {matriz.map((linha, linhaIndex) => (
        <div key={linhaIndex} className="grid-row">
          {/* Cabeçalho da linha */}
          {template.cabecalhos?.linhas && (
            <div className="grid-header-cell">
              {template.cabecalhos.linhas[linhaIndex]}
            </div>
          )}

          {/* Células da linha */}
          {linha.map((celula, colunaIndex) => (
            <QuadroCell
              key={`${linhaIndex}-${colunaIndex}`}
              celula={celula}
              linha={linhaIndex}
              coluna={colunaIndex}
              isEditing={
                editingCell?.linha === linhaIndex &&
                editingCell?.coluna === colunaIndex
              }
              onStartEdit={() => 
                !readonly && setEditingCell({ 
                  linha: linhaIndex, 
                  coluna: colunaIndex 
                })
              }
              onFinishEdit={(valor) => {
                onCellUpdate(linhaIndex, colunaIndex, valor);
                setEditingCell(null);
              }}
              readonly={readonly}
            />
          ))}
        </div>
      ))}
    </div>
  );
};
```

### 4.3 Componente de Célula - QuadroCell

```typescript
// QuadroCell.tsx
interface QuadroCellProps {
  celula: CelulaQuadro | null;
  linha: number;
  coluna: number;
  isEditing: boolean;
  onStartEdit: () => void;
  onFinishEdit: (valor: string) => void;
  readonly?: boolean;
}

export const QuadroCell: React.FC<QuadroCellProps> = ({
  celula,
  linha,
  coluna,
  isEditing,
  onStartEdit,
  onFinishEdit,
  readonly = false,
}) => {
  const [valor, setValor] = useState(celula?.valor_html || '');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [isEditing]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onFinishEdit(valor);
    } else if (e.key === 'Escape') {
      setValor(celula?.valor_html || '');
      onFinishEdit(celula?.valor_html || '');
    }
  };

  const handleBlur = () => {
    onFinishEdit(valor);
  };

  if (isEditing) {
    return (
      <div className="quadro-cell editing">
        <textarea
          ref={textareaRef}
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          className="cell-editor"
          placeholder="Digite o conteúdo..."
        />
      </div>
    );
  }

  return (
    <div
      className={`quadro-cell ${readonly ? 'readonly' : 'editable'}`}
      onClick={!readonly ? onStartEdit : undefined}
      title={readonly ? undefined : 'Clique para editar'}
    >
      {celula?.valor_html ? (
        <div
          className="cell-content"
          dangerouslySetInnerHTML={{ __html: celula.valor_html }}
        />
      ) : (
        <div className="cell-placeholder">
          {readonly ? '' : 'Clique para adicionar conteúdo'}
        </div>
      )}
    </div>
  );
};
```

### 4.4 Sistema de Templates

```typescript
// quadroTemplates.ts
export const QUADRO_TEMPLATES: Record<string, QuadroTemplate> = {
  swot: {
    id: 'swot',
    nome: 'Análise SWOT',
    descricao: 'Matriz de Forças, Fraquezas, Oportunidades e Ameaças',
    linhas: 2,
    colunas: 2,
    cabecalhos: {
      linhas: ['Fatores Internos', 'Fatores Externos'],
      colunas: ['Positivos', 'Negativos'],
    },
    configuracao: {
      celulasFixas: [
        { linha: 0, coluna: 0, valor: '<strong>FORÇAS</strong>', editavel: false },
        { linha: 0, coluna: 1, valor: '<strong>FRAQUEZAS</strong>', editavel: false },
        { linha: 1, coluna: 0, valor: '<strong>OPORTUNIDADES</strong>', editavel: false },
        { linha: 1, coluna: 1, valor: '<strong>AMEAÇAS</strong>', editavel: false },
      ],
    },
  },

  canvas: {
    id: 'canvas',
    nome: 'Business Model Canvas',
    descricao: 'Modelo de 9 blocos para planejamento de negócios',
    linhas: 3,
    colunas: 5,
    cabecalhos: {
      colunas: [
        'Parcerias Chave',
        'Atividades Chave',
        'Proposta de Valor',
        'Relacionamento',
        'Segmentos de Cliente'
      ],
    },
  },

  brainstorm: {
    id: 'brainstorm',
    nome: 'Quadro de Brainstorming',
    descricao: 'Grade livre para organização de ideias',
    linhas: 4,
    colunas: 4,
  },

  decisao: {
    id: 'decisao',
    nome: 'Matriz de Decisão',
    descricao: 'Critérios vs. Alternativas para tomada de decisão',
    linhas: 5,
    colunas: 4,
    cabecalhos: {
      linhas: ['Critério 1', 'Critério 2', 'Critério 3', 'Critério 4', 'TOTAL'],
      colunas: ['Alternativa A', 'Alternativa B', 'Alternativa C', 'Melhor Opção'],
    },
  },

  retrospectiva: {
    id: 'retrospectiva',
    nome: 'Retrospectiva',
    descricao: 'O que funcionou, o que melhorar, próximas ações',
    linhas: 1,
    colunas: 3,
    cabecalhos: {
      colunas: ['O que funcionou bem?', 'O que pode melhorar?', 'Próximas ações'],
    },
  },
};
```

## 5. Página Principal - QuadroPage

```typescript
// QuadroPage.tsx
export const QuadroPage: React.FC = () => {
  const { tarefaId, gt: gtParam } = useParams();
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [gtId, setGtId] = useState<number>(Number(gtParam) || 0);

  // Hooks para dados
  const { data: tarefa } = useTarefa(Number(tarefaId));
  const { data: quadros, isLoading: loadingQuadros } = useQuadros(
    gtId, 
    selectedTemplate
  );
  const updateCelula = useUpdateCelula();

  // Auto-save com debounce
  const debouncedUpdate = useMemo(
    () => debounce((quadroId: number, linha: number, coluna: number, valor: string) => {
      updateCelula.mutate({ quadroId, linha, coluna, valor_html: valor });
    }, 500),
    [updateCelula]
  );

  const handleCellUpdate = (linha: number, coluna: number, valor: string) => {
    if (quadros?.[0]) {
      debouncedUpdate(quadros[0].id, linha, coluna, valor);
    }
  };

  const currentTemplate = selectedTemplate 
    ? QUADRO_TEMPLATES[selectedTemplate] 
    : null;

  const currentQuadro = quadros?.[0] || null;

  return (
    <div className="quadro-page">
      <div className="quadro-header">
        <div className="quadro-title">
          <h1>Quadro - {tarefa?.nome}</h1>
          <div className="quadro-meta">
            GT: {gtId} | Template: {currentTemplate?.nome || 'Nenhum'}
          </div>
        </div>

        <QuadroToolbar
          selectedTemplate={selectedTemplate}
          onTemplateChange={setSelectedTemplate}
          gtId={gtId}
          onGtChange={setGtId}
          saving={updateCelula.isPending}
        />
      </div>

      <div className="quadro-content">
        {loadingQuadros ? (
          <div className="loading-state">
            <div className="spinner" />
            <p>Carregando quadro...</p>
          </div>
        ) : currentTemplate && currentQuadro ? (
          <QuadroGrid
            quadro={currentQuadro}
            template={currentTemplate}
            onCellUpdate={handleCellUpdate}
          />
        ) : (
          <div className="empty-state">
            <h3>Selecione um template para começar</h3>
            <p>Escolha um template na barra de ferramentas acima.</p>
          </div>
        )}
      </div>

      <QuadroStatusBar
        saving={updateCelula.isPending}
        lastSaved={currentQuadro?.updated_at}
        error={updateCelula.error?.message}
      />
    </div>
  );
};
```

## 6. Estilos CSS

```css
/* QuadroGrid.css */
.quadro-grid {
  display: table;
  border-collapse: collapse;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.grid-header-row,
.grid-row {
  display: table-row;
}

.grid-header-cell {
  display: table-cell;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 12px;
  font-weight: 600;
  text-align: center;
  vertical-align: middle;
  min-width: 150px;
}

.grid-corner {
  display: table-cell;
  background: #e9ecef;
  border: 1px solid #dee2e6;
  width: 120px;
}

.quadro-cell {
  display: table-cell;
  border: 1px solid #dee2e6;
  padding: 8px;
  vertical-align: top;
  min-height: 80px;
  min-width: 150px;
  position: relative;
  transition: all 0.2s ease;
}

.quadro-cell.editable {
  cursor: pointer;
}

.quadro-cell.editable:hover {
  background-color: #f8f9fa;
  border-color: #007bff;
}

.quadro-cell.editing {
  padding: 0;
  background-color: #fff;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.cell-editor {
  width: 100%;
  height: 100%;
  min-height: 80px;
  border: none;
  padding: 8px;
  resize: none;
  font-family: inherit;
  font-size: inherit;
  outline: none;
  background: transparent;
}

.cell-content {
  min-height: 60px;
  word-wrap: break-word;
}

.cell-placeholder {
  color: #6c757d;
  font-style: italic;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.quadro-cell.readonly .cell-placeholder {
  display: none;
}

/* Responsividade */
@media (max-width: 768px) {
  .quadro-grid {
    font-size: 14px;
  }
  
  .grid-header-cell,
  .quadro-cell {
    min-width: 120px;
    padding: 6px;
  }
  
  .cell-editor {
    min-height: 60px;
    padding: 6px;
  }
}
```

## 7. Integração com Sistema Existente

### 7.1 Roteamento

```typescript
// router.tsx - Adicionar nova rota
{
  path: "/quadros/:tarefaId",
  element: (
    <ProtectedRoute>
      <QuadroPage />
    </ProtectedRoute>
  ),
}
```

### 7.2 Navegação desde TaskDetailPage

```typescript
// TaskDetailPage.tsx - Adicionar link para quadros
const handleQuadroClick = () => {
  navigate(`/quadros/${tarefa.id}?gt=${selectedGt}`);
};

// No JSX
<button
  onClick={handleQuadroClick}
  className="btn btn-secondary"
  disabled={!selectedGt}
>
  <i className="fas fa-th"></i>
  Quadro
</button>
```

## 8. Fases de Implementação

### Fase 1: Estrutura Base (1-2 dias)
- [ ] Criar interfaces TypeScript
- [ ] Implementar hooks básicos (useQuadros, useQuadro)
- [ ] Criar componente QuadroGrid básico
- [ ] Implementar QuadroCell com edição simples

### Fase 2: Templates e Funcionalidades (2-3 dias)
- [ ] Sistema de templates configuráveis
- [ ] TemplateSelector component
- [ ] Implementar auto-save com debounce
- [ ] QuadroToolbar e QuadroStatusBar

### Fase 3: UX/UI Avançada (1-2 dias)
- [ ] Estilos CSS responsivos
- [ ] Estados de loading e erro
- [ ] Navegação por teclado
- [ ] Indicadores visuais de edição

### Fase 4: Integração e Testes (1 dia)
- [ ] Integrar com TaskDetailPage
- [ ] Testes de funcionalidade
- [ ] Ajustes de performance
- [ ] Documentação de uso

## 9. Considerações Técnicas

### 9.1 Performance
- **Virtualização**: Para quadros muito grandes, implementar virtualização de células
- **Debouncing**: Auto-save com 500ms de delay para evitar requests excessivos
- **Cache**: React Query para cache inteligente de dados
- **Lazy Loading**: Carregar templates sob demanda

### 9.2 Acessibilidade
- **Navegação por teclado**: Tab, Enter, Escape para navegação
- **ARIA labels**: Identificação adequada de células e controles
- **Contraste**: Cores adequadas para leitura
- **Screen readers**: Suporte para leitores de tela

### 9.3 Colaboração
- **Indicadores visuais**: Mostrar quem está editando cada célula
- **Conflitos**: Detectar e resolver conflitos de edição simultânea
- **Histórico**: Rastrear mudanças e permitir reversão
- **Notificações**: Alertar sobre mudanças de outros usuários

### 9.4 Extensibilidade
- **Templates customizáveis**: Permitir criação de novos templates
- **Plugins**: Sistema para extensões de funcionalidade
- **Exportação**: PDF, Excel, imagem dos quadros
- **Importação**: Dados de planilhas externas

## 10. Métricas de Sucesso

### 10.1 Técnicas
- Tempo de carregamento < 2 segundos
- Auto-save funcionando em < 500ms
- Zero erros de sincronização
- 100% responsivo em dispositivos móveis

### 10.2 Usabilidade
- Facilidade de criação de novos quadros
- Intuitividade na edição de células
- Satisfação dos usuários com templates
- Redução no tempo de organização de workshops

Este sistema transformará a experiência de workshops e atividades colaborativas, oferecendo uma ferramenta poderosa e intuitiva para organização visual de informações em formato matricial.