import { ReactNode } from 'react';

import './PageInstructions.css';

type Instruction = {
  title: string;
  description: ReactNode;
};

interface PageInstructionsProps {
  title: string;
  description?: ReactNode;
  items?: Instruction[];
  className?: string;
  footer?: ReactNode;
}

export function PageInstructions({ title, description, items, className, footer }: PageInstructionsProps) {
  return (
    <section className={`page-instructions ${className ?? ''}`.trim()}>
      <header className="page-instructions__header">
        <div>
          <span className="page-instructions__eyebrow">Guia rápido</span>
          <h2>{title}</h2>
        </div>
        {description && <p className="page-instructions__description">{description}</p>}
      </header>

      {items && items.length > 0 && (
        <ul className="page-instructions__list">
          {items.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </li>
          ))}
        </ul>
      )}

      {footer && <div className="page-instructions__footer">{footer}</div>}
    </section>
  );
}
