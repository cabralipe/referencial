import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: React.ReactNode;
}

export function PageHeader({ title, description, actions, breadcrumbs }: PageHeaderProps) {
  return (
    <div className="page-header animate-fade-in" style={{ marginBottom: 'var(--space-8)' }}>
      {breadcrumbs && <div style={{ marginBottom: 'var(--space-2)' }}>{breadcrumbs}</div>}
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start', 
        gap: 'var(--space-4)',
        flexWrap: 'wrap'
      }}>
        <div style={{ maxWidth: '800px' }}>
          <h1 style={{ 
            fontSize: '2rem', 
            fontWeight: 700, 
            color: 'var(--color-text)',
            marginBottom: description ? 'var(--space-2)' : 0
          }}>
            {title}
          </h1>
          {description && (
            <p style={{ 
              fontSize: '1.125rem', 
              color: 'var(--color-text-secondary)', 
              lineHeight: 1.6,
              margin: 0 
            }}>
              {description}
            </p>
          )}
        </div>
        
        {actions && (
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
