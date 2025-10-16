import { useCallback, useRef, useEffect } from 'react';
import './RichTextEditor.css';

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  height?: number;
  readonly?: boolean;
  className?: string;
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = 'Digite seu texto aqui...',
  height = 400,
  readonly = false,
  className = '',
}: RichTextEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = useCallback((event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(event.target.value);
  }, [onChange]);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.max(height, textarea.scrollHeight)}px`;
    }
  }, [value, height]);

  return (
    <div className={`rich-text-editor ${className}`}>
      <div className="editor-toolbar">
        <div className="toolbar-group">
          <button
            type="button"
            className="toolbar-button"
            title="Negrito"
            disabled={readonly}
            onClick={() => {
              // Future: implement bold formatting
              console.log('Bold formatting - to be implemented with TinyMCE');
            }}
          >
            <strong>B</strong>
          </button>
          <button
            type="button"
            className="toolbar-button"
            title="Itálico"
            disabled={readonly}
            onClick={() => {
              // Future: implement italic formatting
              console.log('Italic formatting - to be implemented with TinyMCE');
            }}
          >
            <em>I</em>
          </button>
          <button
            type="button"
            className="toolbar-button"
            title="Sublinhado"
            disabled={readonly}
            onClick={() => {
              // Future: implement underline formatting
              console.log('Underline formatting - to be implemented with TinyMCE');
            }}
          >
            <u>U</u>
          </button>
        </div>
        <div className="toolbar-group">
          <button
            type="button"
            className="toolbar-button"
            title="Lista com marcadores"
            disabled={readonly}
            onClick={() => {
              // Future: implement bullet list
              console.log('Bullet list - to be implemented with TinyMCE');
            }}
          >
            • Lista
          </button>
          <button
            type="button"
            className="toolbar-button"
            title="Lista numerada"
            disabled={readonly}
            onClick={() => {
              // Future: implement numbered list
              console.log('Numbered list - to be implemented with TinyMCE');
            }}
          >
            1. Lista
          </button>
        </div>
      </div>
      
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        readOnly={readonly}
        className={`editor-textarea ${readonly ? 'readonly' : ''}`}
        style={{ minHeight: `${height}px` }}
        spellCheck
      />
      
      <div className="editor-footer">
        <span className="character-count">
          {value.length} caracteres
        </span>
        <span className="editor-hint">
          {readonly ? 'Modo somente leitura' : 'Editor de texto rico (TinyMCE será integrado em breve)'}
        </span>
      </div>
    </div>
  );
}