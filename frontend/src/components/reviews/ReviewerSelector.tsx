import { useState } from 'react';
import { Search, User, Check } from 'lucide-react';
import type { ReviewerSelectorProps, User as UserType } from '@/api/types';
import './ReviewerSelector.css';

export function ReviewerSelector({
  reviewers,
  selectedReviewerId,
  onSelect,
  loading = false,
  placeholder = 'Selecione um revisor',
  showSearch = true,
}: ReviewerSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const filteredReviewers = reviewers.filter(reviewer =>
    reviewer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    reviewer.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const selectedReviewer = reviewers.find(r => r.id === selectedReviewerId);

  const handleSelect = (reviewer: UserType) => {
    onSelect(reviewer.id);
    setIsOpen(false);
    setSearchTerm('');
  };

  return (
    <div className="reviewer-selector">
      <div 
        className={`reviewer-selector__trigger ${isOpen ? 'open' : ''} ${loading ? 'loading' : ''}`}
        onClick={() => !loading && setIsOpen(!isOpen)}
      >
        <div className="reviewer-selector__trigger-content">
          {selectedReviewer ? (
            <div className="reviewer-selector__selected">
              <User size={16} />
              <span>{selectedReviewer.name}</span>
              {selectedReviewer.email && (
                <span className="reviewer-selector__email">({selectedReviewer.email})</span>
              )}
            </div>
          ) : (
            <div className="reviewer-selector__placeholder">
              <User size={16} />
              <span>{placeholder}</span>
            </div>
          )}
        </div>
        <div className="reviewer-selector__arrow">
          <svg width="12" height="8" viewBox="0 0 12 8" fill="none">
            <path d="M1 1L6 6L11 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>

      {isOpen && (
        <div className="reviewer-selector__dropdown">
          {showSearch && (
            <div className="reviewer-selector__search">
              <Search size={16} />
              <input
                type="text"
                placeholder="Buscar revisor..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="reviewer-selector__search-input"
                autoFocus
              />
            </div>
          )}

          <div className="reviewer-selector__options">
            {filteredReviewers.length === 0 ? (
              <div className="reviewer-selector__no-results">
                {searchTerm ? 'Nenhum revisor encontrado' : 'Nenhum revisor disponível'}
              </div>
            ) : (
              filteredReviewers.map((reviewer) => (
                <div
                  key={reviewer.id}
                  className={`reviewer-selector__option ${
                    reviewer.id === selectedReviewerId ? 'selected' : ''
                  }`}
                  onClick={() => handleSelect(reviewer)}
                >
                  <div className="reviewer-selector__option-content">
                    <User size={16} />
                    <div className="reviewer-selector__option-info">
                      <span className="reviewer-selector__option-name">{reviewer.name}</span>
                      {reviewer.email && (
                        <span className="reviewer-selector__option-email">{reviewer.email}</span>
                      )}
                    </div>
                  </div>
                  {reviewer.id === selectedReviewerId && (
                    <Check size={16} className="reviewer-selector__check" />
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Overlay to close dropdown when clicking outside */}
      {isOpen && (
        <div 
          className="reviewer-selector__overlay"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}