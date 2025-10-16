# Sistema de Comentários - Especificação Técnica

## 1. Visão Geral

O **Sistema de Comentários** é um módulo de colaboração em tempo real que permite comentários inline, threads de discussão, menções de usuários e workflow de resolução, integrado com WebSocket para atualizações instantâneas.

## 2. Análise do Backend

### 2.1 Modelo de Dados

```typescript
interface Comentario {
  id: number;
  alvo_tipo: 'resposta' | 'texto_unico' | 'quadro';
  alvo_id: string;
  anchor_json: Record<string, any>; // Dados de ancoragem (posição, seleção, etc.)
  conteudo_html: string;
  autor: number;
  resolvido: boolean;
  resolvido_por: number | null;
  resolved_at: string | null;
  mentions: number[]; // IDs dos usuários mencionados
  mentions_ids: number[]; // Campo calculado do serializer
  created_at: string;
  updated_at: string;
  etag: string;
}
```

### 2.2 API Endpoints

- **GET /api/v1/comentarios/** - Listar comentários (filtros: alvo_tipo, alvo_id, resolvido)
- **POST /api/v1/comentarios/** - Criar novo comentário
- **GET /api/v1/comentarios/{id}/** - Obter comentário específico
- **PUT /api/v1/comentarios/{id}/** - Atualizar comentário (resolver/editar)
- **DELETE /api/v1/comentarios/{id}/** - Deletar comentário

### 2.3 WebSocket Events

- **comentario_criado**: Novo comentário adicionado
- **comentario_atualizado**: Comentário editado ou resolvido
- **comentario_deletado**: Comentário removido
- **mencao_criada**: Usuário foi mencionado em comentário

### 2.4 Permissões e Regras

- **Criação**: Membros GT, Articuladores e Admins podem criar comentários
- **Edição**: Apenas autor pode editar próprios comentários
- **Resolução**: Apenas Articuladores e Admins podem resolver comentários
- **Visualização**: Membros do GT podem ver comentários relacionados
- **Feature Flag**: `ff.comments.enabled`

## 3. Arquitetura Frontend

### 3.1 Estrutura de Componentes

```
src/
├── components/
│   └── comments/
│       ├── CommentCard.tsx           # Card individual de comentário
│       ├── CommentList.tsx           # Lista de comentários
│       ├── CommentForm.tsx           # Formulário criar/editar
│       ├── CommentThread.tsx         # Thread de discussão
│       ├── CommentEditor.tsx         # Editor rico de comentários
│       ├── CommentAnchor.tsx         # Indicador de ancoragem
│       ├── CommentSidebar.tsx        # Painel lateral de comentários
│       ├── CommentInline.tsx         # Comentários inline no conteúdo
│       ├── CommentMentions.tsx       # Sistema de menções
│       ├── CommentResolution.tsx     # Controles de resolução
│       └── CommentFilters.tsx        # Filtros e busca
├── hooks/
│   ├── useComments.ts               # Hook principal
│   ├── useCreateComment.ts          # Criar comentário
│   ├── useUpdateComment.ts          # Atualizar comentário
│   ├── useCommentMentions.ts        # Sistema de menções
│   ├── useCommentRealtime.ts        # WebSocket integration
│   └── useCommentAnchoring.ts       # Sistema de ancoragem
├── pages/
│   └── (integração com páginas existentes)
├── utils/
│   ├── commentHelpers.ts            # Utilitários
│   ├── commentAnchoring.ts          # Lógica de ancoragem
│   ├── commentMentions.ts           # Processamento de menções
│   └── commentValidation.ts         # Validações
└── styles/
    └── comments.css                 # Estilos específicos
```

### 3.2 TypeScript Interfaces

```typescript
// Tipos base
interface Comment {
  id: number;
  alvo_tipo: CommentTargetType;
  alvo_id: string;
  anchor_json: CommentAnchor;
  conteudo_html: string;
  autor: User;
  resolvido: boolean;
  resolvido_por: User | null;
  resolved_at: string | null;
  mentions_ids: number[];
  created_at: string;
  updated_at: string;
  etag: string;
  replies?: Comment[]; // Para threads aninhadas
}

type CommentTargetType = 'resposta' | 'texto_unico' | 'quadro';

// Dados de ancoragem
interface CommentAnchor {
  type: 'text_selection' | 'paragraph' | 'cell' | 'general';
  startOffset?: number;
  endOffset?: number;
  selectedText?: string;
  paragraphIndex?: number;
  cellId?: string;
  coordinates?: { x: number; y: number };
}

// Payloads para API
interface CreateCommentPayload {
  alvo_tipo: CommentTargetType;
  alvo_id: string;
  anchor_json: CommentAnchor;
  conteudo_html: string;
  mentions?: number[];
  parent_id?: number; // Para replies
}

interface UpdateCommentPayload {
  conteudo_html?: string;
  resolvido?: boolean;
  mentions?: number[];
}

// Estados da interface
interface CommentState {
  selectedComment: Comment | null;
  isEditing: boolean;
  showResolved: boolean;
  filter: CommentFilter;
  realtimeEnabled: boolean;
}

interface CommentFilter {
  resolvido?: boolean;
  autor?: number;
  search?: string;
  dateRange?: { start: string; end: string };
}

// Eventos WebSocket
interface CommentWebSocketEvent {
  type: 'comentario_criado' | 'comentario_atualizado' | 'comentario_deletado' | 'mencao_criada';
  payload: {
    comentario_id: number;
    alvo_tipo: CommentTargetType;
    alvo_id: string;
    conteudo_html?: string;
    autor?: User;
    mentions_ids?: number[];
  };
}
```

### 3.3 React Query Hooks

```typescript
// useComments.ts
export function useComments(targetType: CommentTargetType, targetId: string, filter?: CommentFilter) {
  const client = useApiClient();
  
  return useQuery({
    queryKey: ['comments', targetType, targetId, filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('alvo_tipo', targetType);
      params.append('alvo_id', targetId);
      if (filter?.resolvido !== undefined) params.append('resolvido', filter.resolvido.toString());
      if (filter?.autor) params.append('autor', filter.autor.toString());
      
      const response = await client.get<PaginatedResponse<Comment>>(`/comentarios?${params}`);
      return response.data;
    },
    staleTime: 30000,
  });
}

// useCreateComment.ts
export function useCreateComment() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: CreateCommentPayload) => {
      const response = await client.post<Comment>('/comentarios', payload);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ 
        queryKey: ['comments', data.alvo_tipo, data.alvo_id] 
      });
      
      // Broadcast via WebSocket se necessário
      broadcastCommentEvent('comentario_criado', data);
      
      toast.success('Comentário adicionado com sucesso!');
    },
    onError: (error) => {
      toast.error('Erro ao adicionar comentário');
    },
  });
}

// useUpdateComment.ts
export function useUpdateComment() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, payload, etag }: { 
      id: number; 
      payload: UpdateCommentPayload; 
      etag: string;
    }) => {
      const response = await client.put<Comment>(`/comentarios/${id}`, payload, {
        headers: { 'If-Match': etag },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['comment', data.id], data);
      queryClient.invalidateQueries({ 
        queryKey: ['comments', data.alvo_tipo, data.alvo_id] 
      });
      
      broadcastCommentEvent('comentario_atualizado', data);
      toast.success('Comentário atualizado com sucesso!');
    },
  });
}

// useCommentRealtime.ts
export function useCommentRealtime(targetType: CommentTargetType, targetId: string) {
  const queryClient = useQueryClient();
  const { socket } = useWebSocket();
  
  useEffect(() => {
    if (!socket) return;
    
    const handleCommentEvent = (event: CommentWebSocketEvent) => {
      if (event.payload.alvo_tipo === targetType && event.payload.alvo_id === targetId) {
        // Invalidar e refetch comentários
        queryClient.invalidateQueries({ 
          queryKey: ['comments', targetType, targetId] 
        });
        
        // Mostrar notificação se necessário
        if (event.type === 'comentario_criado') {
          toast.info('Novo comentário adicionado');
        }
      }
    };
    
    socket.on('comment_event', handleCommentEvent);
    
    return () => {
      socket.off('comment_event', handleCommentEvent);
    };
  }, [socket, targetType, targetId, queryClient]);
}
```

## 4. Componentes Principais

### 4.1 CommentCard.tsx

```typescript
interface CommentCardProps {
  comment: Comment;
  onReply?: (comment: Comment) => void;
  onResolve?: (comment: Comment) => void;
  onEdit?: (comment: Comment) => void;
  onDelete?: (comment: Comment) => void;
  showActions?: boolean;
  isNested?: boolean;
}

export function CommentCard({ 
  comment, 
  onReply, 
  onResolve, 
  onEdit, 
  onDelete, 
  showActions = true,
  isNested = false 
}: CommentCardProps) {
  const { user } = useAuth();
  const canResolve = user?.role === 'ARTICULADOR' || user?.role === 'ADMIN_CLIENTE';
  const canEdit = user?.id === comment.autor.id;
  const canDelete = canEdit || canResolve;
  
  return (
    <div className={`comment-card ${comment.resolvido ? 'comment-card--resolved' : ''} ${isNested ? 'comment-card--nested' : ''}`}>
      <div className="comment-card__header">
        <div className="comment-card__author">
          <Avatar user={comment.autor} size="sm" />
          <div className="comment-card__meta">
            <span className="comment-card__author-name">{comment.autor.name}</span>
            <span className="comment-card__timestamp">
              {formatRelativeTime(comment.created_at)}
            </span>
          </div>
        </div>
        
        {comment.resolvido && (
          <div className="comment-card__resolved-badge">
            <CheckCircle size={16} />
            <span>Resolvido</span>
          </div>
        )}
      </div>
      
      <div className="comment-card__content">
        <div 
          className="comment-card__html-content"
          dangerouslySetInnerHTML={{ __html: comment.conteudo_html }} 
        />
        
        {comment.mentions_ids.length > 0 && (
          <div className="comment-card__mentions">
            <span>Mencionou:</span>
            {comment.mentions_ids.map(userId => (
              <UserMention key={userId} userId={userId} />
            ))}
          </div>
        )}
      </div>
      
      {showActions && (
        <div className="comment-card__actions">
          <button 
            onClick={() => onReply?.(comment)}
            className="comment-action comment-action--reply"
          >
            <MessageCircle size={14} />
            Responder
          </button>
          
          {canResolve && !comment.resolvido && (
            <button 
              onClick={() => onResolve?.(comment)}
              className="comment-action comment-action--resolve"
            >
              <CheckCircle size={14} />
              Resolver
            </button>
          )}
          
          {canEdit && (
            <button 
              onClick={() => onEdit?.(comment)}
              className="comment-action comment-action--edit"
            >
              <Edit2 size={14} />
              Editar
            </button>
          )}
          
          {canDelete && (
            <button 
              onClick={() => onDelete?.(comment)}
              className="comment-action comment-action--delete"
            >
              <Trash2 size={14} />
              Deletar
            </button>
          )}
        </div>
      )}
      
      {comment.replies && comment.replies.length > 0 && (
        <div className="comment-card__replies">
          {comment.replies.map(reply => (
            <CommentCard
              key={reply.id}
              comment={reply}
              onReply={onReply}
              onResolve={onResolve}
              onEdit={onEdit}
              onDelete={onDelete}
              isNested={true}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 4.2 CommentEditor.tsx

```typescript
interface CommentEditorProps {
  targetType: CommentTargetType;
  targetId: string;
  anchor?: CommentAnchor;
  parentComment?: Comment;
  initialContent?: string;
  onSave?: (comment: Comment) => void;
  onCancel?: () => void;
  placeholder?: string;
}

export function CommentEditor({ 
  targetType, 
  targetId, 
  anchor, 
  parentComment,
  initialContent = '',
  onSave,
  onCancel,
  placeholder = 'Adicione seu comentário...'
}: CommentEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [mentions, setMentions] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const createComment = useCreateComment();
  const updateComment = useUpdateComment();
  const { data: gtMembers } = useGTMembers();
  
  const handleSubmit = async () => {
    if (!content.trim()) return;
    
    setIsSubmitting(true);
    
    try {
      const payload: CreateCommentPayload = {
        alvo_tipo: targetType,
        alvo_id: targetId,
        anchor_json: anchor || { type: 'general' },
        conteudo_html: content,
        mentions: mentions.length > 0 ? mentions : undefined,
        parent_id: parentComment?.id,
      };
      
      const newComment = await createComment.mutateAsync(payload);
      onSave?.(newComment);
      setContent('');
      setMentions([]);
    } catch (error) {
      console.error('Erro ao salvar comentário:', error);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleMentionSelect = (userId: number) => {
    setMentions(prev => [...prev, userId]);
  };
  
  return (
    <div className="comment-editor">
      <div className="comment-editor__header">
        <h4>
          {parentComment ? 'Responder comentário' : 'Novo comentário'}
        </h4>
        {anchor?.selectedText && (
          <div className="comment-editor__anchor">
            <Quote size={14} />
            <span>"{anchor.selectedText}"</span>
          </div>
        )}
      </div>
      
      <RichTextEditor
        value={content}
        onChange={setContent}
        placeholder={placeholder}
        mentions={{
          users: gtMembers || [],
          onSelect: handleMentionSelect,
        }}
        toolbar={[
          'bold', 'italic', 'link', 'bulletList', 'orderedList'
        ]}
      />
      
      {mentions.length > 0 && (
        <div className="comment-editor__mentions">
          <span>Mencionando:</span>
          {mentions.map(userId => (
            <UserMention 
              key={userId} 
              userId={userId} 
              onRemove={() => setMentions(prev => prev.filter(id => id !== userId))}
            />
          ))}
        </div>
      )}
      
      <div className="comment-editor__actions">
        <button 
          onClick={onCancel}
          className="btn btn--secondary"
          disabled={isSubmitting}
        >
          Cancelar
        </button>
        <button 
          onClick={handleSubmit}
          className="btn btn--primary"
          disabled={!content.trim() || isSubmitting}
        >
          {isSubmitting ? 'Salvando...' : 'Salvar Comentário'}
        </button>
      </div>
    </div>
  );
}
```

### 4.3 CommentSidebar.tsx

```typescript
interface CommentSidebarProps {
  targetType: CommentTargetType;
  targetId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function CommentSidebar({ targetType, targetId, isOpen, onClose }: CommentSidebarProps) {
  const [filter, setFilter] = useState<CommentFilter>({});
  const [showEditor, setShowEditor] = useState(false);
  
  const { data: comments, isLoading } = useComments(targetType, targetId, filter);
  useCommentRealtime(targetType, targetId);
  
  const unresolvedCount = comments?.results.filter(c => !c.resolvido).length || 0;
  const totalCount = comments?.results.length || 0;
  
  return (
    <div className={`comment-sidebar ${isOpen ? 'comment-sidebar--open' : ''}`}>
      <div className="comment-sidebar__header">
        <div className="comment-sidebar__title">
          <MessageSquare size={20} />
          <span>Comentários</span>
          <div className="comment-sidebar__counts">
            <span className="comment-count comment-count--unresolved">
              {unresolvedCount} pendentes
            </span>
            <span className="comment-count comment-count--total">
              {totalCount} total
            </span>
          </div>
        </div>
        
        <button 
          onClick={onClose}
          className="comment-sidebar__close"
        >
          <X size={20} />
        </button>
      </div>
      
      <div className="comment-sidebar__filters">
        <CommentFilters
          filter={filter}
          onChange={setFilter}
          totalCount={totalCount}
          unresolvedCount={unresolvedCount}
        />
      </div>
      
      <div className="comment-sidebar__content">
        {!showEditor && (
          <button 
            onClick={() => setShowEditor(true)}
            className="comment-sidebar__add-button"
          >
            <Plus size={16} />
            Adicionar comentário
          </button>
        )}
        
        {showEditor && (
          <CommentEditor
            targetType={targetType}
            targetId={targetId}
            onSave={() => setShowEditor(false)}
            onCancel={() => setShowEditor(false)}
          />
        )}
        
        {isLoading ? (
          <div className="comment-sidebar__loading">
            <Loader2 className="animate-spin" size={24} />
            <span>Carregando comentários...</span>
          </div>
        ) : (
          <CommentList
            comments={comments?.results || []}
            onReply={(comment) => {
              // Implementar lógica de resposta
            }}
            onResolve={(comment) => {
              // Implementar lógica de resolução
            }}
          />
        )}
      </div>
    </div>
  );
}
```

### 4.4 CommentInline.tsx

```typescript
interface CommentInlineProps {
  targetType: CommentTargetType;
  targetId: string;
  children: React.ReactNode;
}

export function CommentInline({ targetType, targetId, children }: CommentInlineProps) {
  const [selectedText, setSelectedText] = useState<string>('');
  const [selectionAnchor, setSelectionAnchor] = useState<CommentAnchor | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editorPosition, setEditorPosition] = useState<{ x: number; y: number } | null>(null);
  
  const { data: comments } = useComments(targetType, targetId);
  
  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) {
      setShowEditor(false);
      return;
    }
    
    const selectedText = selection.toString().trim();
    if (!selectedText) return;
    
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    setSelectedText(selectedText);
    setSelectionAnchor({
      type: 'text_selection',
      startOffset: range.startOffset,
      endOffset: range.endOffset,
      selectedText,
    });
    setEditorPosition({
      x: rect.left + rect.width / 2,
      y: rect.bottom + 10,
    });
    setShowEditor(true);
  };
  
  const renderCommentIndicators = () => {
    if (!comments?.results) return null;
    
    return comments.results.map(comment => {
      if (comment.anchor_json.type !== 'text_selection') return null;
      
      return (
        <CommentAnchor
          key={comment.id}
          comment={comment}
          onSelect={() => {
            // Scroll to comment or show details
          }}
        />
      );
    });
  };
  
  return (
    <div className="comment-inline-container">
      <div 
        className="comment-inline-content"
        onMouseUp={handleTextSelection}
      >
        {children}
        {renderCommentIndicators()}
      </div>
      
      {showEditor && editorPosition && (
        <div 
          className="comment-inline-editor"
          style={{
            position: 'fixed',
            left: editorPosition.x,
            top: editorPosition.y,
            zIndex: 1000,
          }}
        >
          <CommentEditor
            targetType={targetType}
            targetId={targetId}
            anchor={selectionAnchor || undefined}
            onSave={() => {
              setShowEditor(false);
              window.getSelection()?.removeAllRanges();
            }}
            onCancel={() => {
              setShowEditor(false);
              window.getSelection()?.removeAllRanges();
            }}
          />
        </div>
      )}
    </div>
  );
}
```

## 5. Integração com Páginas Existentes

### 5.1 TaskDetailPage.tsx

```typescript
// Adicionar sidebar de comentários
const [showComments, setShowComments] = useState(false);
const { data: comments } = useComments('resposta', `${tarefa.id}-${selectedGtId}`);
const unresolvedCount = comments?.results.filter(c => !c.resolvido).length || 0;

// No JSX:
<div className="task-detail__header">
  <button 
    onClick={() => setShowComments(!showComments)}
    className={`btn btn--secondary ${unresolvedCount > 0 ? 'btn--with-badge' : ''}`}
  >
    <MessageSquare size={16} />
    Comentários
    {unresolvedCount > 0 && (
      <span className="btn__badge">{unresolvedCount}</span>
    )}
  </button>
</div>

<CommentSidebar
  targetType="resposta"
  targetId={`${tarefa.id}-${selectedGtId}`}
  isOpen={showComments}
  onClose={() => setShowComments(false)}
/>
```

### 5.2 TextoUnicoPage.tsx

```typescript
// Envolver o editor com comentários inline
<CommentInline
  targetType="texto_unico"
  targetId={textoUnico?.id.toString() || ''}
>
  <RichTextEditor
    value={content}
    onChange={setContent}
    // ... outras props
  />
</CommentInline>

// Adicionar sidebar
<CommentSidebar
  targetType="texto_unico"
  targetId={textoUnico?.id.toString() || ''}
  isOpen={showComments}
  onClose={() => setShowComments(false)}
/>
```

### 5.3 QuadroPage.tsx

```typescript
// Adicionar comentários por célula
<QuadroCell
  cell={cell}
  onEdit={handleCellEdit}
  comments={getCellComments(cell.id)}
  onAddComment={(cellId) => {
    setSelectedCell(cellId);
    setShowCommentEditor(true);
  }}
/>

// Modal para comentários da célula
{showCommentEditor && selectedCell && (
  <Modal onClose={() => setShowCommentEditor(false)}>
    <CommentEditor
      targetType="quadro"
      targetId={quadro?.id.toString() || ''}
      anchor={{
        type: 'cell',
        cellId: selectedCell,
      }}
      onSave={() => setShowCommentEditor(false)}
      onCancel={() => setShowCommentEditor(false)}
    />
  </Modal>
)}
```

## 6. Roteamento

```typescript
// Não há rotas específicas para comentários, pois são integrados nas páginas existentes
// Mas podemos adicionar deep links para comentários específicos:

// router.tsx - adicionar parâmetros de query para comentários
{
  path: '/tarefas/:tarefaId',
  element: <ProtectedRoute><TaskDetailPage /></ProtectedRoute>,
  // Suporte a ?comment=123 para abrir comentário específico
},
```

## 7. Estilos CSS

### 7.1 CommentCard.css

```css
.comment-card {
  background: white;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.comment-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.comment-card--resolved {
  opacity: 0.7;
  background: #f8f9fa;
}

.comment-card--nested {
  margin-left: 24px;
  border-left: 3px solid #007bff;
  border-radius: 0 8px 8px 0;
}

.comment-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.comment-card__author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.comment-card__meta {
  display: flex;
  flex-direction: column;
}

.comment-card__author-name {
  font-weight: 600;
  font-size: 14px;
}

.comment-card__timestamp {
  font-size: 12px;
  color: #6c757d;
}

.comment-card__resolved-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #d1edff;
  color: #0c5460;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.comment-card__content {
  margin-bottom: 12px;
}

.comment-card__html-content {
  line-height: 1.5;
  color: #333;
}

.comment-card__mentions {
  margin-top: 8px;
  padding: 8px;
  background: #fff3cd;
  border-radius: 4px;
  font-size: 12px;
}

.comment-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.comment-action {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: #6c757d;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.comment-action:hover {
  background: #f8f9fa;
  color: #333;
}

.comment-action--resolve:hover {
  background: #d1edff;
  color: #0c5460;
}

.comment-action--delete:hover {
  background: #f8d7da;
  color: #721c24;
}

.comment-card__replies {
  margin-top: 16px;
  border-top: 1px solid #e1e5e9;
  padding-top: 16px;
}
```

### 7.2 CommentSidebar.css

```css
.comment-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  height: 100vh;
  background: white;
  border-left: 1px solid #e1e5e9;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
  transform: translateX(100%);
  transition: transform 0.3s ease;
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.comment-sidebar--open {
  transform: translateX(0);
}

.comment-sidebar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e1e5e9;
  background: #f8f9fa;
}

.comment-sidebar__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.comment-sidebar__counts {
  display: flex;
  gap: 8px;
  margin-left: 12px;
}

.comment-count {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.comment-count--unresolved {
  background: #fff3cd;
  color: #856404;
}

.comment-count--total {
  background: #e9ecef;
  color: #495057;
}

.comment-sidebar__close {
  border: none;
  background: transparent;
  color: #6c757d;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.comment-sidebar__close:hover {
  background: #e9ecef;
}

.comment-sidebar__filters {
  padding: 16px;
  border-bottom: 1px solid #e1e5e9;
}

.comment-sidebar__content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.comment-sidebar__add-button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border: 2px dashed #007bff;
  background: transparent;
  color: #007bff;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 16px;
  transition: all 0.2s ease;
}

.comment-sidebar__add-button:hover {
  background: #f0f8ff;
}

.comment-sidebar__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px;
  color: #6c757d;
}

@media (max-width: 768px) {
  .comment-sidebar {
    width: 100vw;
  }
}
```

### 7.3 CommentInline.css

```css
.comment-inline-container {
  position: relative;
}

.comment-inline-content {
  position: relative;
}

.comment-inline-editor {
  background: white;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 16px;
  min-width: 300px;
  max-width: 400px;
}

.comment-anchor {
  position: absolute;
  width: 20px;
  height: 20px;
  background: #007bff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  z-index: 10;
}

.comment-anchor:hover {
  background: #0056b3;
  transform: scale(1.1);
}

.comment-anchor--resolved {
  background: #6c757d;
}

.comment-highlight {
  background: rgba(255, 235, 59, 0.3);
  border-radius: 2px;
  cursor: pointer;
}

.comment-highlight:hover {
  background: rgba(255, 235, 59, 0.5);
}
```

## 8. WebSocket Integration

### 8.1 WebSocket Hook

```typescript
// useWebSocket.ts
export function useWebSocket() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const { user } = useAuth();
  
  useEffect(() => {
    if (!user) return;
    
    const newSocket = io('/comments', {
      auth: {
        token: getAuthToken(),
      },
    });
    
    newSocket.on('connect', () => {
      console.log('WebSocket conectado para comentários');
    });
    
    newSocket.on('disconnect', () => {
      console.log('WebSocket desconectado');
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.close();
    };
  }, [user]);
  
  return { socket };
}

// Função para broadcast de eventos
export function broadcastCommentEvent(type: string, comment: Comment) {
  // Esta função seria chamada pelo backend via WebSocket
  // Aqui apenas documentamos a estrutura do evento
}
```

## 9. Considerações de Performance

### 9.1 Otimizações

- **Virtual scrolling** para listas grandes de comentários
- **Debounce** em filtros e busca (300ms)
- **Lazy loading** de threads aninhadas
- **Memoização** de componentes pesados
- **Cache inteligente** via React Query

### 9.2 Real-time Optimization

- **Event batching** para múltiplas atualizações
- **Selective updates** apenas para comentários visíveis
- **Connection pooling** para WebSocket
- **Graceful degradation** se WebSocket falhar

## 10. Testes

### 10.1 Testes Unitários

- Hooks de React Query
- Componentes isolados
- Utilitários de ancoragem e menções
- Validações de formulário

### 10.2 Testes de Integração

- Fluxo completo de comentário
- WebSocket events
- Integração com páginas existentes
- Sistema de menções

### 10.3 Testes E2E

- Jornada completa do usuário
- Colaboração em tempo real
- Diferentes tipos de ancoragem
- Resolução de comentários

## 11. Deployment e Monitoramento

### 11.1 Feature Flags

- `ff.comments.enabled` - Habilita/desabilita sistema globalmente
- `ff.comments.realtime` - Controla atualizações em tempo real
- `ff.comments.mentions` - Sistema de menções
- `ff.comments.threading` - Threads aninhadas

### 11.2 Métricas

- Número de comentários criados por dia
- Tempo médio de resolução
- Taxa de engajamento por GT
- Performance de WebSocket (latência, reconexões)
- Erros de sincronização

O Sistema de Comentários está agora completamente especificado e pronto para implementação, seguindo as melhores práticas de arquitetura frontend e integração com o backend existente.