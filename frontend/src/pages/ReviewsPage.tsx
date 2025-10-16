import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, RefreshCw } from 'lucide-react';
import { useReviews, useReviewActions } from '@/hooks/useReviews';
import { ReviewList } from '@/components/reviews';
import type { Review, ReviewFilters } from '@/api/types';
import './ReviewsPage.css';

export function ReviewsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ReviewFilters>({});
  const [activeTab, setActiveTab] = useState<'all' | 'my_requests' | 'my_reviews'>('all');
  
  const { data: reviews, isLoading, error, refetch } = useReviews(filters);
  const { approveReview, rejectReview } = useReviewActions();

  // Mock current user ID - in real app, this would come from auth context
  const currentUserId = 1;

  const handleViewReview = (review: Review) => {
    navigate(`/reviews/${review.id}`);
  };

  const handleEditReview = (review: Review) => {
    navigate(`/reviews/${review.id}/edit`);
  };

  const handleApproveReview = async (review: Review) => {
    try {
      await approveReview.mutateAsync(review.id);
      refetch();
    } catch (error) {
      console.error('Erro ao aprovar revisão:', error);
    }
  };

  const handleRejectReview = async (review: Review) => {
    try {
      await rejectReview.mutateAsync(review.id);
      refetch();
    } catch (error) {
      console.error('Erro ao reprovar revisão:', error);
    }
  };

  const handleTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    
    // Update filters based on tab
    const newFilters: ReviewFilters = {};
    if (tab === 'my_requests') {
      newFilters.solicitante_id = currentUserId;
    } else if (tab === 'my_reviews') {
      newFilters.revisor_id = currentUserId;
    }
    
    setFilters(newFilters);
  };

  const getTabCounts = () => {
    if (!reviews) return { all: 0, my_requests: 0, my_reviews: 0 };
    
    return {
      all: reviews.length,
      my_requests: reviews.filter(r => r.solicitante?.id === currentUserId).length,
      my_reviews: reviews.filter(r => r.revisor?.id === currentUserId).length,
    };
  };

  const tabCounts = getTabCounts();

  return (
    <div className="reviews-page">
      <div className="reviews-page__header">
        <div className="reviews-page__title-section">
          <h1 className="reviews-page__title">
            <FileText size={24} />
            Sistema de Revisões
          </h1>
          <p className="reviews-page__subtitle">
            Gerencie solicitações de revisão e acompanhe o progresso das avaliações
          </p>
        </div>
        
        <div className="reviews-page__actions">
          <button
            onClick={() => refetch()}
            className="btn btn--secondary"
            disabled={isLoading}
          >
            <RefreshCw size={16} />
            Atualizar
          </button>
        </div>
      </div>

      <div className="reviews-page__tabs">
        <button
          onClick={() => handleTabChange('all')}
          className={`reviews-page__tab ${activeTab === 'all' ? 'active' : ''}`}
        >
          Todas as Revisões
          <span className="reviews-page__tab-count">{tabCounts.all}</span>
        </button>
        <button
          onClick={() => handleTabChange('my_requests')}
          className={`reviews-page__tab ${activeTab === 'my_requests' ? 'active' : ''}`}
        >
          Minhas Solicitações
          <span className="reviews-page__tab-count">{tabCounts.my_requests}</span>
        </button>
        <button
          onClick={() => handleTabChange('my_reviews')}
          className={`reviews-page__tab ${activeTab === 'my_reviews' ? 'active' : ''}`}
        >
          Para Revisar
          <span className="reviews-page__tab-count">{tabCounts.my_reviews}</span>
        </button>
      </div>

      <div className="reviews-page__content">
        <ReviewList
          reviews={reviews || []}
          loading={isLoading}
          error={error}
          onView={handleViewReview}
          onEdit={handleEditReview}
          onApprove={handleApproveReview}
          onReject={handleRejectReview}
          onRefresh={() => refetch()}
          currentUserId={currentUserId}
          showFilters={true}
          emptyMessage={
            activeTab === 'my_requests' 
              ? 'Você ainda não fez nenhuma solicitação de revisão'
              : activeTab === 'my_reviews'
              ? 'Não há revisões pendentes para você'
              : 'Nenhuma revisão encontrada'
          }
        />
      </div>
    </div>
  );
}