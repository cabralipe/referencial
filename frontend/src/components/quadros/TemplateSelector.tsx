import { useState } from 'react';
import { getAllTemplates } from '@/utils/quadroTemplates';
import './TemplateSelector.css';

interface TemplateSelectorProps {
  selectedTemplate: string;
  onTemplateSelect: (templateId: string) => void;
  disabled?: boolean;
}

export function TemplateSelector({
  selectedTemplate,
  onTemplateSelect,
  disabled = false,
}: TemplateSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const templates = getAllTemplates();
  const currentTemplate = templates.find(t => t.id === selectedTemplate);

  const handleTemplateClick = (templateId: string) => {
    onTemplateSelect(templateId);
    setIsOpen(false);
  };

  const getTemplateIcon = (templateId: string): string => {
    switch (templateId) {
      case 'swot':
        return '⚡';
      case 'canvas':
        return '🏢';
      case 'brainstorm':
        return '💡';
      case 'decisao':
        return '⚖️';
      case 'retrospectiva':
        return '🔄';
      default:
        return '📋';
    }
  };

  return (
    <div className="template-selector">
      <button
        className={`template-selector-button ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        type="button"
      >
        <span className="template-icon">
          {currentTemplate ? getTemplateIcon(currentTemplate.id) : '📋'}
        </span>
        <span className="template-name">
          {currentTemplate ? currentTemplate.nome : 'Selecionar Template'}
        </span>
        <span className="dropdown-arrow">
          {isOpen ? '▲' : '▼'}
        </span>
      </button>

      {isOpen && (
        <div className="template-dropdown">
          <div className="template-dropdown-header">
            <h3>Escolha um Template</h3>
            <button
              className="close-button"
              onClick={() => setIsOpen(false)}
              type="button"
            >
              ✕
            </button>
          </div>
          
          <div className="template-grid">
            {templates.map((template) => (
              <div
                key={template.id}
                className={`template-card ${selectedTemplate === template.id ? 'selected' : ''}`}
                onClick={() => handleTemplateClick(template.id)}
              >
                <div className="template-card-header">
                  <span className="template-card-icon">
                    {getTemplateIcon(template.id)}
                  </span>
                  <h4 className="template-card-title">{template.nome}</h4>
                </div>
                
                <p className="template-card-description">
                  {template.descricao}
                </p>
                
                <div className="template-card-meta">
                  <span className="template-dimensions">
                    {template.linhas} × {template.colunas}
                  </span>
                  {selectedTemplate === template.id && (
                    <span className="selected-badge">✓ Selecionado</span>
                  )}
                </div>
                
                <div className="template-preview">
                  <div className="preview-grid">
                    {Array.from({ length: Math.min(template.linhas, 3) }, (_, linha) => (
                      <div key={linha} className="preview-row">
                        {Array.from({ length: Math.min(template.colunas, 4) }, (_, coluna) => (
                          <div key={coluna} className="preview-cell"></div>
                        ))}
                        {template.colunas > 4 && <div className="preview-more">...</div>}
                      </div>
                    ))}
                    {template.linhas > 3 && (
                      <div className="preview-more-rows">⋮</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {isOpen && (
        <div 
          className="template-overlay" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}