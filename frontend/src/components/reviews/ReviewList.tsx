import { useState } from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';
import { ReviewCard } from './ReviewCard';
import './ReviewList.css';

export function ReviewList({
  reviews,
  loading = false,
  error,
  onEdit,
  onApprove,
  onReject,
  onView,
  onRefresh,
  currentUserId,
  showFilters = true,
  emptyMessage = 'Nenhuma revisão encontrada',
}: ReviewListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [targetTypeFilter, setTargetTypeFilter] = useState<string>('all');
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);

  // Filter reviews based on search and filters
  const filteredReviews = reviews.filter(review => {
    const matchesSearch = searchTerm === '' || 
      review.solicitante?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      review.revisor?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      review.parecer_html?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || review.status === statusFilter;
    const matchesTargetType = targetTypeFilter === 'all' || review.alvo_tipo === targetTypeFilter;
    
    return matchesSearch && matchesStatus && matchesTargetType;
  });

  if (error) {
    return (
      <div className="review-list__error">
        <p>Erro ao carregar revisões: {error.message}</p>
        {onRefresh && (
          <button onClick={onRefresh} className="btn btn--secondary">
            <RefreshCw size={16} />
            Tentar novamente
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="review-list">
      {showFilters && (
        <div className="review-list__filters">
          <div className="review-list__search">
            <Search size={20} />
            <input
              type="text"
              placeholder="Buscar por solicitante, revisor ou parecer..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="review-list__search-input"
            />
          </div>
          
          <button
            onClick={() => setShowFiltersPanel(!showFiltersPanel)}
            className={`review-list__filter-toggle ${showFiltersPanel ? 'active' : ''}`}
          >
            <Filter size={16} />
            Filtros
          </button>
          
          {onRefresh && (
            <button onClick={onRefresh} className="btn btn--secondary btn--sm">
              <RefreshCw size={16} />
              Atualizar
            </button>
          )}
        </div>
      )}

      {showFiltersPanel && (
        <div className="review-list__filters-panel">
          <div className="review-list__filter-group">
            <label htmlFor="status-filter">Status:</label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="review-list__filter-select"
            >
              <option value="all">Todos os status</option>
              <option value="rascunho">Rascunho</option>
              <option value="em_revisao">Em Revisão</option>
              <option value="aprovado">Aprovado</option>
              <option value="reprovado">Reprovado</option>
            </select>
          </div>
          
          <div className="review-list__filter-group">
            <label htmlFor="target-type-filter">Tipo de Alvo:</label>
            <select
              id="target-type-filter"
              value={targetTypeFilter}
              onChange={(e) => setTargetTypeFilter(e.target.value)}
              className="review-list__filter-select"
            >
              <option value="all">Todos os tipos</option>
              <option value="resposta">Resposta</option>
              <option value="texto_unico">Texto Único</option>
              <option value="quadro">Quadro/Oficina</option>
            </select>
          </div>
        </div>
      )}

      {loading ? (
        <div className="review-list__loading">
          <div className="review-list__spinner"></div>
          <p>Carregando revisões...</p>
        </div>
      ) : filteredReviews.length === 0 ? (
        <div className="review-list__empty">
          <p>{emptyMessage}</p>
          {searchTerm || statusFilter !== 'all' || targetTypeFilter !== 'all' ? (
            <button
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
                setTargetTypeFilter('all');
              }}
              className="btn btn--secondary btn--sm"
            >
              Limpar filtros
            </button>
          ) : null}
        </div>
      ) : (
        <div className="review-list__items">
          {filteredReviews.map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              onEdit={onEdit}
              onApprove={onApprove}
              onReject={onReject}
              onView={onView}
              currentUserId={currentUserId}
            />
          ))}
        </div>
      )}

      {filteredReviews.length > 0 && (
        <div className="review-list__summary">
          <p>
            Mostrando {filteredReviews.length} de {reviews.length} revisões
          </p>
        </div>
      )}
    </div>
  );
}