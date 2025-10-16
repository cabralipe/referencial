# Sistema de Reviews - Especificação Técnica

## 1. Visão Geral

O **Sistema de Reviews** é um módulo de avaliação e feedback que permite aos usuários solicitar, gerenciar e executar revisões de conteúdo (Respostas, Textos Únicos e Quadros) com fluxo de aprovação estruturado.

## 2. Análise do Backend

### 2.1 Modelo de Dados

```typescript
interface Revisao {
  id: number;
  alvo_tipo: 'resposta' | 'texto_unico' | 'quadro';
  alvo_id: string;
  status: 'rascunho' | 'em_revisao' | 'aprovado' | 'reprovado';
  parecer_html: string;
  revisor: number | null;
  solicitante: number | null;
  created_at: string;
  updated_at: string;
  etag: string;
}
```

### 2.2 API Endpoints

- **GET /api/v1/revisoes/** - Listar revisões (filtros: alvo_tipo, alvo_id, status)
- **POST /api/v1/revisoes/** - Criar nova revisão
- **GET /api/v1/revisoes/{id}/** - Obter revisão específica
- **PUT /api/v1/revisoes/{id}/** - Atualizar revisão
- **DELETE /api/v1/revisoes/{id}/** - Deletar revisão

### 2.3 Permissões e Regras

- **Criação**: Articuladores e Admins podem solicitar revisões
- **Revisão**: Apenas o revisor designado pode aprovar/reprovar
- **Visualização**: Membros do GT podem ver revisões relacionadas
- **Feature Flag**: `ff.reviews.enabled`

## 3. Arquitetura Frontend

### 3.1 Estrutura de Componentes

```
src/
├── components/
│   └── reviews/
│       ├── ReviewCard.tsx           # Card individual de revisão
│       ├── ReviewList.tsx           # Lista de revisões
│       ├── ReviewForm.tsx           # Formulário criar/editar
│       ├── ReviewStatusBadge.tsx    # Badge de status
│       ├── ReviewWorkflow.tsx       # Interface de workflow
│       ├── ReviewerSelector.tsx     # Seletor de revisor
│       ├── ReviewParecer.tsx        # Editor de parecer
│       └── ReviewHistory.tsx        # Histórico de revisões
├── hooks/
│   ├── useReviews.ts               # Hook principal
│   ├── useCreateReview.ts          # Criar revisão
│   ├── useUpdateReview.ts          # Atualizar revisão
│   └── useReviewActions.ts         # Ações de workflow
├── pages/
│   ├── ReviewsPage.tsx             # Página principal
│   └── ReviewDetailPage.tsx        # Detalhes da revisão
└── utils/
    ├── reviewHelpers.ts            # Utilitários
    └── reviewValidation.ts         # Validações
```

### 3.2 TypeScript Interfaces

```typescript
// Tipos base
interface Review {
  id: number;
  alvo_tipo: ReviewTargetType;
  alvo_id: string;
  status: ReviewStatus;
  parecer_html: string;
  revisor: User | null;
  solicitante: User | null;
  created_at: string;
  updated_at: string;
  etag: string;
}

type ReviewTargetType = 'resposta' | 'texto_unico' | 'quadro';
type ReviewStatus = 'rascunho' | 'em_revisao' | 'aprovado' | 'reprovado';

// Payloads para API
interface CreateReviewPayload {
  alvo_tipo: ReviewTargetType;
  alvo_id: string;
  revisor?: number;
  parecer_html?: string;
}

interface UpdateReviewPayload {
  status?: ReviewStatus;
  parecer_html?: string;
  revisor?: number;
}

// Estados da interface
interface ReviewState {
  selectedReview: Review | null;
  isEditing: boolean;
  hasUnsavedChanges: boolean;
  filter: ReviewFilter;
}

interface ReviewFilter {
  status?: ReviewStatus;
  alvo_tipo?: ReviewTargetType;
  revisor?: number;
  solicitante?: number;
}
```

### 3.3 React Query Hooks

```typescript
// useReviews.ts
export function useReviews(filter?: ReviewFilter) {
  const client = useApiClient();
  
  return useQuery({
    queryKey: ['reviews', filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filter?.status) params.append('status', filter.status);
      if (filter?.alvo_tipo) params.append('alvo_tipo', filter.alvo_tipo);
      if (filter?.alvo_id) params.append('alvo_id', filter.alvo_id);
      
      const response = await client.get<PaginatedResponse<Review>>(`/revisoes?${params}`);
      return response.data;
    },
    staleTime: 30000,
  });
}

// useCreateReview.ts
export function useCreateReview() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: CreateReviewPayload) => {
      const response = await client.post<Review>('/revisoes', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Revisão solicitada com sucesso!');
    },
    onError: (error) => {
      toast.error('Erro ao solicitar revisão');
    },
  });
}

// useUpdateReview.ts
export function useUpdateReview() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, payload, etag }: { 
      id: number; 
      payload: UpdateReviewPayload; 
      etag: string;
    }) => {
      const response = await client.put<Review>(`/revisoes/${id}`, payload, {
        headers: { 'If-Match': etag },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['review', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Revisão atualizada com sucesso!');
    },
  });
}
```

## 4. Componentes Principais

### 4.1 ReviewCard.tsx

```typescript
interface ReviewCardProps {
  review: Review;
  onEdit?: (review: Review) => void;
  onApprove?: (review: Review) => void;
  onReject?: (review: Review) => void;
  showActions?: boolean;
}

export function ReviewCard({ review, onEdit, onApprove, onReject, showActions = true }: ReviewCardProps) {
  const { user } = useAuth();
  const canReview = user?.id === review.revisor?.id;
  const canEdit = user?.id === review.solicitante?.id && review.status === 'rascunho';
  
  return (
    <div className="review-card">
      <div className="review-card__header">
        <div className="review-card__info">
          <h3>Revisão {getTargetTypeLabel(review.alvo_tipo)}</h3>
          <ReviewStatusBadge status={review.status} />
        </div>
        <div className="review-card__meta">
          <span>Solicitado por: {review.solicitante?.name}</span>
          <span>Revisor: {review.revisor?.name || 'Não atribuído'}</span>
        </div>
      </div>
      
      {review.parecer_html && (
        <div className="review-card__parecer">
          <h4>Parecer:</h4>
          <div dangerouslySetInnerHTML={{ __html: review.parecer_html }} />
        </div>
      )}
      
      {showActions && (
        <div className="review-card__actions">
          {canEdit && (
            <button onClick={() => onEdit?.(review)} className="btn btn--secondary">
              Editar
            </button>
          )}
          {canReview && review.status === 'em_revisao' && (
            <>
              <button onClick={() => onApprove?.(review)} className="btn btn--success">
                Aprovar
              </button>
              <button onClick={() => onReject?.(review)} className="btn btn--danger">
                Reprovar
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
```

### 4.2 ReviewWorkflow.tsx

```typescript
interface ReviewWorkflowProps {
  targetType: ReviewTargetType;
  targetId: string;
  existingReview?: Review;
}

export function ReviewWorkflow({ targetType, targetId, existingReview }: ReviewWorkflowProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedRevisor, setSelectedRevisor] = useState<User | null>(null);
  const [parecer, setParecer] = useState('');
  
  const createReview = useCreateReview();
  const updateReview = useUpdateReview();
  
  const handleSubmitReview = async () => {
    if (existingReview) {
      await updateReview.mutateAsync({
        id: existingReview.id,
        payload: {
          status: 'em_revisao',
          parecer_html: parecer,
          revisor: selectedRevisor?.id,
        },
        etag: existingReview.etag,
      });
    } else {
      await createReview.mutateAsync({
        alvo_tipo: targetType,
        alvo_id: targetId,
        revisor: selectedRevisor?.id,
        parecer_html: parecer,
      });
    }
    setIsOpen(false);
  };
  
  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        className="btn btn--primary"
      >
        {existingReview ? 'Gerenciar Revisão' : 'Solicitar Revisão'}
      </button>
      
      {isOpen && (
        <Modal onClose={() => setIsOpen(false)}>
          <div className="review-workflow">
            <h3>Solicitar Revisão</h3>
            
            <ReviewerSelector
              value={selectedRevisor}
              onChange={setSelectedRevisor}
            />
            
            <RichTextEditor
              value={parecer}
              onChange={setParecer}
              placeholder="Adicione observações para o revisor..."
            />
            
            <div className="review-workflow__actions">
              <button onClick={() => setIsOpen(false)} className="btn btn--secondary">
                Cancelar
              </button>
              <button 
                onClick={handleSubmitReview}
                disabled={!selectedRevisor}
                className="btn btn--primary"
              >
                Solicitar Revisão
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
```

### 4.3 ReviewsPage.tsx

```typescript
export function ReviewsPage() {
  const [filter, setFilter] = useState<ReviewFilter>({});
  const { data: reviews, isLoading } = useReviews(filter);
  const { user } = useAuth();
  
  const tabs = [
    { key: 'all', label: 'Todas', count: reviews?.results.length || 0 },
    { key: 'pending', label: 'Pendentes', count: reviews?.results.filter(r => r.status === 'em_revisao').length || 0 },
    { key: 'my-requests', label: 'Minhas Solicitações', count: reviews?.results.filter(r => r.solicitante?.id === user?.id).length || 0 },
    { key: 'my-reviews', label: 'Para Revisar', count: reviews?.results.filter(r => r.revisor?.id === user?.id).length || 0 },
  ];
  
  return (
    <div className="reviews-page">
      <div className="reviews-page__header">
        <h1>Sistema de Reviews</h1>
        <div className="reviews-page__stats">
          {tabs.map(tab => (
            <div key={tab.key} className="stat-card">
              <span className="stat-card__value">{tab.count}</span>
              <span className="stat-card__label">{tab.label}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="reviews-page__filters">
        <select 
          value={filter.status || ''} 
          onChange={(e) => setFilter(prev => ({ ...prev, status: e.target.value as ReviewStatus || undefined }))}
        >
          <option value="">Todos os status</option>
          <option value="rascunho">Rascunho</option>
          <option value="em_revisao">Em Revisão</option>
          <option value="aprovado">Aprovado</option>
          <option value="reprovado">Reprovado</option>
        </select>
        
        <select 
          value={filter.alvo_tipo || ''} 
          onChange={(e) => setFilter(prev => ({ ...prev, alvo_tipo: e.target.value as ReviewTargetType || undefined }))}
        >
          <option value="">Todos os tipos</option>
          <option value="resposta">Respostas</option>
          <option value="texto_unico">Textos Únicos</option>
          <option value="quadro">Quadros</option>
        </select>
      </div>
      
      <div className="reviews-page__content">
        {isLoading ? (
          <div className="loading">Carregando revisões...</div>
        ) : (
          <ReviewList reviews={reviews?.results || []} />
        )}
      </div>
    </div>
  );
}
```

## 5. Integração com Sistemas Existentes

### 5.1 TaskDetailPage.tsx

```typescript
// Adicionar botão de revisão na página de detalhes da tarefa
{selectedGtId && (
  <div className="task-detail__review-section">
    <ReviewWorkflow
      targetType="resposta"
      targetId={`${tarefa.id}-${selectedGtId}`}
    />
  </div>
)}
```

### 5.2 TextoUnicoPage.tsx

```typescript
// Adicionar controle de revisão no editor de texto único
<div className="texto-unico__toolbar">
  <ReviewWorkflow
    targetType="texto_unico"
    targetId={textoUnico?.id.toString() || ''}
    existingReview={existingReview}
  />
</div>
```

### 5.3 QuadroPage.tsx

```typescript
// Adicionar revisão no sistema de quadros
<QuadroToolbar>
  <ReviewWorkflow
    targetType="quadro"
    targetId={quadro?.id.toString() || ''}
  />
</QuadroToolbar>
```

## 6. Roteamento

```typescript
// router.tsx
{
  path: '/reviews',
  element: <ProtectedRoute><ReviewsPage /></ProtectedRoute>,
},
{
  path: '/reviews/:reviewId',
  element: <ProtectedRoute><ReviewDetailPage /></ProtectedRoute>,
},
```

## 7. Estilos CSS

### 7.1 ReviewCard.css

```css
.review-card {
  background: white;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  transition: box-shadow 0.2s ease;
}

.review-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.review-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.review-card__info h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.review-card__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: #6c757d;
}

.review-card__parecer {
  margin: 16px 0;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;
}

.review-card__actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
```

### 7.2 ReviewStatusBadge.css

```css
.review-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.review-status-badge--rascunho {
  background: #e9ecef;
  color: #495057;
}

.review-status-badge--em_revisao {
  background: #fff3cd;
  color: #856404;
}

.review-status-badge--aprovado {
  background: #d1edff;
  color: #0c5460;
}

.review-status-badge--reprovado {
  background: #f8d7da;
  color: #721c24;
}
```

## 8. Considerações de UX

### 8.1 Fluxo de Trabalho

1. **Solicitação**: Interface clara para solicitar revisões
2. **Notificações**: Alertas para revisores quando atribuídos
3. **Status Visual**: Badges e indicadores de progresso
4. **Histórico**: Rastreamento completo de mudanças
5. **Feedback**: Mensagens claras de sucesso/erro

### 8.2 Responsividade

- Layout adaptável para mobile/tablet
- Componentes otimizados para touch
- Navegação simplificada em telas pequenas

### 8.3 Acessibilidade

- Suporte a leitores de tela
- Navegação por teclado
- Contraste adequado
- Labels descritivos

## 9. Performance

### 9.1 Otimizações

- React Query para cache inteligente
- Lazy loading de componentes
- Debounce em filtros
- Paginação eficiente

### 9.2 Métricas

- Tempo de carregamento < 2s
- Interações responsivas < 100ms
- Cache hit rate > 80%

## 10. Testes

### 10.1 Testes Unitários

- Hooks de React Query
- Componentes isolados
- Utilitários e validações

### 10.2 Testes de Integração

- Fluxo completo de revisão
- Integração com APIs
- Estados de erro

### 10.3 Testes E2E

- Jornada do usuário completa
- Diferentes perfis de acesso
- Cenários de erro