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
                };
            case 'secondary':
                return {
                    backgroundColor: 'var(--color-primary-light)',
                    color: 'var(--color-primary)',
                    border: '1px solid transparent',
                };
            case 'outline':
                return {
                    backgroundColor: 'transparent',
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
                    padding: '0.375rem 0.75rem',
                    fontSize: '0.875rem',
                };
            case 'lg':
                return {
                    padding: '0.75rem 1.5rem',
                    fontSize: '1.125rem',
                };
            case 'md':
            default:
                return {
                    padding: '0.625rem 1.25rem',
                    fontSize: '1rem',
                };
        }
    };

    const baseStyles: React.CSSProperties = {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        borderRadius: 'var(--radius-pill)',
        fontWeight: 600,
        cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
        opacity: disabled || isLoading ? 0.6 : 1,
        transition: 'all 0.2s ease',
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
            {isLoading && <span className="spinner" style={{ width: '1em', height: '1em', border: '2px solid currentColor', borderRightColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />}
            {!isLoading && leftIcon}
            {children}
            {!isLoading && rightIcon}
        </button>
    );
}
