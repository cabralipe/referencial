import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  style,
  ...props
}: ButtonProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return {
          backgroundColor: 'var(--color-primary)',
          color: '#ffffff',
          border: '1px solid transparent',
          boxShadow: '0 16px 24px -20px var(--color-primary)',
        };
      case 'secondary':
        return {
          backgroundColor: 'var(--color-primary-light)',
          color: 'var(--color-primary)',
          border: '1px solid transparent',
        };
      case 'outline':
        return {
          backgroundColor: '#ffffff',
          color: 'var(--color-text)',
          border: '1px solid var(--color-border)',
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          color: 'var(--color-text-secondary)',
          border: '1px solid transparent',
        };
      case 'danger':
        return {
          backgroundColor: 'var(--color-danger)',
          color: '#ffffff',
          border: '1px solid transparent',
        };
      default:
        return {};
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return {
          padding: '0.42rem 0.74rem',
          fontSize: '0.77rem',
        };
      case 'lg':
        return {
          padding: '0.72rem 1.22rem',
          fontSize: '0.98rem',
        };
      case 'md':
      default:
        return {
          padding: '0.56rem 0.96rem',
          fontSize: '0.86rem',
        };
    }
  };

  const baseStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.45rem',
    borderRadius: '0.7rem',
    fontWeight: 700,
    letterSpacing: '0.01em',
    cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
    opacity: disabled || isLoading ? 0.62 : 1,
    transition: 'all 0.16s ease',
    ...getVariantStyles(),
    ...getSizeStyles(),
    ...style,
  };

  return (
    <button
      className={`btn-${variant} ${className}`}
      style={baseStyles}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <span
          className="spinner"
          style={{
            width: '1em',
            height: '1em',
            border: '2px solid currentColor',
            borderRightColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }}
        />
      )}
      {!isLoading && leftIcon}
      {children}
      {!isLoading && rightIcon}
    </button>
  );
}
