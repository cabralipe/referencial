import { useState } from 'react';
import { MoreVertical, Reply, Edit, Trash2, User, Check, Clock } from 'lucide-react';
import { CommentEditor } from './CommentEditor';
import { CommentResolution } from './CommentResolution';
import { useAuth } from '@/context/AuthContext';
import { useUpdateComment, useDeleteComment } from '@/hooks/useComments';
import type { Comment, CommentCardProps } from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentCard.css';

// Helper function to format relative time
function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const commentDate = new Date(date);
  const diffInSeconds = Math.floor((now.getTime() - commentDate.getTime()) / 1000);
  
  if (diffInSeconds < 60) {
    return 'agora mesmo';
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `há ${minutes} minuto${minutes > 1 ? 's' : ''}`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `há ${hours} hora${hours > 1 ? 's' : ''}`;
  } else if (diffInSeconds < 2592000) {
    const days = Math.floor(diffInSeconds / 86400);
    return `há ${days} dia${days > 1 ? 's' : ''}`;
  } else {
    return commentDate.toLocaleDateString('pt-BR');
  }
}

export function CommentCard({
  comment,
  onReply,
  onEdit,
  onDelete,
  onResolve,
  onReopen,
  isReply = false,
  className,
}: CommentCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showReplyEditor, setShowReplyEditor] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  
  const { user } = useAuth();
  const { mutateAsync: updateComment, isPending: isUpdating } = useUpdateComment();
  const { mutateAsync: deleteComment, isPending: isDeleting } = useDeleteComment();

  // Verificar permissões
  const canEdit = user?.id === comment.autor.id;
  const canDelete = user?.id === comment.autor.id || user?.role === 'admin';

  const handleEdit = async (content: string, mentions: number[]) => {
    try {
      await updateComment({
        id: comment.id,
        data: {
          conteudo_html: content,
          mentions_ids: mentions,
        },
        etag: comment.etag,
      });
      setIsEditing(false);
      onEdit?.(comment.id, content);
    } catch (error) {
      console.error('Erro ao editar comentário:', error);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Tem certeza que deseja deletar este comentário?')) {
      try {
        await deleteComment({ id: comment.id, etag: comment.etag });
        onDelete?.(comment.id);
      } catch (error) {
        console.error('Erro ao deletar comentário:', error);
      }
    }
  };

  const handleStatusChange = (commentId: string, status: any) => {
    if (status === 'resolvido') {
      onResolve?.(commentId);
    } else if (status === 'aberto') {
      onReopen?.(commentId);
    }
  };

  const handleReply = (content: string, mentions: number[]) => {
    onReply?.(comment.id, content, mentions);
    setShowReplyEditor(false);
  };

  const formatDate = (date: string) => {
    return formatRelativeTime(date);
  };

  const getAuthorInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div 
      id={`comment-${comment.id}`}
      className={cn(
        'comment-card',
        comment.resolvido && 'resolved',
        isReply && 'nested',
        className
      )}
    >
      <div className="comment-card__header">
        <div className="comment-card__author">
          <div className="comment-card__avatar">
            {comment.autor.avatar ? (
              <img src={comment.autor.avatar} alt={comment.autor.nome} />
            ) : (
              getAuthorInitials(comment.autor.nome)
            )}
          </div>
          
          <div className="comment-card__author-info">
            <div className="comment-card__author-name">
              {comment.autor.nome}
              {comment.resolvido && (
                <span className="comment-card__badge comment-card__badge--resolved">
                  <Check className="h-3 w-3" />
                  Resolvido
                </span>
              )}
            </div>
            
            <div className="comment-card__timestamp">
              <Clock className="h-3 w-3" />
              <span>{formatDate(comment.created_at)}</span>
              {comment.updated_at !== comment.created_at && (
                <span>(editado)</span>
              )}
            </div>
          </div>
        </div>

        <div className="comment-card__actions">
          {comment.resolvido && comment.resolvido_por && (
            <div className="comment-card__resolved-by">
              Resolvido por {comment.resolvido_por.nome}
            </div>
          )}
          
          <div className="comment-card__dropdown">
            <button 
              className="comment-card__action-button"
              onClick={() => setShowDropdown(!showDropdown)}
            >
              <MoreVertical className="h-4 w-4" />
            </button>
            
            {showDropdown && (
              <div className="comment-card__dropdown-menu">
                <button 
                  className="comment-card__dropdown-item"
                  onClick={() => {
                    setShowReplyEditor(true);
                    setShowDropdown(false);
                  }}
                >
                  <Reply className="h-4 w-4" />
                  Responder
                </button>
                
                {canEdit && (
                  <button 
                    className="comment-card__dropdown-item"
                    onClick={() => {
                      setIsEditing(true);
                      setShowDropdown(false);
                    }}
                  >
                    <Edit className="h-4 w-4" />
                    Editar
                  </button>
                )}
                
                {canDelete && (
                  <button 
                    className="comment-card__dropdown-item danger"
                    onClick={() => {
                      handleDelete();
                      setShowDropdown(false);
                    }}
                    disabled={isDeleting}
                  >
                    <Trash2 className="h-4 w-4" />
                    Deletar
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="comment-card__content">
        {isEditing ? (
          <div className="comment-card__editor">
            <CommentEditor
              initialContent={comment.conteudo_html}
              initialMentions={comment.mentions_ids}
              onSubmit={handleEdit}
              onCancel={() => setIsEditing(false)}
              placeholder="Editar comentário..."
              submitLabel="Salvar"
              isSubmitting={isUpdating}
            />
          </div>
        ) : (
          <div>
            <div 
              className="comment-card__text"
              dangerouslySetInnerHTML={{ __html: comment.conteudo_html }}
            />
            
            {comment.anchor_json && (
              <div className="comment-card__context">
                <strong>Contexto:</strong> {comment.anchor_json.selectedText}
              </div>
            )}
            
            {comment.mentions && comment.mentions.length > 0 && (
              <div className="comment-card__mentions">
                {comment.mentions.map((mention) => (
                  <span key={mention.id} className="comment-card__mention">
                    <User className="h-3 w-3" />
                    {mention.nome}
                  </span>
                ))}
              </div>
            )}
            
            {/* Resolution controls */}
            <CommentResolution
              comment={comment}
              onStatusChange={handleStatusChange}
              className="comment-card__resolution"
            />
          </div>
        )}

        {showReplyEditor && (
          <div className="comment-card__editor">
            <CommentEditor
              onSubmit={handleReply}
              onCancel={() => setShowReplyEditor(false)}
              placeholder="Escrever resposta..."
              submitLabel="Responder"
              compact
            />
          </div>
        )}
      </div>
    </div>
  );
}