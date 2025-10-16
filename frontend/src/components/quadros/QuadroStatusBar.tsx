import { useMemo } from 'react';
import type { Quadro, QuadroTemplate } from '@/api/types';
import './QuadroStatusBar.css';

interface QuadroStatusBarProps {
  quadro: Quadro | null;
  template: QuadroTemplate | null;
  isLoading?: boolean;
  isSaving?: boolean;
  lastSaved?: Date;
  error?: string | null;
}

export function QuadroStatusBar({
  quadro,
  template,
  isLoading = false,
  isSaving = false,
  lastSaved,
  error,
}: QuadroStatusBarProps) {
  const stats = useMemo(() => {
    if (!quadro || !template) {
      return {
        totalCells: 0,
        filledCells: 0,
        emptyPercentage: 100,
        filledPercentage: 0,
      };
    }

    const totalCells = template.linhas * template.colunas;
    const filledCells = quadro.celulas?.filter(
      celula => celula.valor_html && celula.valor_html.trim() !== ''
    ).length || 0;
    
    const filledPercentage = totalCells > 0 ? Math.round((filledCells / totalCells) * 100) : 0;
    const emptyPercentage = 100 - filledPercentage;

    return {
      totalCells,
      filledCells,
      emptyPercentage,
      filledPercentage,
    };
  }, [quadro, template]);

  const formatLastSaved = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) {
      return 'agora mesmo';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} min atrás`;
    } else if (diffHours < 24) {
      return `${diffHours}h atrás`;
    } else if (diffDays < 7) {
      return `${diffDays}d atrás`;
    } else {
      return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
  };

  const getProgressColor = (percentage: number): string => {
    if (percentage < 25) return '#dc3545'; // red
    if (percentage < 50) return '#ffc107'; // yellow
    if (percentage < 75) return '#fd7e14'; // orange
    return '#28a745'; // green
  };

  return (
    <div className="quadro-status-bar">
      <div className="status-left">
        {template && (
          <div className="template-info">
            <span className="template-name">{template.nome}</span>
            <span className="template-dimensions">
              {template.linhas} × {template.colunas}
            </span>
          </div>
        )}
        
        {quadro && (
          <div className="quadro-version">
            <span className="version-label">Versão:</span>
            <span className="version-number">{quadro.version}</span>
          </div>
        )}
      </div>

      <div className="status-center">
        {error ? (
          <div className="status-error">
            <span className="error-icon">⚠️</span>
            <span className="error-message">{error}</span>
          </div>
        ) : (
          <div className="progress-info">
            <div className="progress-stats">
              <span className="filled-count">
                {stats.filledCells} de {stats.totalCells} células preenchidas
              </span>
              <span className="progress-percentage">
                ({stats.filledPercentage}%)
              </span>
            </div>
            
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{
                  width: `${stats.filledPercentage}%`,
                  backgroundColor: getProgressColor(stats.filledPercentage),
                }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="status-right">
        <div className="save-status">
          {isLoading && (
            <div className="status-item loading">
              <div className="spinner-small"></div>
              <span>Carregando...</span>
            </div>
          )}
          
          {isSaving && (
            <div className="status-item saving">
              <div className="spinner-small"></div>
              <span>Salvando...</span>
            </div>
          )}
          
          {!isLoading && !isSaving && lastSaved && (
            <div className="status-item saved">
              <span className="save-icon">💾</span>
              <span className="save-time">
                Salvo {formatLastSaved(lastSaved)}
              </span>
            </div>
          )}
          
          {!isLoading && !isSaving && !lastSaved && quadro && (
            <div className="status-item unsaved">
              <span className="unsaved-icon">●</span>
              <span>Não salvo</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}