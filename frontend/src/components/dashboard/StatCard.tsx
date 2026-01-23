import React from 'react';
import Icon from '@/components/common/Icon';
import './StatCard.css';

interface StatCardProps {
    title: string;
    value: string | number;
    icon?: string;
    trend?: {
        value: number;
        label: string;
        direction: 'up' | 'down' | 'neutral';
    };
    color?: 'blue' | 'green' | 'orange' | 'purple' | 'red';
    loading?: boolean;
}

export function StatCard({ title, value, icon, trend, color = 'blue', loading = false }: StatCardProps) {
    return (
        <div className={`stat-card stat-card--${color}`}>
            <div className="stat-card__header">
                <span className="stat-card__title">{title}</span>
                {icon && (
                    <div className="stat-card__icon">
                        <Icon name={icon} />
                    </div>
                )}
            </div>

            <div className="stat-card__body">
                {loading ? (
                    <div className="stat-card__loading" />
                ) : (
                    <div className="stat-card__value">{value}</div>
                )}

                {trend && !loading && (
                    <div className={`stat-card__trend stat-card__trend--${trend.direction}`}>
                        <Icon name={trend.direction === 'up' ? 'trending_up' : trend.direction === 'down' ? 'trending_down' : 'remove'} />
                        <span>{Math.abs(trend.value)}% {trend.label}</span>
                    </div>
                )}
            </div>
        </div>
    );
}
