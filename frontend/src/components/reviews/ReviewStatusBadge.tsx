import type { ReviewStatus } from '@/api/types';
import './ReviewStatusBadge.css';

interface ReviewStatusBadgeProps {
  status: ReviewStatus;
  className?: string;
}

const statusConfig = {
  rascunho: {
    label: 'Rascunho',
    className: 'review-status-badge--rascunho',
  },
  em_revisao: {
    label: 'Em Revisão',
    className: 'review-status-badge--em_revisao',
  },
  aprovado: {
    label: 'Aprovado',
    className: 'review-status-badge--aprovado',
  },
  reprovado: {
    label: 'Reprovado',
    className: 'review-status-badge--reprovado',
  },
} as const;

export function ReviewStatusBadge({ status, className = '' }: ReviewStatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <span className={`review-status-badge ${config.className} ${className}`}>
      {config.label}
    </span>
  );
}