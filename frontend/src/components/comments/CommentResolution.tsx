import { useState } from 'react';
import { Check, AlertCircle, Clock, User, Calendar, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useUpdateComment } from '@/hooks/useComments';
import type { Comment, CommentStatus } from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentResolution.css';

interface CommentResolutionProps {
  comment: Comment;
  onStatusChange?: (commentId: string, status: CommentStatus, reason?: string) => void;
  className?: string;
}

interface ResolutionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  action: 'resolve' | 'reopen';
  onConfirm: (reason?: string) => void;
  isLoading?: boolean;
}

function ResolutionDialog({ 
  isOpen, 
  onOpenChange, 
  action, 
  onConfirm, 
  isLoading = false 
}: ResolutionDialogProps) {
  const [reason, setReason] = useState('');

  const handleConfirm = () => {
    onConfirm(reason.trim() || undefined);
    setReason('');
  };

  const handleCancel = () => {
    setReason('');
    onOpenChange(false);
  };

  if (!isOpen) return null;

  return (
    <div className="resolution-dialog-overlay" onClick={(e) => e.target === e.currentTarget && onOpenChange(false)}>
      <div className="resolution-dialog">
        <button 
          className="resolution-dialog-close"
          onClick={() => onOpenChange(false)}
          disabled={isLoading}
        >
          <X className="h-4 w-4" />
        </button>
        
        <div className="resolution-dialog-header">
          <h3 className="resolution-dialog-title">
            {action === 'resolve' ? 'Resolver Comentário' : 'Reabrir Comentário'}
          </h3>
          <p className="resolution-dialog-description">
            {action === 'resolve' 
              ? 'Marcar este comentário como resolvido. Você pode adicionar uma explicação opcional.'
              : 'Reabrir este comentário para discussão adicional. Você pode explicar o motivo.'
            }
          </p>
        </div>
        
        <div className="resolution-dialog-content">
          <div className="resolution-form-group">
            <label htmlFor="reason" className="resolution-form-label">
              {action === 'resolve' ? 'Motivo da resolução (opcional)' : 'Motivo da reabertura (opcional)'}
            </label>
            <textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={
                action === 'resolve' 
                  ? 'Ex: Problema foi corrigido na versão 2.1.0'
                  : 'Ex: Problema ainda persiste, precisa de mais investigação'
              }
              className="resolution-textarea"
              disabled={isLoading}
            />
          </div>
        </div>
        
        <div className="resolution-dialog-footer">
          <button
            type="button"
            className="resolution-dialog-btn resolution-dialog-btn--outline"
            onClick={handleCancel}
            disabled={isLoading}
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            className={cn(
              'resolution-dialog-btn',
              action === 'resolve' ? 'resolution-dialog-btn--resolve' : 'resolution-dialog-btn--reopen'
            )}
          >
            {isLoading ? (
              'Processando...'
            ) : (
              <>
                {action === 'resolve' ? (
                  <>
                    <Check className="h-4 w-4" />
                    Resolver
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    Reabrir
                  </>
                )}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export function CommentResolution({ 
  comment, 
  onStatusChange, 
  className 
}: CommentResolutionProps) {
  const [showResolveDialog, setShowResolveDialog] = useState(false);
  const [showReopenDialog, setShowReopenDialog] = useState(false);
  const { user } = useAuth();
  const updateCommentMutation = useUpdateComment();

  // Verificar permissões
  const canResolve = user && (
    user.id === comment.autor_id || 
    user.role === 'admin' || 
    user.role === 'moderator'
  );

  const canReopen = user && (
    user.id === comment.autor_id || 
    user.role === 'admin' || 
    user.role === 'moderator' ||
    comment.status === 'resolvido'
  );

  const handleResolve = async (reason?: string) => {
    try {
      await updateCommentMutation.mutateAsync({
        id: comment.id,
        status: 'resolvido',
        resolution_reason: reason,
        resolved_by: user?.id,
        resolved_at: new Date().toISOString(),
      });
      
      onStatusChange?.(comment.id, 'resolvido', reason);
      setShowResolveDialog(false);
    } catch (error) {
      console.error('Erro ao resolver comentário:', error);
    }
  };

  const handleReopen = async (reason?: string) => {
    try {
      await updateCommentMutation.mutateAsync({
        id: comment.id,
        status: 'aberto',
        resolution_reason: reason,
        resolved_by: null,
        resolved_at: null,
      });
      
      onStatusChange?.(comment.id, 'aberto', reason);
      setShowReopenDialog(false);
    } catch (error) {
      console.error('Erro ao reabrir comentário:', error);
    }
  };

  const getStatusInfo = () => {
    switch (comment.status) {
      case 'resolvido': {
        return {
          icon: Check,
          label: 'Resolvido',
          color: 'bg-green-100 text-green-800 border-green-200',
          description: 'Este comentário foi marcado como resolvido'
        };
      }
      case 'aberto': {
        return {
          icon: AlertCircle,
          label: 'Aberto',
          color: 'bg-blue-100 text-blue-800 border-blue-200',
          description: 'Este comentário está aguardando resolução'
        };
      }
      case 'em_andamento': {
        return {
          icon: Clock,
          label: 'Em Andamento',
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          description: 'Este comentário está sendo trabalhado'
        };
      }
      default: {
        return {
          icon: AlertCircle,
          label: 'Aberto',
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          description: 'Status do comentário'
        };
      }
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  return (
    <div className={cn('comment-resolution', className)}>
      {/* Status atual */}
      <div className="resolution-status">
        <span className={cn('status-badge', {
          'status-badge--resolved': comment.status === 'resolvido',
          'status-badge--open': comment.status === 'aberto',
          'status-badge--pending': comment.status === 'em_andamento'
        })}>
          <StatusIcon className="h-3 w-3" />
          {statusInfo.label}
        </span>
        
        {/* Botões de ação */}
        <div className="resolution-actions">
          {comment.status !== 'resolvido' && canResolve && (
            <button
              onClick={() => setShowResolveDialog(true)}
              className="resolution-btn resolution-btn--resolve"
              disabled={updateCommentMutation.isPending}
            >
              <Check className="h-4 w-4" />
              Resolver
            </button>
          )}
          
          {comment.status === 'resolvido' && canReopen && (
            <button
              onClick={() => setShowReopenDialog(true)}
              className="resolution-btn resolution-btn--reopen"
              disabled={updateCommentMutation.isPending}
            >
              <AlertCircle className="h-4 w-4" />
              Reabrir
            </button>
          )}
        </div>
      </div>

      {/* Informações de resolução */}
      {comment.status === 'resolvido' && comment.resolved_by && (
        <div className="resolution-info">
          <div className="resolution-meta">
            <div className="resolution-meta-item">
              <User className="h-3 w-3" />
              <span>Resolvido por {comment.resolved_by_name || 'Usuário'}</span>
            </div>
            
            {comment.resolved_at && (
              <div className="resolution-meta-item">
                <Calendar className="h-3 w-3" />
                <span>{new Date(comment.resolved_at).toLocaleString('pt-BR')}</span>
              </div>
            )}
          </div>
          
          {comment.resolution_reason && (
            <div className="resolution-reason">
              <strong>Motivo:</strong> {comment.resolution_reason}
            </div>
          )}
        </div>
      )}

      {/* Diálogos de confirmação */}
      <ResolutionDialog
        isOpen={showResolveDialog}
        onOpenChange={setShowResolveDialog}
        action="resolve"
        onConfirm={handleResolve}
        isLoading={updateCommentMutation.isPending}
      />
      
      <ResolutionDialog
        isOpen={showReopenDialog}
        onOpenChange={setShowReopenDialog}
        action="reopen"
        onConfirm={handleReopen}
        isLoading={updateCommentMutation.isPending}
      />
    </div>
  );
}

export default CommentResolution;