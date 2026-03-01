import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: React.ReactNode;
}

export function PageHeader({ title, description, actions, breadcrumbs }: PageHeaderProps) {
  return (
    <div className="page-header animate-fade-in" style={{ marginBottom: '1.1rem' }}>
      {breadcrumbs && <div style={{ marginBottom: '0.45rem' }}>{breadcrumbs}</div>}

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: '0.85rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ maxWidth: '52rem' }}>
          <h1
            style={{
              fontSize: '1.72rem',
              fontWeight: 900,
              color: 'var(--color-text)',
              marginBottom: description ? '0.32rem' : 0,
              letterSpacing: '-0.015em',
            }}
          >
            {title}
          </h1>
          {description && (
            <p
              style={{
                fontSize: '0.95rem',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.45,
                margin: 0,
              }}
            >
              {description}
            </p>
          )}
        </div>

        {actions && (
          <div style={{ display: 'flex', gap: '0.52rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
