import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

import './HelpHint.css';

interface HelpHintProps {
  /** Conteúdo explicativo exibido no balão. */
  children: ReactNode;
  /** Rótulo acessível do gatilho. */
  label?: string;
  className?: string;
}

/**
 * Dica contextual reutilizável: um pequeno "?" que abre um balão de ajuda.
 * Acessível por teclado (foco, Enter/Espaço e Esc) e por mouse (hover).
 */
export function HelpHint({ children, label = 'Mais informações', className }: HelpHintProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const wrapperRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const onClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClickOutside);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClickOutside);
    };
  }, [open]);

  return (
    <span
      ref={wrapperRef}
      className={`help-hint ${className ?? ''}`.trim()}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="help-hint__trigger"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onClick={() => setOpen((value) => !value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        ?
      </button>
      {open && (
        <span role="tooltip" id={id} className="help-hint__bubble">
          {children}
        </span>
      )}
    </span>
  );
}
