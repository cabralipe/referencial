/**
 * Componente de filtros para a biblioteca de mídia
 */

import React, { useState, useCallback } from 'react';
import { X, Calendar, Tag as TagIcon, FileType, User } from 'lucide-react';
import { MediaLibraryFilters, Tag } from '../../types/media';

interface MediaFiltersProps {
  filters: MediaLibraryFilters;
  tags: Tag[];
  onChange: (filters: MediaLibraryFilters) => void;
}

export const MediaFilters: React.FC<MediaFiltersProps> = ({
  filters,
  tags,
  onChange
}) => {
  const [localFilters, setLocalFilters] = useState<MediaLibraryFilters>(filters);

  const handleFilterChange = useCallback((key: keyof MediaLibraryFilters, value: any) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onChange(newFilters);
  }, [localFilters, onChange]);

  const handleTagToggle = useCallback((tagId: string) => {
    const currentTags = localFilters.tags || [];
    const newTags = currentTags.includes(tagId)
      ? currentTags.filter(id => id !== tagId)
      : [...currentTags, tagId];
    
    handleFilterChange('tags', newTags.length > 0 ? newTags : undefined);
  }, [localFilters.tags, handleFilterChange]);

  const handleClearFilters = useCallback(() => {
    const clearedFilters = {};
    setLocalFilters(clearedFilters);
    onChange(clearedFilters);
  }, [onChange]);

  const fileTypes = [
    { value: 'image', label: 'Imagens', icon: '🖼️' },
    { value: 'video', label: 'Vídeos', icon: '🎥' },
    { value: 'audio', label: 'Áudios', icon: '🎵' },
    { value: 'document', label: 'Documentos', icon: '📄' },
    { value: 'archive', label: 'Arquivos', icon: '📦' },
    { value: 'other', label: 'Outros', icon: '📎' }
  ];

  const hasActiveFilters = Object.keys(localFilters).some(key => {
    const value = localFilters[key as keyof MediaLibraryFilters];
    return value !== undefined && value !== null && value !== '';
  });

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Filtros</h3>
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Limpar filtros
          </button>
        )}
      </div>

      {/* File Type Filter */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <FileType className="w-4 h-4" />
          Tipo de arquivo
        </label>
        <div className="grid grid-cols-2 gap-2">
          {fileTypes.map((type) => (
            <label key={type.value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localFilters.file_type === type.value}
                onChange={(e) => {
                  handleFilterChange('file_type', e.target.checked ? type.value : undefined);
                }}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">
                {type.icon} {type.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Tags Filter */}
      {tags.length > 0 && (
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
            <TagIcon className="w-4 h-4" />
            Tags
          </label>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => {
              const isSelected = localFilters.tags?.includes(tag.id) || false;
              return (
                <button
                  key={tag.id}
                  onClick={() => handleTagToggle(tag.id)}
                  className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border transition-colors ${
                    isSelected
                      ? 'border-current'
                      : 'border-gray-200 hover:border-current'
                  }`}
                  style={{
                    backgroundColor: isSelected ? tag.color + '40' : 'transparent',
                    color: tag.color
                  }}
                >
                  <TagIcon className="w-3 h-3" />
                  {tag.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Date Range Filter */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <Calendar className="w-4 h-4" />
          Data de criação
        </label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-1">De</label>
            <input
              type="date"
              value={localFilters.created_after || ''}
              onChange={(e) => handleFilterChange('created_after', e.target.value || undefined)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Até</label>
            <input
              type="date"
              value={localFilters.created_before || ''}
              onChange={(e) => handleFilterChange('created_before', e.target.value || undefined)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* File Size Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tamanho do arquivo
        </label>
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="file_size"
              checked={!localFilters.size_min && !localFilters.size_max}
              onChange={() => {
                handleFilterChange('size_min', undefined);
                handleFilterChange('size_max', undefined);
              }}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Qualquer tamanho</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="file_size"
              checked={localFilters.size_max === 1048576} // 1MB
              onChange={() => {
                handleFilterChange('size_min', undefined);
                handleFilterChange('size_max', 1048576);
              }}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Até 1MB</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="file_size"
              checked={localFilters.size_min === 1048576 && localFilters.size_max === 10485760} // 1MB - 10MB
              onChange={() => {
                handleFilterChange('size_min', 1048576);
                handleFilterChange('size_max', 10485760);
              }}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">1MB - 10MB</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="file_size"
              checked={localFilters.size_min === 10485760} // > 10MB
              onChange={() => {
                handleFilterChange('size_min', 10485760);
                handleFilterChange('size_max', undefined);
              }}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Mais de 10MB</span>
          </label>
        </div>
      </div>

      {/* Visibility Filter */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Visibilidade
        </label>
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="visibility"
              checked={localFilters.is_public === undefined}
              onChange={() => handleFilterChange('is_public', undefined)}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Todos</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="visibility"
              checked={localFilters.is_public === true}
              onChange={() => handleFilterChange('is_public', true)}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Públicos</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="visibility"
              checked={localFilters.is_public === false}
              onChange={() => handleFilterChange('is_public', false)}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Privados</span>
          </label>
        </div>
      </div>

      {/* Creator Filter */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <User className="w-4 h-4" />
          Criado por
        </label>
        <input
          type="text"
          placeholder="Nome do usuário..."
          value={localFilters.created_by || ''}
          onChange={(e) => handleFilterChange('created_by', e.target.value || undefined)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
    </div>
  );
};