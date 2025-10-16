import { useState } from 'react';
import { X, Filter, MessageCircle, Pin, PinOff, Minimize2, Maximize2 } from 'lucide-react';
import { CommentList } from './CommentList';
import { useComments } from '@/hooks/useComments';
import { useCommentRealtime } from '@/hooks/useCommentRealtime';
import type { CommentTargetType, CommentSidebarProps } from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentSidebar.css';

export function CommentSidebar({
  targetType,
  targetId,
  isOpen,
  onOpenChange,
  position = 'right',
  mode = 'sidebar',
  showTrigger = true,
  isPinned = false,
  onPinChange,
  className,
}: CommentSidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  
  const { comments } = useComments(targetType, targetId);
  const { isConnected } = useCommentRealtime(targetType, targetId);

  const unresolvedCount = comments.filter(c => !c.resolvido).length;
  const totalCount = comments.length;

  const SidebarContent = () => (
    <div className="comment-sidebar">
      {/* Header */}
      <div className="comment-sidebar-header">
        <div className="comment-sidebar-title">
          <MessageCircle className="h-5 w-5" />
          <h3 className="comment-sidebar-title-text">Comentários</h3>
          {totalCount > 0 && (
            <span className="comment-sidebar-badge comment-sidebar-badge--secondary">
              {totalCount}
            </span>
          )}
          {unresolvedCount > 0 && (
            <span className="comment-sidebar-badge comment-sidebar-badge--destructive">
              {unresolvedCount} pendentes
            </span>
          )}
        </div>

        <div className="comment-sidebar-actions">
          {/* Indicador de conexão real-time */}
          <div className="comment-sidebar-btn">
            <div className={cn(
              'comment-sidebar-connection',
              isConnected ? 'comment-sidebar-connection--connected' : 'comment-sidebar-connection--disconnected'
            )} />
            <div className="comment-sidebar-tooltip">
              {isConnected ? 'Conectado - atualizações em tempo real' : 'Desconectado'}
            </div>
          </div>

          {/* Botão de pin (apenas no modo sidebar) */}
          {mode === 'sidebar' && (
            <button
              onClick={() => setIsPinned(!isPinned)}
              className={cn(
                'comment-sidebar-btn',
                isPinned && 'comment-sidebar-btn--active'
              )}
            >
              <Pin className="comment-sidebar-btn-icon" />
              <div className="comment-sidebar-tooltip">
                {isPinned ? 'Desafixar sidebar' : 'Fixar sidebar'}
              </div>
            </button>
          )}

          {/* Botão de expandir/colapsar */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="comment-sidebar-btn"
          >
            {isExpanded ? (
              <ChevronLeft className="comment-sidebar-btn-icon" />
            ) : (
              <ChevronRight className="comment-sidebar-btn-icon" />
            )}
            <div className="comment-sidebar-tooltip">
              {isExpanded ? 'Colapsar' : 'Expandir'}
            </div>
          </button>

          {/* Botão de fechar (apenas no modo modal) */}
          {mode === 'modal' && (
            <button
              onClick={onClose}
              className="comment-sidebar-btn"
            >
              <X className="comment-sidebar-btn-icon" />
            </button>
          )}
        </div>
      </div>

      {/* Conteúdo */}
      <div className="comment-sidebar-content">
        <CommentList
          documentId={documentId}
          anchorId={anchorId}
          filters={filters}
          onFiltersChange={onFiltersChange}
        />
      </div>
    </div>
  );

  // Renderização baseada no modo
  if (mode === 'sidebar') {
    return (
      <div className={cn(
        'comment-sidebar',
        isExpanded ? 'comment-sidebar--expanded' : 'comment-sidebar--collapsed',
        !isOpen && 'comment-sidebar--hidden',
        className
      )}>
        <SidebarContent />
      </div>
    );
  }

  // Modo modal
  return (
    <>
      {isOpen && (
        <div className="comment-sidebar-overlay" onClick={onClose} />
      )}
      <div className={cn(
        'comment-sidebar-modal',
        isOpen && 'comment-sidebar-modal--open',
        isExpanded && 'comment-sidebar-modal--expanded'
      )}>
        <SidebarContent />
      </div>
    </>
  );
}

// Componente de trigger para abrir o sidebar
export const CommentSidebarTrigger: React.FC<{
  children?: React.ReactNode;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}> = ({ 
  children, 
  variant = 'outline', 
  size = 'sm', 
  className,
  onClick 
}) => {
  return (
    <button 
      className={cn(
        'comment-sidebar-trigger',
        variant === 'ghost' && 'comment-sidebar-trigger--ghost',
        variant === 'default' && 'comment-sidebar-trigger--default',
        className
      )}
      onClick={onClick}
    >
      {children || (
        <>
          <MessageCircle className="comment-sidebar-trigger-icon" />
          Comentários
        </>
      )}
    </button>
  );
};

// Hook para controlar o estado do sidebar
export function useCommentSidebar(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [isPinned, setIsPinned] = useState(false);

  const toggle = () => setIsOpen(!isOpen);
  const open = () => setIsOpen(true);
  const close = () => setIsOpen(false);
  const pin = () => setIsPinned(true);
  const unpin = () => setIsPinned(false);
  const togglePin = () => setIsPinned(!isPinned);

  return {
    isOpen,
    isPinned,
    toggle,
    open,
    close,
    pin,
    unpin,
    togglePin,
    setIsOpen,
    setIsPinned,
  };
}