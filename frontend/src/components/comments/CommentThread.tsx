import { useState } from 'react';
import { ChevronDown, ChevronRight, MessageCircle, Users } from 'lucide-react';
import { CommentCard } from './CommentCard';
import { CommentThreadProps } from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentThread.css';

export function CommentThread({
  thread,
  onReply,
  onEdit,
  onDelete,
  onResolve,
  onReopen,
  defaultExpanded = true,
  showReplyCount = true,
  className,
}: CommentThreadProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const { parent, replies, totalReplies, unresolvedReplies } = thread;

  const handleParentReply = (parentId: number, content: string, mentions: number[]) => {
    onReply?.(parentId, content, mentions);
  };

  const handleReplyToReply = (replyId: number, content: string, mentions: number[]) => {
    // Para respostas a respostas, ainda usamos o ID do comentário pai original
    onReply?.(parent.id, content, mentions);
  };

  return (
    <div className={cn('comment-thread', className)}>
      {/* Comentário principal */}
      <CommentCard
        comment={parent}
        onReply={handleParentReply}
        onEdit={onEdit}
        onDelete={onDelete}
        onResolve={onResolve}
        onReopen={onReopen}
        showReplies={false}
      />

      {/* Respostas */}
      {totalReplies > 0 && (
        <div className="comment-thread-replies">
          <div className="comment-thread-trigger">
            <button
              className="comment-thread-toggle"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              <div className="comment-thread-toggle-content">
                {isExpanded ? (
                  <ChevronDown className="comment-thread-toggle-icon" />
                ) : (
                  <ChevronRight className="comment-thread-toggle-icon" />
                )}
                <MessageCircle className="comment-thread-toggle-icon" />
                <span className="comment-thread-toggle-text">
                  {totalReplies} {totalReplies === 1 ? 'resposta' : 'respostas'}
                </span>
                {unresolvedReplies > 0 && (
                  <span className="comment-thread-badge comment-thread-badge--secondary">
                    {unresolvedReplies} pendentes
                  </span>
                )}
              </div>
            </button>

            {showReplyCount && !isExpanded && (
              <div className="comment-thread-participants">
                <Users className="comment-thread-participants-icon" />
                <span>
                  {new Set(replies.map(r => r.autor.id)).size} participantes
                </span>
              </div>
            )}
          </div>

          <div className={`comment-thread-content ${isExpanded ? 'comment-thread-content--expanded' : 'comment-thread-content--collapsed'}`}>
            {isExpanded && replies.map((reply, index) => (
              <CommentCard
                key={reply.id}
                comment={reply}
                onReply={handleReplyToReply}
                onEdit={onEdit}
                onDelete={onDelete}
                onResolve={onResolve}
                onReopen={onReopen}
                isReply={true}
                showReplies={false}
                className={cn(
                  'comment-thread-reply',
                  index === replies.length - 1 && 'mb-0'
                )}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}