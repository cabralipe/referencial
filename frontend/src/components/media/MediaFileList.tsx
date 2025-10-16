/**
 * Componente de lista de arquivos de mídia
 */

import React, { useState, useCallback } from 'react';
import { 
  Download, 
  Move, 
  Trash2, 
  MoreVertical, 
  Eye, 
  Edit3, 
  Share2,
  Tag as TagIcon,
  Calendar,
  User,
  FileText,
  Lock
} from 'lucide-react';
import { MediaFile } from '../../types/media';
import { MediaFilePreview } from './MediaFilePreview';
import { MediaFileActions } from './MediaFileActions';
import { formatFileSize, formatDate, getFileIcon } from '../../utils/media';
import { useMediaPermissions } from '../../hooks/useMediaPermissions';

interface MediaFileListProps {
  files: MediaFile[];
  onFileDelete: (fileId: string) => void;
  onFileUpdate: (fileId: string, data: Partial<MediaFile>) => void;
  hasMore: boolean;
  onLoadMore: () => void;
}

export const MediaFileList: React.FC<MediaFileListProps> = ({
  files,
  onFileDelete,
  onFileUpdate,
  hasMore,
  onLoadMore
}) => {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [previewFile, setPreviewFile] = useState<MediaFile | null>(null);
  const [actionFile, setActionFile] = useState<MediaFile | null>(null);

  // Permissões do usuário
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

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-12 px-6 py-3">
                <input
                  type="checkbox"
                  checked={selectedFiles.length === files.length && files.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tamanho
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tipo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tags
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Criado em
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Criado por
              </th>
              <th className="w-12 px-6 py-3"></th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {files.map((file) => (
              <MediaFileRow
                key={file.id}
                file={file}
                isSelected={isFileSelected(file.id)}
                onSelect={handleFileSelect}
                onPreview={handleFilePreview}
                onAction={handleFileAction}
              />
            ))}
          </tbody>
        </table>
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

// Componente individual da linha de arquivo
interface MediaFileRowProps {
  file: MediaFile;
  isSelected: boolean;
  onSelect: (fileId: string, isSelected: boolean) => void;
  onPreview: (file: MediaFile) => void;
  onAction: (file: MediaFile) => void;
}

const MediaFileRow: React.FC<MediaFileRowProps> = ({
  file,
  isSelected,
  onSelect,
  onPreview,
  onAction
}) => {
  const FileIcon = getFileIcon(file.file_type);
  
  // Permissões para este arquivo específico
  const { canEditFile, canDeleteFile, canShareFiles } = useMediaPermissions();
  const canEdit = canEditFile(file.owner?.id || 0);
  const canDelete = canDeleteFile(file.owner?.id || 0);
  const hasAnyAction = canEdit || canDelete || canShareFiles;

  return (
    <tr className={`hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}>
      {/* Selection */}
      <td className="px-6 py-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(file.id, e.target.checked)}
          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
      </td>

      {/* Name with thumbnail */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          {/* Thumbnail */}
          <div className="flex-shrink-0 w-10 h-10">
            {file.thumbnail_url ? (
              <img
                src={file.thumbnail_url}
                alt={file.name}
                className="w-10 h-10 object-cover rounded border border-gray-200"
              />
            ) : (
              <div className="w-10 h-10 bg-gray-100 rounded border border-gray-200 flex items-center justify-center">
                <FileIcon className="w-5 h-5 text-gray-400" />
              </div>
            )}
          </div>

          {/* File info */}
          <div className="min-w-0 flex-1">
            <button
              onClick={() => onPreview(file)}
              className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate block"
            >
              {file.name}
            </button>
            {file.description && (
              <p className="text-xs text-gray-500 truncate">{file.description}</p>
            )}
          </div>
        </div>
      </td>

      {/* Size */}
      <td className="px-6 py-4 text-sm text-gray-500">
        {formatFileSize(file.size)}
      </td>

      {/* Type */}
      <td className="px-6 py-4 text-sm text-gray-500">
        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
          {file.file_type}
        </span>
      </td>

      {/* Tags */}
      <td className="px-6 py-4">
        <div className="flex flex-wrap gap-1">
          {file.tags?.slice(0, 3).map((tag) => (
            <span
              key={tag.id}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full"
              style={{
                backgroundColor: tag.color + '20',
                color: tag.color
              }}
            >
              <TagIcon className="w-3 h-3" />
              {tag.name}
            </span>
          ))}
          {file.tags && file.tags.length > 3 && (
            <span className="text-xs text-gray-500">
              +{file.tags.length - 3} mais
            </span>
          )}
        </div>
      </td>

      {/* Created at */}
      <td className="px-6 py-4 text-sm text-gray-500">
        <div className="flex items-center gap-1">
          <Calendar className="w-4 h-4" />
          {formatDate(file.created_at)}
        </div>
      </td>

      {/* Created by */}
      <td className="px-6 py-4 text-sm text-gray-500">
        <div className="flex items-center gap-1">
          <User className="w-4 h-4" />
          {file.created_by?.username || 'Desconhecido'}
        </div>
      </td>

      {/* Actions */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPreview(file)}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
            title="Visualizar"
          >
            <Eye className="w-4 h-4" />
          </button>
          {hasAnyAction ? (
            <button
              onClick={() => onAction(file)}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title="Mais ações"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          ) : (
            <div className="p-1 text-gray-300" title="Acesso limitado">
              <Lock className="w-4 h-4" />
            </div>
          )}
        </div>
      </td>
    </tr>
  );
};