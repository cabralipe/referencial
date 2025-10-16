import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit, Trash2 } from 'lucide-react';
import { useReview, useReviewActions, useUpdateReview, useDeleteReview } from '@/hooks/useReviews';
import { ReviewWorkflow, ReviewParecer, ReviewForm } from '@/components/reviews';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import type { UpdateReviewPayload } from '@/api/types';
import './ReviewDetailPage.css';

export function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const reviewId = parseInt(id || '0');
  const { data: review, isLoading, error, refetch } = useReview(reviewId);
  const { approveReview, rejectReview, submitReview } = useReviewActions();
  const updateReview = useUpdateReview();
  const deleteReview = useDeleteReview();

  // Mock current user ID - in real app, this would come from auth context
  const currentUserId = 1;

  if (isLoading) {
    return <FullPageLoader />;
  }

  if (error || !review) {
    return (
      <div className="review-detail-page__error">
        <h2>Erro ao carregar revisão</h2>
        <p>{error?.message || 'Revisão não encontrada'}</p>
        <button onClick={() => navigate('/reviews')} className="btn btn--primary">
          <ArrowLeft size={16} />
          Voltar para Revisões
        </button>
      </div>
    );
  }

  const isOwner = currentUserId === review.solicitante?.id;
  const isReviewer = currentUserId === review.revisor?.id;
  const canEdit = isOwner && review.status === 'rascunho';
  const canDelete = isOwner && review.status === 'rascunho';

  const canReview = isReviewer && review.status === 'em_revisao';

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleUpdateReview = async (payload: UpdateReviewPayload, action: 'save' | 'submit') => {
    try {
      await updateReview.mutateAsync({ id: reviewId, ...payload });
      
      if (action === 'submit') {
        await submitReview.mutateAsync(reviewId);
      }
      
      setIsEditing(false);
      refetch();
    } catch (error) {
      console.error('Erro ao atualizar revisão:', error);
      throw error;
    }
  };

  const handleApprove = async () => {
    try {
      await approveReview.mutateAsync(reviewId);
      refetch();
    } catch (error) {
      console.error('Erro ao aprovar revisão:', error);
    }
  };

  const handleReject = async () => {
    try {
      await rejectReview.mutateAsync(reviewId);
      refetch();
    } catch (error) {
      console.error('Erro ao reprovar revisão:', error);
    }
  };

  const handleSubmit = async () => {
    try {
      await submitReview.mutateAsync(reviewId);
      refetch();
    } catch (error) {
      console.error('Erro ao enviar revisão:', error);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteReview.mutateAsync(reviewId);
      navigate('/reviews');
    } catch (error) {
      console.error('Erro ao excluir revisão:', error);
    }
  };

  const handleUpdateParecer = async (newParecer: string) => {
    try {
      await updateReview.mutateAsync({ 
        id: reviewId, 
        parecer_html: newParecer 
      });
      refetch();
    } catch (error) {
      console.error('Erro ao atualizar parecer:', error);
      throw error;
    }
  };

  const getTargetTypeLabel = (type: string) => {
    const labels = {
      resposta: 'Resposta',
      texto_unico: 'Texto Único',
      quadro: 'Quadro/Oficina',
    };
    return labels[type as keyof typeof labels] || type;
  };

  if (isEditing) {
    return (
      <div className="review-detail-page">
        <div className="review-detail-page__header">
          <button 
            onClick={handleCancelEdit}
            className="btn btn--secondary"
          >
            <ArrowLeft size={16} />
            Cancelar Edição
          </button>
        </div>

        <ReviewForm
          review={review}
          mode="edit"
          onSubmit={handleUpdateReview}
          onCancel={handleCancelEdit}
          loading={updateReview.isPending || submitReview.isPending}
          availableReviewers={[]} // TODO: Load available reviewers
        />
      </div>
    );
  }

  return (
    <div className="review-detail-page">
      <div className="review-detail-page__header">
        <button 
          onClick={() => navigate('/reviews')}
          className="btn btn--secondary"
        >
          <ArrowLeft size={16} />
          Voltar para Revisões
        </button>

        <div className="review-detail-page__header-info">
          <h1 className="review-detail-page__title">
            Revisão de {getTargetTypeLabel(review.alvo_tipo)}
          </h1>
          <p className="review-detail-page__subtitle">
            ID: {review.id} • Criado em {new Date(review.created_at).toLocaleDateString('pt-BR')}
          </p>
        </div>

        <div className="review-detail-page__header-actions">
          {canEdit && (
            <button 
              onClick={handleEdit}
              className="btn btn--primary"
              disabled={updateReview.isPending}
            >
              <Edit size={16} />
              Editar
            </button>
          )}
          
          {canDelete && (
            <button 
              onClick={() => setShowDeleteConfirm(true)}
              className="btn btn--danger"
              disabled={deleteReview.isPending}
            >
              <Trash2 size={16} />
              Excluir
            </button>
          )}
        </div>
      </div>

      <div className="review-detail-page__content">
        <div className="review-detail-page__main">
          <ReviewWorkflow
            review={review}
            onApprove={handleApprove}
            onReject={handleReject}
            onEdit={handleEdit}
            onSubmit={handleSubmit}
            currentUserId={currentUserId}
            loading={
              approveReview.isPending || 
              rejectReview.isPending || 
              submitReview.isPending
            }
          />
        </div>

        <div className="review-detail-page__sidebar">
          <ReviewParecer
            parecer={review.parecer_html}
            onUpdate={handleUpdateParecer}
            canEdit={canReview}
            loading={updateReview.isPending}
          />
        </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="review-detail-page__modal-overlay">
          <div className="review-detail-page__modal">
            <h3>Confirmar Exclusão</h3>
            <p>Tem certeza que deseja excluir esta revisão? Esta ação não pode ser desfeita.</p>
            <div className="review-detail-page__modal-actions">
              <button 
                onClick={() => setShowDeleteConfirm(false)}
                className="btn btn--secondary"
              >
                Cancelar
              </button>
              <button 
                onClick={handleDelete}
                className="btn btn--danger"
                disabled={deleteReview.isPending}
              >
                <Trash2 size={16} />
                {deleteReview.isPending ? 'Excluindo...' : 'Excluir'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}