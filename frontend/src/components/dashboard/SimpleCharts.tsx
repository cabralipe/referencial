import React from 'react';
import './SimpleCharts.css';

// --- SimpleBarChart ---

interface BarChartItem {
    label: string;
    value: number;
    color?: string;
    displayValue?: string;
}

interface SimpleBarChartProps {
    data: BarChartItem[];
    maxValue?: number;
    height?: number;
    showValues?: boolean;
}

export function SimpleBarChart({ data, maxValue, height = 200, showValues = true }: SimpleBarChartProps) {
    const max = maxValue || Math.max(...data.map((d) => d.value), 1);

    return (
        <div className="simple-bar-chart" style={{ height }}>
            {data.map((item, index) => {
                const percent = (item.value / max) * 100;
                return (
                    <div key={index} className="simple-bar-chart__item">
                        <div className="simple-bar-chart__bar-container">
                            <div
                                className="simple-bar-chart__bar"
                                style={{
                                    height: `${percent}%`,
                                    backgroundColor: item.color || '#3b82f6',
                                }}
                            >
                                {showValues && (
                                    <span className="simple-bar-chart__value-label">
                                        {item.displayValue || item.value}
                                    </span>
                                )}
                            </div>
                        </div>
                        <span className="simple-bar-chart__label" title={item.label}>
                            {item.label}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}

// --- SimpleHorizontalBarChart ---

interface SimpleHorizontalBarChartProps {
    data: BarChartItem[];
    maxValue?: number;
    showValues?: boolean;
}

export function SimpleHorizontalBarChart({ data, maxValue, showValues = true }: SimpleHorizontalBarChartProps) {
    const max = maxValue || Math.max(...data.map((d) => d.value), 1);

    return (
        <div className="simple-horizontal-bar-chart">
            {data.map((item, index) => {
                const percent = (item.value / max) * 100;
                return (
                    <div key={index} className="simple-horizontal-bar-chart__item">
                        <div className="simple-horizontal-bar-chart__labels">
                            <span className="simple-horizontal-bar-chart__label">{item.label}</span>
                            {showValues && (
                                <span className="simple-horizontal-bar-chart__value">
                                    {item.displayValue || item.value}
                                </span>
                            )}
                        </div>
                        <div className="simple-horizontal-bar-chart__track">
                            <div
                                className="simple-horizontal-bar-chart__bar"
                                style={{
                                    width: `${percent}%`,
                                    backgroundColor: item.color || '#3b82f6',
                                }}
                            />
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

// --- SimpleDonutChart ---

interface SimpleDonutChartProps {
    percent: number;
    label?: string;
    subLabel?: string;
    color?: string;
    size?: number;
    strokeWidth?: number;
}

export function SimpleDonutChart({
    percent,
    label,
    subLabel,
    color = '#3b82f6',
    size = 120,
    strokeWidth = 10,
}: SimpleDonutChartProps) {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percent / 100) * circumference;

    return (
        <div className="simple-donut-chart" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="simple-donut-chart__svg">
                <circle
                    className="simple-donut-chart__bg"
                    stroke="#e2e8f0"
                    strokeWidth={strokeWidth}
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
                <circle
                    className="simple-donut-chart__progress"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                />
            </svg>
            <div className="simple-donut-chart__content">
                {label && <span className="simple-donut-chart__label">{label}</span>}
                {subLabel && <span className="simple-donut-chart__sublabel">{subLabel}</span>}
            </div>
        </div>
    );
}
