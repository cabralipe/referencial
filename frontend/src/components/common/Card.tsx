import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode;
    noPadding?: boolean;
    glass?: boolean;
}

export function Card({ children, className = '', noPadding = false, glass = false, style, ...props }: CardProps) {
    const baseStyles: React.CSSProperties = {
        backgroundColor: glass ? 'var(--color-surface-glass)' : 'var(--color-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-border)',
        boxShadow: glass ? 'var(--shadow-glass)' : 'var(--shadow-sm)',
        padding: noPadding ? 0 : 'var(--space-6)',
        backdropFilter: glass ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: glass ? 'blur(12px)' : 'none',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        ...style
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
