import { useState } from 'react';
import { TemplateSelector } from './TemplateSelector';
import type { Quadro, QuadroTemplate } from '@/api/types';
import './QuadroToolbar.css';

interface QuadroToolbarProps {
  quadro: Quadro | null;
  template: QuadroTemplate | null;
  onTemplateChange: (templateId: string) => void;
  onExport?: () => void;
  onPrint?: () => void;
  onFullscreen?: () => void;
  onSolicitarRevisao?: () => void;
  onOpenComments?: () => void;
  isLoading?: boolean;
  isSaving?: boolean;
  isRequestingReview?: boolean;
  hasUnsavedChanges?: boolean;
}

export function QuadroToolbar({
  quadro,
  template,
  onTemplateChange,
  onExport,
  onPrint,
  onFullscreen,
  onSolicitarRevisao,
  onOpenComments,
  isLoading = false,
  isSaving = false,
  isRequestingReview = false,
  hasUnsavedChanges = false,
}: QuadroToolbarProps) {
  const [showActions, setShowActions] = useState(false);

  const handleExport = () => {
    if (onExport) {
      onExport();
    }
    setShowActions(false);
  };

  const handlePrint = () => {
    if (onPrint) {
      onPrint();
    } else {
      window.print();
    }
    setShowActions(false);
  };

  const handleFullscreen = () => {
    if (onFullscreen) {
      onFullscreen();
    } else {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        document.documentElement.requestFullscreen();
      }
    }
    setShowActions(false);
  };

  const handleSolicitarRevisao = () => {
    if (onSolicitarRevisao) {
      onSolicitarRevisao();
    }
    setShowActions(false);
  };

  return (
    <div className="quadro-toolbar">
      <div className="toolbar-left">
        <div className="quadro-info">
          <h2 className="quadro-title">
            {template ? template.nome : 'Quadro'}
            {quadro && (
              <span className="version-badge">
                v{quadro.version}
              </span>
            )}
          </h2>
          {template && (
            <p className="quadro-description">
              {template.descricao}
            </p>
          )}
        </div>
      </div>

      <div className="toolbar-center">
        <TemplateSelector
          selectedTemplate={template?.id || ''}
          onTemplateSelect={onTemplateChange}
          disabled={isLoading || isSaving}
        />
      </div>

      <div className="toolbar-right">
        <div className="status-indicators">
          {isSaving && (
            <div className="status-indicator saving">
              <div className="spinner"></div>
              <span>Salvando...</span>
            </div>
          )}
          
          {isRequestingReview && (
            <div className="status-indicator saving">
              <div className="spinner"></div>
              <span>Solicitando...</span>
            </div>
          )}
          
          {hasUnsavedChanges && !isSaving && !isRequestingReview && (
            <div className="status-indicator unsaved">
              <span className="dot"></span>
              <span>Não salvo</span>
            </div>
          )}
          
          {!hasUnsavedChanges && !isSaving && !isRequestingReview && quadro && (
            <div className="status-indicator saved">
              <span className="checkmark">✓</span>
              <span>Salvo</span>
            </div>
          )}
        </div>

        <div className="toolbar-actions">
          {onOpenComments && (
            <button
              className="action-button action-button--comments"
              onClick={onOpenComments}
              disabled={isLoading}
              type="button"
              title="Comentários"
            >
              <span className="action-icon">💬</span>
            </button>
          )}
          
          <button
            className="action-button"
            onClick={() => setShowActions(!showActions)}
            disabled={isLoading}
            type="button"
            title="Mais ações"
          >
            <span className="action-icon">⋮</span>
          </button>

          {showActions && (
            <div className="actions-dropdown">
              {onSolicitarRevisao && (
                <button
                  className="action-item action-item--review"
                  onClick={handleSolicitarRevisao}
                  type="button"
                  disabled={isRequestingReview}
                >
                  <span className="action-item-icon">📋</span>
                  <span>Solicitar Revisão</span>
                </button>
              )}
              
              <button
                className="action-item"
                onClick={handleExport}
                type="button"
              >
                <span className="action-item-icon">📤</span>
                <span>Exportar</span>
              </button>
              
              <button
                className="action-item"
                onClick={handlePrint}
                type="button"
              >
                <span className="action-item-icon">🖨️</span>
                <span>Imprimir</span>
              </button>
              
              <button
                className="action-item"
                onClick={handleFullscreen}
                type="button"
              >
                <span className="action-item-icon">⛶</span>
                <span>Tela cheia</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {showActions && (
        <div 
          className="actions-overlay" 
          onClick={() => setShowActions(false)}
        />
      )}
    </div>
  );
}