import { Eye, Edit, Check, X, Clock, User } from 'lucide-react';
import type { Review, ReviewCardProps } from '@/api/types';
import { ReviewStatusBadge } from './ReviewStatusBadge';
import './ReviewCard.css';

// Helper function to get target type label
function getTargetTypeLabel(alvoTipo: string): string {
  const labels = {
    resposta: 'Resposta',
    texto_unico: 'Texto Único',
    quadro: 'Quadro/Oficina',
  };
  return labels[alvoTipo as keyof typeof labels] || alvoTipo;
}

// Helper function to format date
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ReviewCard({ 
  review, 
  onEdit, 
  onApprove, 
  onReject, 
  onView,
  showActions = true,
  currentUserId 
}: ReviewCardProps & { 
  onView?: (review: Review) => void;
  currentUserId?: number;
}) {
  const canReview = currentUserId === review.revisor?.id;
  const canEdit = currentUserId === review.solicitante?.id && review.status === 'rascunho';

  return (
    <div className="review-card">
      <div className="review-card__header">
        <div className="review-card__info">
          <h3 className="review-card__title">
            Revisão {getTargetTypeLabel(review.alvo_tipo)}
          </h3>
          <ReviewStatusBadge status={review.status} />
        </div>
        <div className="review-card__meta">
          <div className="review-card__meta-item">
            <User size={14} />
            <span>Solicitado por: {review.solicitante?.name || 'Usuário desconhecido'}</span>
          </div>
          <div className="review-card__meta-item">
            <User size={14} />
            <span>Revisor: {review.revisor?.name || 'Não atribuído'}</span>
          </div>
          <div className="review-card__meta-item">
            <Clock size={14} />
            <span>Criado em: {formatDate(review.created_at)}</span>
          </div>
          {review.updated_at !== review.created_at && (
            <div className="review-card__meta-item">
              <Clock size={14} />
              <span>Atualizado em: {formatDate(review.updated_at)}</span>
            </div>
          )}
        </div>
      </div>
      
      {review.parecer_html && (
        <div className="review-card__parecer">
          <h4>Parecer:</h4>
          <div 
            className="review-card__parecer-content"
            dangerouslySetInnerHTML={{ __html: review.parecer_html }} 
          />
        </div>
      )}
      
      {showActions && (
        <div className="review-card__actions">
          {/* View action - always available */}
          <button 
            onClick={() => onView?.(review)} 
            className="btn btn--secondary btn--sm"
            title="Visualizar detalhes"
          >
            <Eye size={16} />
            Visualizar
          </button>

          {/* Edit action - only for draft reviews by owner */}
          {canEdit && (
            <button 
              onClick={() => onEdit?.(review)} 
              className="btn btn--secondary btn--sm"
              title="Editar revisão"
            >
              <Edit size={16} />
              Editar
            </button>
          )}
          
          {/* Review actions - only for assigned reviewer on reviews in progress */}
          {canReview && review.status === 'em_revisao' && (
            <>
              <button 
                onClick={() => onApprove?.(review)} 
                className="btn btn--success btn--sm"
                title="Aprovar revisão"
              >
                <Check size={16} />
                Aprovar
              </button>
              <button 
                onClick={() => onReject?.(review)} 
                className="btn btn--danger btn--sm"
                title="Reprovar revisão"
              >
                <X size={16} />
                Reprovar
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}