import { useState } from 'react';
import { Edit, Save, X, FileText } from 'lucide-react';
import type { ReviewParecerProps } from '@/api/types';
import { RichTextEditor } from '@/components/forms/RichTextEditor';
import './ReviewParecer.css';

export function ReviewParecer({
  parecer,
  onUpdate,
  canEdit = false,
  loading = false,
  placeholder = 'Digite o parecer da revisão...',
}: ReviewParecerProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(parecer || '');

  const handleStartEdit = () => {
    setEditValue(parecer || '');
    setIsEditing(true);
  };

  const handleSave = async () => {
    try {
      await onUpdate?.(editValue);
      setIsEditing(false);
    } catch (error) {
      console.error('Erro ao salvar parecer:', error);
    }
  };

  const handleCancel = () => {
    setEditValue(parecer || '');
    setIsEditing(false);
  };

  const hasContent = parecer && parecer.trim() !== '';

  return (
    <div className="review-parecer">
      <div className="review-parecer__header">
        <div className="review-parecer__title">
          <FileText size={16} />
          <h4>Parecer da Revisão</h4>
        </div>
        {canEdit && !isEditing && (
          <button
            onClick={handleStartEdit}
            className="btn btn--secondary btn--sm"
            disabled={loading}
          >
            <Edit size={14} />
            {hasContent ? 'Editar' : 'Adicionar'}
          </button>
        )}
      </div>

      <div className="review-parecer__content">
        {isEditing ? (
          <div className="review-parecer__editor">
            <div className="review-parecer__editor-wrapper">
              <RichTextEditor
                value={editValue}
                onChange={setEditValue}
                placeholder={placeholder}
                disabled={loading}
              />
            </div>
            <div className="review-parecer__editor-actions">
              <button
                onClick={handleCancel}
                className="btn btn--secondary btn--sm"
                disabled={loading}
              >
                <X size={14} />
                Cancelar
              </button>
              <button
                onClick={handleSave}
                className="btn btn--primary btn--sm"
                disabled={loading || !editValue.trim()}
              >
                <Save size={14} />
                {loading ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </div>
        ) : hasContent ? (
          <div className="review-parecer__display">
            <div 
              className="review-parecer__html-content"
              dangerouslySetInnerHTML={{ __html: parecer }}
            />
          </div>
        ) : (
          <div className="review-parecer__empty">
            <FileText size={24} />
            <p>Nenhum parecer foi adicionado ainda.</p>
            {canEdit && (
              <button
                onClick={handleStartEdit}
                className="btn btn--primary btn--sm"
                disabled={loading}
              >
                <Edit size={14} />
                Adicionar Parecer
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}