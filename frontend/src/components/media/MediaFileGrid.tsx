/**
 * Componente de grid para exibir arquivos de mídia
 */

import React, { useState, useCallback } from 'react';
import { 
  MoreVertical, 
  Download, 
  Edit, 
  Trash2, 
  Share2, 
  Copy, 
  Move,
  Eye,
  Clock,
  Tag,
  Lock
} from 'lucide-react';
import { MediaFile } from '../../types/media';
import { MediaFilePreview } from './MediaFilePreview';
import { MediaFileActions } from './MediaFileActions';
import { useMediaPermissions } from '../../hooks/useMediaPermissions';
import { formatFileSize, formatDate, getFileIcon } from '../../utils/media';

interface MediaFileGridProps {
  files: MediaFile[];
  onFileDelete: (fileId: string) => void;
  onFileUpdate: (fileId: string, data: Partial<MediaFile>) => void;
  hasMore: boolean;
  onLoadMore: () => void;
}

export const MediaFileGrid: React.FC<MediaFileGridProps> = ({
  files,
  onFileDelete,
  onFileUpdate,
  hasMore,
  onLoadMore
}) => {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [previewFile, setPreviewFile] = useState<MediaFile | null>(null);
  const [actionFile, setActionFile] = useState<MediaFile | null>(null);
  
  const { canEditFile, canDeleteFile, canShareFiles } = useMediaPermissions();

  const handleFileSelect = useCallback((fileId: string, isSelected: boolean) => {
    setSelectedFiles(prev => 
      isSelected 
        ? [...prev, fileId]
        : prev.filter(id => id !== fileId)
    );
  }, []);

  const handleSelectAll = useCallback(() => {
    const allSelected = selectedFiles.length === files.length;
    setSelectedFiles(allSelected ? [] : files.map(f => f.id));
  }, [selectedFiles.length, files]);

  const handleFilePreview = useCallback((file: MediaFile) => {
    setPreviewFile(file);
  }, []);

  const handleFileAction = useCallback((file: MediaFile) => {
    setActionFile(file);
  }, []);

  const isFileSelected = useCallback((fileId: string) => {
    return selectedFiles.includes(fileId);
  }, [selectedFiles]);

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <div className="w-16 h-16 mb-4 text-gray-300">
          <svg fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        </div>
        <p className="text-lg font-medium">Nenhum arquivo encontrado</p>
        <p className="text-sm">Faça upload de arquivos para começar</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Selection Controls */}
      {selectedFiles.length > 0 && (
        <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <span className="text-sm font-medium text-blue-900">
            {selectedFiles.length} arquivo{selectedFiles.length !== 1 ? 's' : ''} selecionado{selectedFiles.length !== 1 ? 's' : ''}
          </span>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1 px-3 py-1 text-sm text-blue-700 hover:bg-blue-100 rounded">
              <Download className="w-4 h-4" />
              Download
            </button>
            <button className="flex items-center gap-1 px-3 py-1 text-sm text-blue-700 hover:bg-blue-100 rounded">
              <Move className="w-4 h-4" />
              Mover
            </button>
            <button className="flex items-center gap-1 px-3 py-1 text-sm text-red-700 hover:bg-red-100 rounded">
              <Trash2 className="w-4 h-4" />
              Excluir
            </button>
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {files.map((file) => (
          <MediaFileCard
            key={file.id}
            file={file}
            isSelected={isFileSelected(file.id)}
            onSelect={handleFileSelect}
            onPreview={handleFilePreview}
            onAction={handleFileAction}
          />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center pt-6">
          <button
            onClick={onLoadMore}
            className="px-6 py-2 text-sm font-medium text-blue-600 bg-white border border-blue-600 rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Carregar mais
          </button>
        </div>
      )}

      {/* Preview Modal */}
      {previewFile && (
        <MediaFilePreview
          file={previewFile}
          isOpen={!!previewFile}
          onClose={() => setPreviewFile(null)}
        />
      )}

      {/* Actions Modal */}
      {actionFile && (
        <MediaFileActions
          file={actionFile}
          isOpen={!!actionFile}
          onClose={() => setActionFile(null)}
          onDelete={onFileDelete}
          onUpdate={onFileUpdate}
        />
      )}
    </div>
  );
};

// Componente individual do card de arquivo
interface MediaFileCardProps {
  file: MediaFile;
  isSelected: boolean;
  onSelect: (fileId: string, isSelected: boolean) => void;
  onPreview: (file: MediaFile) => void;
  onAction: (file: MediaFile) => void;
}

const MediaFileCard: React.FC<MediaFileCardProps> = ({
  file,
  isSelected,
  onSelect,
  onPreview,
  onAction
}) => {
  const FileIcon = getFileIcon(file.file_type);
  const { canEditFile, canDeleteFile, canShareFiles } = useMediaPermissions();
  
  const canEdit = canEditFile(file.owner?.id || 0);
  const canDelete = canDeleteFile(file.owner?.id || 0);
  const hasLimitedAccess = !canEdit && !canDelete && !canShareFiles;

  return (
    <div 
      className={`group relative bg-white border rounded-lg overflow-hidden hover:shadow-md transition-shadow ${
        isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-200'
      }`}
    >
      {/* Selection Checkbox */}
      <div className="absolute top-2 left-2 z-10">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(file.id, e.target.checked)}
          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
      </div>

      {/* Actions Menu */}
      <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
        {(canEdit || canDelete || canShareFiles) ? (
          <button
            onClick={() => onAction(file)}
            className="p-1 bg-white rounded-full shadow-sm hover:bg-gray-50"
          >
            <MoreVertical className="w-4 h-4 text-gray-600" />
          </button>
        ) : (
          <div className="p-1 bg-gray-100 rounded-full">
            <Lock className="w-4 h-4 text-gray-400" />
          </div>
        )}
      </div>

      {/* Thumbnail/Preview */}
      <div 
        className="aspect-square bg-gray-50 flex items-center justify-center cursor-pointer"
        onClick={() => onPreview(file)}
      >
        {file.thumbnail_url ? (
          <img
            src={file.thumbnail_url}
            alt={file.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <FileIcon className="w-8 h-8 text-gray-400" />
        )}
      </div>

      {/* File Info */}
      <div className="p-3">
        <h3 
          className="text-sm font-medium text-gray-900 truncate cursor-pointer hover:text-blue-600"
          title={file.name}
          onClick={() => onPreview(file)}
        >
          {file.name}
        </h3>
        
        <div className="mt-1 space-y-1">
          <p className="text-xs text-gray-500">
            {formatFileSize(file.size)}
          </p>
          
          <p className="text-xs text-gray-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDate(file.created_at)}
          </p>

          {file.tags && file.tags.length > 0 && (
            <div className="flex items-center gap-1 mt-2">
              <Tag className="w-3 h-3 text-gray-400" />
              <div className="flex gap-1">
                {file.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag.id}
                    className="inline-block px-1.5 py-0.5 text-xs rounded"
                    style={{ 
                      backgroundColor: tag.color + '20', 
                      color: tag.color 
                    }}
                  >
                    {tag.name}
                  </span>
                ))}
                {file.tags.length > 2 && (
                  <span className="text-xs text-gray-400">
                    +{file.tags.length - 2}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status Indicators */}
      <div className="absolute bottom-2 right-2 flex gap-1">
        {file.is_public && (
          <div className="w-2 h-2 bg-green-500 rounded-full" title="Público" />
        )}
        {file.shared_with && file.shared_with.length > 0 && (
          <div className="w-2 h-2 bg-blue-500 rounded-full" title="Compartilhado" />
        )}
        {file.versions && file.versions.length > 1 && (
          <div className="w-2 h-2 bg-orange-500 rounded-full" title="Múltiplas versões" />
        )}
      </div>
    </div>
  );
};