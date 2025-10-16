import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, X } from 'lucide-react';
import { CommentMentions } from './CommentMentions';
import { useCommentRealtime } from '@/hooks/useCommentRealtime';
import type { CommentEditorProps } from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentEditor.css';

export function CommentEditor({
  initialContent = '',
  initialMentions = [],
  onSubmit,
  onCancel,
  placeholder = 'Escrever comentário...',
  submitLabel = 'Comentar',
  isSubmitting = false,
  compact = false,
  targetType,
  targetId,
  className,
}: CommentEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [mentions, setMentions] = useState<number[]>(initialMentions);
  const [isTyping, setIsTyping] = useState(false);
  
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Real-time typing indicators
  const { sendTypingIndicator, sendStoppedTypingIndicator } = useCommentRealtime(
    targetType || 'resposta',
    targetId || '0',
    { autoConnect: !!targetType && !!targetId }
  );

  const handleTyping = useCallback(() => {
    if (!isTyping) {
      setIsTyping(true);
      sendTypingIndicator();
    }

    // Reset timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      sendStoppedTypingIndicator();
    }, 1000);
  }, [isTyping, sendTypingIndicator, sendStoppedTypingIndicator]);

  const handleContentChange = (newContent: string, newMentions: number[]) => {
    setContent(newContent);
    setMentions(newMentions);
    handleTyping();
  };

  const handleSubmit = () => {
    if (!content.trim()) return;
    
    // Converter texto simples para HTML básico
    const htmlContent = content
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    onSubmit(htmlContent, mentions);
    
    // Limpar formulário
    setContent('');
    setMentions([]);
  };

  const handleCancel = () => {
    setContent(initialContent);
    setMentions(initialMentions);
    onCancel?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Mock data para usuários mencionados
  const mockUsers = [
    { id: 1, nome: 'João Silva', email: 'joao@example.com', avatar: '' },
    { id: 2, nome: 'Maria Santos', email: 'maria@example.com', avatar: '' },
    { id: 3, nome: 'Pedro Costa', email: 'pedro@example.com', avatar: '' },
  ];

  const getMentionedUsers = () => {
    return mockUsers.filter(user => mentions.includes(user.id));
  };

  // Cleanup typing timeout
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={cn('comment-editor-container', className)}>
      <CommentMentions
        value={content}
        onChange={handleContentChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isSubmitting}
        className={cn(
          'comment-editor__input',
          compact && 'comment-editor__input--compact'
        )}
      />

      {/* Usuários mencionados */}
      {getMentionedUsers().length > 0 && (
        <div className="comment-editor__mentions">
          <span className="comment-editor__mentions-label">Mencionando:</span>
          {getMentionedUsers().map((user) => (
            <span key={user.id} className="comment-editor__mention-badge">
              {user.nome}
              <button
                type="button"
                className="comment-editor__mention-remove"
                onClick={() => setMentions(prev => prev.filter(id => id !== user.id))}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Botões de ação */}
      <div className="comment-editor__footer">
        <div className="comment-editor__hint">
          {compact ? 'Ctrl+Enter para enviar' : 'Use @ para mencionar usuários'}
        </div>
        
        <div className="comment-editor__actions">
          {onCancel && (
            <button
              type="button"
              className="comment-editor__cancel"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              Cancelar
            </button>
          )}
          <button
            type="button"
            className="comment-editor__submit"
            onClick={handleSubmit}
            disabled={!content.trim() || isSubmitting}
          >
            {isSubmitting ? (
              'Enviando...'
            ) : (
              <>
                <Send className="h-4 w-4" />
                {submitLabel}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}