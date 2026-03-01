import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  noPadding?: boolean;
  glass?: boolean;
}

export function Card({ children, className = '', noPadding = false, glass = false, style, ...props }: CardProps) {
  const baseStyles: React.CSSProperties = {
    backgroundColor: glass ? 'var(--color-surface-glass)' : 'var(--color-surface)',
    borderRadius: '0.9rem',
    border: '1px solid var(--color-border)',
    boxShadow: glass ? 'var(--shadow-glass)' : 'var(--shadow-sm)',
    padding: noPadding ? 0 : '1.1rem',
    backdropFilter: glass ? 'blur(8px)' : 'none',
    WebkitBackdropFilter: glass ? 'blur(8px)' : 'none',
    transition: 'border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease',
    ...style,
  };

  return (
    <div
      className={`card ${className}`}
      style={baseStyles}
      {...props}
    >
      {children}
    </div>
  );
}
