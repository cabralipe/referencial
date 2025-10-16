import { Check, X, Edit, Send, Clock, User, FileText } from 'lucide-react';
import { ReviewStatusBadge } from './ReviewStatusBadge';
import './ReviewWorkflow.css';

export function ReviewWorkflow({
  review,
  onApprove,
  onReject,
  onEdit,
  onSubmit,
  currentUserId,
  loading = false,
}: ReviewWorkflowProps) {
  const isOwner = currentUserId === review.solicitante?.id;
  const isReviewer = currentUserId === review.revisor?.id;
  const canEdit = isOwner && review.status === 'rascunho';
  const canSubmit = isOwner && review.status === 'rascunho';
  const canReview = isReviewer && review.status === 'em_revisao';

  const getWorkflowSteps = () => {
    const steps = [
      {
        id: 'created',
        label: 'Criado',
        icon: FileText,
        completed: true,
        active: review.status === 'rascunho',
        description: 'Revisão criada como rascunho',
      },
      {
        id: 'submitted',
        label: 'Enviado',
        icon: Send,
        completed: ['em_revisao', 'aprovado', 'reprovado'].includes(review.status),
        active: review.status === 'em_revisao',
        description: 'Enviado para revisão',
      },
      {
        id: 'reviewed',
        label: 'Revisado',
        icon: review.status === 'aprovado' ? Check : review.status === 'reprovado' ? X : Clock,
        completed: ['aprovado', 'reprovado'].includes(review.status),
        active: false,
        description: review.status === 'aprovado' ? 'Aprovado' : 
                    review.status === 'reprovado' ? 'Reprovado' : 'Aguardando revisão',
      },
    ];

    return steps;
  };

  const steps = getWorkflowSteps();

  return (
    <div className="review-workflow">
      <div className="review-workflow__header">
        <h3 className="review-workflow__title">Status da Revisão</h3>
        <ReviewStatusBadge status={review.status} />
      </div>

      <div className="review-workflow__steps">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.id} className="review-workflow__step">
              <div className={`review-workflow__step-indicator ${
                step.completed ? 'completed' : step.active ? 'active' : 'pending'
              }`}>
                <Icon size={16} />
              </div>
              <div className="review-workflow__step-content">
                <h4 className="review-workflow__step-title">{step.label}</h4>
                <p className="review-workflow__step-description">{step.description}</p>
              </div>
              {index < steps.length - 1 && (
                <div className={`review-workflow__step-connector ${
                  steps[index + 1].completed ? 'completed' : ''
                }`} />
              )}
            </div>
          );
        })}
      </div>

      <div className="review-workflow__info">
        <div className="review-workflow__info-item">
          <User size={16} />
          <span>Solicitante: {review.solicitante?.name || 'Usuário desconhecido'}</span>
        </div>
        <div className="review-workflow__info-item">
          <User size={16} />
          <span>Revisor: {review.revisor?.name || 'Não atribuído'}</span>
        </div>
        <div className="review-workflow__info-item">
          <Clock size={16} />
          <span>Criado em: {new Date(review.created_at).toLocaleDateString('pt-BR')}</span>
        </div>
        {review.updated_at !== review.created_at && (
          <div className="review-workflow__info-item">
            <Clock size={16} />
            <span>Atualizado em: {new Date(review.updated_at).toLocaleDateString('pt-BR')}</span>
          </div>
        )}
      </div>

      <div className="review-workflow__actions">
        {canEdit && (
          <button
            onClick={() => onEdit?.(review)}
            className="btn btn--secondary"
            disabled={loading}
          >
            <Edit size={16} />
            Editar
          </button>
        )}

        {canSubmit && (
          <button
            onClick={() => onSubmit?.(review)}
            className="btn btn--primary"
            disabled={loading}
          >
            <Send size={16} />
            Enviar para Revisão
          </button>
        )}

        {canReview && (
          <>
            <button
              onClick={() => onApprove?.(review)}
              className="btn btn--success"
              disabled={loading}
            >
              <Check size={16} />
              Aprovar
            </button>
            <button
              onClick={() => onReject?.(review)}
              className="btn btn--danger"
              disabled={loading}
            >
              <X size={16} />
              Reprovar
            </button>
          </>
        )}
      </div>

      {review.parecer_html && (
        <div className="review-workflow__parecer">
          <h4>Parecer do Revisor:</h4>
          <div 
            className="review-workflow__parecer-content"
            dangerouslySetInnerHTML={{ __html: review.parecer_html }}
          />
        </div>
      )}
    </div>
  );
}