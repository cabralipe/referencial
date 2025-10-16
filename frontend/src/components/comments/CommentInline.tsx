import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X } from 'lucide-react';
import { CommentEditor } from './CommentEditor';
import { CommentList } from './CommentList';
import { useComments, useCreateComment } from '@/hooks/useComments';
import { 
  CommentInlineProps, 
  CommentAnchor, 
  CommentTargetType,
  Comment 
} from '@/types/comments';
import { cn } from '@/lib/utils';
import './CommentInline.css';

export function CommentInline({
  targetType,
  targetId,
  children,
  enableSelection = true,
  showIndicators = true,
  className,
}: CommentInlineProps) {
  const [selectedText, setSelectedText] = useState('');
  const [showCommentEditor, setShowCommentEditor] = useState(false);
  const [activeAnchor, setActiveAnchor] = useState<CommentAnchor | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { comments } = useComments(targetType, targetId);
  const { createComment, isCreating } = useCreateComment();

  // Filtrar comentários que têm âncoras (texto selecionado)
  const anchoredComments = comments.filter(comment => comment.anchor_json);

  const handleTextSelection = useCallback(() => {
    if (!enableSelection) return;

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const text = selection.toString().trim();

    if (text.length > 0 && containerRef.current?.contains(range.commonAncestorContainer)) {
      setSelectedText(text);
      
      // Criar âncora com informações de posição
      const anchor: CommentAnchor = {
        selectedText: text,
        startOffset: range.startOffset,
        endOffset: range.endOffset,
        startContainer: getNodePath(range.startContainer),
        endContainer: getNodePath(range.endContainer),
        timestamp: new Date().toISOString(),
      };
      
      setActiveAnchor(anchor);
      setShowCommentEditor(true);
    } else {
      clearSelection();
    }
  }, [enableSelection]);

  const clearSelection = () => {
    setSelectedText('');
    setActiveAnchor(null);
    setShowCommentEditor(false);
    window.getSelection()?.removeAllRanges();
  };

  const handleCreateComment = async (content: string, mentions: number[]) => {
    if (!activeAnchor) return;

    try {
      await createComment({
        alvo_tipo: targetType,
        alvo_id: targetId,
        conteudo_html: content,
        mentions,
        anchor_json: activeAnchor,
      });
      
      clearSelection();
    } catch (error) {
      console.error('Erro ao criar comentário:', error);
    }
  };

  // Adicionar event listeners para seleção de texto
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMouseUp = () => {
      setTimeout(handleTextSelection, 10);
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        clearSelection();
      }
    };

    container.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('keyup', handleKeyUp);

    return () => {
      container.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleTextSelection]);

  // Renderizar indicadores de comentários existentes
  const renderCommentIndicators = () => {
    if (!showIndicators || !containerRef.current) return null;

    return anchoredComments.map((comment) => {
      if (!comment.anchor_json) return null;

      try {
        const range = recreateRange(comment.anchor_json, containerRef.current!);
        if (!range) return null;

        const rect = range.getBoundingClientRect();
        const containerRect = containerRef.current!.getBoundingClientRect();

        const top = rect.top - containerRect.top;
        const left = rect.right - containerRect.left + 5;

        return (
          <CommentIndicator
            key={comment.id}
            comment={comment}
            style={{
              position: 'absolute',
              top: `${top}px`,
              left: `${left}px`,
              zIndex: 10,
            }}
          />
        );
      } catch (error) {
        console.warn('Erro ao renderizar indicador de comentário:', error);
        return null;
      }
    });
  };

  return (
    <div 
      ref={containerRef}
      className={cn('relative', className)}
      style={{ userSelect: enableSelection ? 'text' : 'none' }}
    >
      {children}
      
      {/* Indicadores de comentários */}
      {renderCommentIndicators()}

      {/* Editor de comentário para texto selecionado */}
      {showCommentEditor && activeAnchor && (
        <div className="comment-inline-overlay" onClick={clearSelection}>
          <div 
            className="comment-inline-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="comment-inline-modal-header">
              <h4 className="comment-inline-modal-title">Comentar texto selecionado</h4>
              <button
                className="comment-inline-modal-close"
                onClick={clearSelection}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="comment-inline-modal-quote">
              &quot;{selectedText}&quot;
            </div>
            
            <CommentEditor
              onSubmit={handleCreateComment}
              onCancel={clearSelection}
              placeholder="Comentar sobre este texto..."
              submitLabel="Comentar"
              isSubmitting={isCreating}
              targetType={targetType}
              targetId={targetId}
              compact
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Componente para indicadores de comentários
function CommentIndicator({ 
  comment, 
  style 
}: { 
  comment: Comment; 
  style: React.CSSProperties;
}) {
  const [showComments, setShowComments] = useState(false);

  return (
    <div className="comment-indicator" style={style}>
      <button
        className="comment-indicator-trigger"
        onClick={() => setShowComments(!showComments)}
      >
        <MessageCircle className="comment-indicator-trigger-icon" />
      </button>
      
      {showComments && (
        <>
          <div 
            className="comment-inline-overlay" 
            onClick={() => setShowComments(false)}
          />
          <div className="comment-indicator-popover">
            <div className="comment-indicator-popover-header">
              <div className="comment-indicator-popover-title">
                <MessageCircle className="h-4 w-4" />
                <span className="comment-indicator-popover-title-text">Comentários</span>
                <span className="comment-indicator-popover-badge">
                  Texto selecionado
                </span>
              </div>
              {comment.anchor_json && (
                <div className="comment-indicator-popover-quote">
                  &quot;{comment.anchor_json.selectedText}&quot;
                </div>
              )}
            </div>
            <div className="comment-indicator-popover-content">
              <CommentList
                targetType={comment.alvo_tipo as CommentTargetType}
                targetId={comment.alvo_id}
                showEditor={true}
                showFilters={false}
                showStats={false}
                groupByThread={true}
                className="p-3"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Utilitários para trabalhar com ranges de texto

function getNodePath(node: Node): string[] {
  const path: string[] = [];
  let current = node;

  while (current && current.nodeType !== Node.DOCUMENT_NODE) {
    if (current.parentNode) {
      const siblings = Array.from(current.parentNode.childNodes);
      const index = siblings.indexOf(current);
      path.unshift(`${current.nodeName}:${index}`);
    }
    current = current.parentNode!;
  }

  return path;
}

function recreateRange(anchor: CommentAnchor, container: HTMLElement): Range | null {
  try {
    const range = document.createRange();
    
    const startNode = findNodeByPath(anchor.startContainer, container);
    const endNode = findNodeByPath(anchor.endContainer, container);
    
    if (!startNode || !endNode) return null;
    
    range.setStart(startNode, anchor.startOffset);
    range.setEnd(endNode, anchor.endOffset);
    
    // Verificar se o texto ainda corresponde
    if (range.toString() === anchor.selectedText) {
      return range;
    }
    
    return null;
  } catch (error) {
    console.warn('Erro ao recriar range:', error);
    return null;
  }
}

function findNodeByPath(path: string[], container: HTMLElement): Node | null {
  let current: Node = container;
  
  for (const segment of path) {
    const [nodeName, indexStr] = segment.split(':');
    const index = parseInt(indexStr, 10);
    
    if (current.childNodes.length <= index) return null;
    
    current = current.childNodes[index];
    
    if (current.nodeName !== nodeName) return null;
  }
  
  return current;
}

// Hook para usar o sistema de comentários inline
export function useCommentInline(targetType: CommentTargetType, targetId: string) {
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const { comments } = useComments(targetType, targetId);
  
  const anchoredComments = comments.filter(comment => comment.anchor_json);
  const inlineCommentsCount = anchoredComments.length;
  
  const toggleSelectionMode = () => setIsSelectionMode(!isSelectionMode);
  const enableSelectionMode = () => setIsSelectionMode(true);
  const disableSelectionMode = () => setIsSelectionMode(false);
  
  return {
    isSelectionMode,
    inlineCommentsCount,
    anchoredComments,
    toggleSelectionMode,
    enableSelectionMode,
    disableSelectionMode,
  };
}