import { useEffect, useRef, useState } from 'react';
import type { CelulaQuadro, QuadroTemplate } from '@/api/types';
import { isCellFixed, getFixedCellValue, getCellStyles } from '@/utils/quadroTemplates';

interface QuadroCellProps {
  celula: CelulaQuadro | null;
  linha: number;
  coluna: number;
  template: QuadroTemplate;
  isEditing: boolean;
  onStartEdit: () => void;
  onFinishEdit: (valor: string) => void;
  onOpenComments?: (linha: number, coluna: number) => void;
  readonly?: boolean;
}

export function QuadroCell({
  celula,
  linha,
  coluna,
  template,
  isEditing,
  onStartEdit,
  onFinishEdit,
  onOpenComments,
  readonly = false,
}: QuadroCellProps) {
  const [valor, setValor] = useState(celula?.valor_html || '');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const isFixed = isCellFixed(template, linha, coluna);
  const fixedValue = getFixedCellValue(template, linha, coluna);
  const cellStyles = getCellStyles(template, linha, coluna);
  
  // Update local value when celula changes
  useEffect(() => {
    if (isFixed && fixedValue) {
      setValor(fixedValue);
    } else {
      setValor(celula?.valor_html || '');
    }
  }, [celula?.valor_html, isFixed, fixedValue]);

  // Focus and select text when editing starts
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

  const handleClick = () => {
    if (!readonly && !isFixed) {
      onStartEdit();
    }
  };

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  useEffect(() => {
    if (isEditing) {
      adjustTextareaHeight();
    }
  }, [isEditing, valor]);

  const cellClasses = [
    'quadro-cell',
    isEditing && 'editing',
    !readonly && !isFixed && 'editable',
    readonly && 'readonly',
    isFixed && 'fixed',
  ].filter(Boolean).join(' ');

  if (isEditing && !isFixed) {
    return (
      <div 
        className={cellClasses}
        style={cellStyles}
      >
        <textarea
          ref={textareaRef}
          value={valor}
          onChange={(e) => {
            setValor(e.target.value);
            adjustTextareaHeight();
          }}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          className="cell-editor"
          placeholder="Digite o conteúdo..."
          rows={1}
        />
      </div>
    );
  }

  const displayValue = isFixed && fixedValue ? fixedValue : (celula?.valor_html || '');

  return (
    <div
      className={cellClasses}
      onClick={handleClick}
      title={!readonly && !isFixed ? 'Clique para editar' : undefined}
      style={cellStyles}
    >
      {displayValue ? (
        <div
          className="cell-content"
          dangerouslySetInnerHTML={{ __html: displayValue }}
        />
      ) : (
        <div className="cell-placeholder">
          {readonly || isFixed ? '' : 'Clique para adicionar conteúdo'}
        </div>
      )}
      
      {onOpenComments && (
        <button
          className="cell-comment-button"
          onClick={(e) => {
            e.stopPropagation();
            onOpenComments(linha, coluna);
          }}
          title="Comentários da célula"
          type="button"
        >
          💬
        </button>
      )}
    </div>
  );
}