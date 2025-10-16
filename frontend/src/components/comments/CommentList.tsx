import { useState } from 'react';
import { MessageCircle, Search, Users, X } from 'lucide-react';
import { useComments, useCreateComment } from '@/hooks/useComments';
import { useTypingIndicators } from '@/hooks/useCommentRealtime';
import { CommentCard } from './CommentCard';
import { CommentEditor } from './CommentEditor';
import { CommentThread } from './CommentThread';
import { 
  CommentListProps, 
  CommentFilter,
  Comment 
} from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentList.css';

export function CommentList({
  targetType,
  targetId,
  showEditor = true,
  showFilters = true,
  showStats = true,
  groupByThread = true,
  className,
}: CommentListProps) {
  const [filter, setFilter] = useState<CommentFilter>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'resolved'>('newest');
  
  const { 
    comments, 
    isLoading, 
    error, 
    hasNextPage, 
    fetchNextPage,
    refetch 
  } = useComments(targetType, targetId, {
    ...filter,
    search: searchQuery || undefined,
  });

  const { createComment, isCreating } = useCreateComment();
  const typingUsers = useTypingIndicators(targetType, targetId);

  // Organizar comentários em threads se necessário
  const organizedComments = groupByThread 
    ? organizeIntoThreads(comments)
    : comments.filter(comment => !comment.parent_id);

  // Aplicar ordenação
  const sortedComments = [...organizedComments].sort((a, b) => {
    const dateA = new Date(getCommentDate(a)).getTime();
    const dateB = new Date(getCommentDate(b)).getTime();
    
    switch (sortBy) {
      case 'oldest':
        return dateA - dateB;
      case 'resolved': {
        const resolvedA = getCommentResolved(a) ? 1 : 0;
        const resolvedB = getCommentResolved(b) ? 1 : 0;
        return resolvedB - resolvedA;
      }
      case 'newest':
      default:
        return dateB - dateA;
    }
  });

  const handleCreateComment = async (content: string, mentions: number[]) => {
    try {
      await createComment({
        alvo_tipo: targetType,
        alvo_id: targetId,
        conteudo_html: content,
        mentions,
      });
    } catch (error) {
      console.error('Erro ao criar comentário:', error);
    }
  };

  const handleReply = async (parentId: number, content: string, mentions: number[]) => {
    try {
      await createComment({
        alvo_tipo: targetType,
        alvo_id: targetId,
        conteudo_html: content,
        mentions,
        parent_id: parentId,
      });
    } catch (error) {
      console.error('Erro ao responder comentário:', error);
    }
  };

  const getStats = () => {
    const total = comments.length;
    const unresolved = comments.filter(c => !c.resolvido).length;
    const resolved = comments.filter(c => c.resolvido).length;
    const authors = new Set(comments.map(c => c.autor.id)).size;
    
    return { total, unresolved, resolved, authors };
  };

  const stats = getStats();

  if (error) {
    return (
      <div className="comment-list-error">
        <MessageCircle className="h-12 w-12 comment-list-error-icon" />
        <p className="comment-list-error-text">Erro ao carregar comentários</p>
        <button onClick={() => refetch()} className="comment-list-retry-btn">
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className={cn('comment-list', className)}>
      {/* Estatísticas */}
      {showStats && (
        <div className="comment-list-stats">
          <div className="comment-list-stat">
            <MessageCircle className="h-4 w-4" />
            <span>{stats.total} comentários</span>
          </div>
          <div className="comment-list-separator" />
          <span className="comment-list-badge comment-list-badge--secondary">
            {stats.unresolved} pendentes
          </span>
          <span className="comment-list-badge comment-list-badge--outline">
            {stats.resolved} resolvidos
          </span>
          <div className="comment-list-participants">
            <Users className="h-3 w-3" />
            {stats.authors} participantes
          </div>
        </div>
      )}

      {/* Filtros e busca */}
      {showFilters && (
        <div className="comment-list-filters">
          <div className="comment-list-search-row">
            <div className="comment-list-search">
              <Search className="comment-list-search-icon h-4 w-4" />
              <input
                type="text"
                placeholder="Buscar comentários..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="comment-list-input"
              />
            </div>
            <select 
              value={sortBy} 
              onChange={(e) => setSortBy(e.target.value as any)}
              className="comment-list-select-trigger"
            >
              <option value="newest">Mais recentes</option>
              <option value="oldest">Mais antigos</option>
              <option value="resolved">Resolvidos primeiro</option>
            </select>
          </div>

          <div className="comment-list-filter-row">
            <select 
              value={filter.resolvido?.toString() || 'all'} 
              onChange={(e) => {
                const value = e.target.value;
                setFilter(prev => ({
                  ...prev,
                  resolvido: value === 'all' ? undefined : value === 'true'
                }));
              }}
              className="comment-list-select-trigger"
            >
              <option value="all">Todos</option>
              <option value="false">Pendentes</option>
              <option value="true">Resolvidos</option>
            </select>

            {(filter.resolvido !== undefined || searchQuery) && (
              <button
                onClick={() => {
                  setFilter({});
                  setSearchQuery('');
                }}
                className="comment-list-clear-btn"
              >
                <X className="h-4 w-4" />
                Limpar filtros
              </button>
            )}
          </div>
        </div>
      )}

      {/* Editor de novo comentário */}
      {showEditor && (
        <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px' }}>
          <CommentEditor
            onSubmit={handleCreateComment}
            placeholder="Adicionar comentário..."
            submitLabel="Comentar"
            isSubmitting={isCreating}
            targetType={targetType}
            targetId={targetId}
          />
        </div>
      )}

      {/* Indicadores de digitação */}
      {typingUsers.length > 0 && (
        <div className="comment-list-typing">
          <span className="comment-list-typing-dots">...</span>
          <span>
            {typingUsers.length === 1 
              ? `${typingUsers[0].userName} está digitando...`
              : `${typingUsers.length} pessoas estão digitando...`
            }
          </span>
        </div>
      )}

      {/* Lista de comentários */}
      <div className="comment-list-content">
        {isLoading && comments.length === 0 ? (
          <div className="comment-list-loading">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="comment-list-skeleton">
                <div className="comment-list-skeleton-item">
                  <div className="comment-list-skeleton-avatar" />
                  <div className="comment-list-skeleton-content">
                    <div className="comment-list-skeleton-line comment-list-skeleton-line--short" />
                    <div className="comment-list-skeleton-line comment-list-skeleton-line--long" />
                    <div className="comment-list-skeleton-line comment-list-skeleton-line--medium" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : sortedComments.length === 0 ? (
          <div className="comment-list-empty">
            <MessageCircle className="comment-list-empty-icon" />
            <p className="comment-list-empty-text">
              {searchQuery || filter.resolvido !== undefined 
                ? 'Nenhum comentário encontrado com os filtros aplicados'
                : 'Nenhum comentário ainda'
              }
            </p>
          </div>
        ) : (
          <>
            {sortedComments.map((item) => (
              groupByThread ? (
                <CommentThread
                  key={`thread-${item.parent.id}`}
                  thread={item}
                  onReply={handleReply}
                />
              ) : (
                <CommentCard
                  key={`comment-${item.id}`}
                  comment={item as Comment}
                  onReply={handleReply}
                />
              )
            ))}
            
            {hasNextPage && (
              <div className="comment-list-load-more">
                <button
                  className="comment-list-load-more-btn"
                  onClick={() => fetchNextPage()}
                  disabled={isLoading}
                >
                  {isLoading ? 'Carregando...' : 'Carregar mais'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Função auxiliar para organizar comentários em threads
function organizeIntoThreads(comments: Comment[]) {
  const parentComments = comments.filter(comment => !comment.parent_id);
  
  return parentComments.map(parent => {
    const replies = comments
      .filter(comment => comment.parent_id === parent.id)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    
    return {
      parent,
      replies,
      totalReplies: replies.length,
      unresolvedReplies: replies.filter(r => !r.resolvido).length,
    };
  });
}

// Funções auxiliares para ordenação
function getCommentDate(item: any): string {
  return item.parent ? item.parent.created_at : item.created_at;
}

function getCommentResolved(item: any): boolean {
  return item.parent ? item.parent.resolvido : item.resolvido;
}