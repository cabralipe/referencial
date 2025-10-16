/**
 * Modal de preview de arquivos de mídia
 */

import React, { useState, useCallback } from 'react';
import { 
  X, 
  Download, 
  Share2, 
  Edit, 
  Trash2, 
  Eye, 
  EyeOff,
  Calendar,
  User,
  HardDrive,
  Tag as TagIcon,
  Clock,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCw
} from 'lucide-react';
import { MediaFile } from '../../types/media';
import { formatFileSize, formatDate, getFileIcon } from '../../utils/media';

interface MediaFilePreviewProps {
  file: MediaFile;
  isOpen: boolean;
  onClose: () => void;
  files?: MediaFile[];
  currentIndex?: number;
  onNavigate?: (direction: 'prev' | 'next') => void;
}

export const MediaFilePreview: React.FC<MediaFilePreviewProps> = ({
  file,
  isOpen,
  onClose,
  files = [],
  currentIndex = 0,
  onNavigate
}) => {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);

  const isImage = file.file_type.startsWith('image/');
  const isVideo = file.file_type.startsWith('video/');
  const isAudio = file.file_type.startsWith('audio/');
  const isPdf = file.file_type === 'application/pdf';
  
  const canNavigate = files.length > 1 && onNavigate;
  const hasPrev = canNavigate && currentIndex > 0;
  const hasNext = canNavigate && currentIndex < files.length - 1;

  const handleDownload = useCallback(() => {
    const link = document.createElement('a');
    link.href = file.file_url;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [file]);

  const handleZoomIn = useCallback(() => {
    setZoom(prev => Math.min(prev + 25, 300));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom(prev => Math.max(prev - 25, 25));
  }, []);

  const handleRotate = useCallback(() => {
    setRotation(prev => (prev + 90) % 360);
  }, []);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!isOpen) return;

    switch (e.key) {
      case 'Escape':
        onClose();
        break;
      case 'ArrowLeft':
        if (hasPrev) onNavigate?.('prev');
        break;
      case 'ArrowRight':
        if (hasNext) onNavigate?.('next');
        break;
      case '+':
      case '=':
        if (isImage) handleZoomIn();
        break;
      case '-':
        if (isImage) handleZoomOut();
        break;
      case 'r':
      case 'R':
        if (isImage) handleRotate();
        break;
    }
  }, [isOpen, hasPrev, hasNext, isImage, onClose, onNavigate, handleZoomIn, handleZoomOut, handleRotate]);

  React.useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const FileIcon = getFileIcon(file.file_type);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black bg-opacity-90">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-black bg-opacity-50 backdrop-blur-sm">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4 text-white">
            <h2 className="text-lg font-medium truncate max-w-md" title={file.name}>
              {file.name}
            </h2>
            {canNavigate && (
              <span className="text-sm text-gray-300">
                {currentIndex + 1} de {files.length}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Image Controls */}
            {isImage && (
              <>
                <button
                  onClick={handleZoomOut}
                  className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded-md"
                  title="Diminuir zoom"
                >
                  <ZoomOut className="w-5 h-5" />
                </button>
                <span className="text-sm text-white px-2">{zoom}%</span>
                <button
                  onClick={handleZoomIn}
                  className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded-md"
                  title="Aumentar zoom"
                >
                  <ZoomIn className="w-5 h-5" />
                </button>
                <button
                  onClick={handleRotate}
                  className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded-md"
                  title="Rotacionar"
                >
                  <RotateCw className="w-5 h-5" />
                </button>
              </>
            )}

            <button
              onClick={handleDownload}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded-md"
              title="Download"
            >
              <Download className="w-5 h-5" />
            </button>

            <button
              onClick={onClose}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded-md"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Navigation */}
      {canNavigate && (
        <>
          {hasPrev && (
            <button
              onClick={() => onNavigate?.('prev')}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 z-10 p-3 text-white bg-black bg-opacity-50 hover:bg-opacity-70 rounded-full"
              title="Arquivo anterior"
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
          )}
          
          {hasNext && (
            <button
              onClick={() => onNavigate?.('next')}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 z-10 p-3 text-white bg-black bg-opacity-50 hover:bg-opacity-70 rounded-full"
              title="Próximo arquivo"
            >
              <ChevronRight className="w-6 h-6" />
            </button>
          )}
        </>
      )}

      {/* Content */}
      <div className="flex h-full pt-16">
        {/* Main Preview */}
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-full max-h-full flex items-center justify-center">
            {isImage ? (
              <img
                src={file.file_url}
                alt={file.name}
                className="max-w-full max-h-full object-contain transition-transform duration-200"
                style={{
                  transform: `scale(${zoom / 100}) rotate(${rotation}deg)`
                }}
              />
            ) : isVideo ? (
              <video
                src={file.file_url}
                controls
                className="max-w-full max-h-full"
                style={{ maxHeight: 'calc(100vh - 8rem)' }}
              >
                Seu navegador não suporta o elemento de vídeo.
              </video>
            ) : isAudio ? (
              <div className="flex flex-col items-center gap-4 text-white">
                <div className="w-32 h-32 bg-gray-700 rounded-lg flex items-center justify-center">
                  <FileIcon className="w-16 h-16" />
                </div>
                <audio
                  src={file.file_url}
                  controls
                  className="w-full max-w-md"
                >
                  Seu navegador não suporta o elemento de áudio.
                </audio>
              </div>
            ) : isPdf ? (
              <iframe
                src={file.file_url}
                className="w-full h-full border-0"
                style={{ minHeight: 'calc(100vh - 8rem)' }}
                title={file.name}
              />
            ) : (
              <div className="flex flex-col items-center gap-4 text-white">
                <div className="w-32 h-32 bg-gray-700 rounded-lg flex items-center justify-center">
                  <FileIcon className="w-16 h-16" />
                </div>
                <p className="text-lg font-medium">{file.name}</p>
                <p className="text-gray-300">Preview não disponível para este tipo de arquivo</p>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* File Info */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Informações do Arquivo</h3>
              
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <HardDrive className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Tamanho</p>
                    <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Criado em</p>
                    <p className="text-sm text-gray-500">{formatDate(file.created_at)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Atualizado em</p>
                    <p className="text-sm text-gray-500">{formatDate(file.updated_at)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <User className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Criado por</p>
                    <p className="text-sm text-gray-500">{file.created_by.username}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {file.is_public ? (
                    <Eye className="w-4 h-4 text-green-500" />
                  ) : (
                    <EyeOff className="w-4 h-4 text-gray-400" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">Visibilidade</p>
                    <p className="text-sm text-gray-500">
                      {file.is_public ? 'Público' : 'Privado'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Tags */}
            {file.tags && file.tags.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {file.tags.map((tag) => (
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
                </div>
              </div>
            )}

            {/* Versions */}
            {file.versions && file.versions.length > 1 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Versões ({file.versions.length})
                </h3>
                <div className="space-y-2">
                  {file.versions.slice(0, 5).map((version, index) => (
                    <div key={version.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Versão {file.versions.length - index}
                          {index === 0 && ' (atual)'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatDate(version.created_at)}
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = version.file_url;
                          link.download = `${file.name}_v${file.versions.length - index}`;
                          link.click();
                        }}
                        className="text-blue-600 hover:text-blue-700"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                  {file.versions.length > 5 && (
                    <p className="text-sm text-gray-500 text-center">
                      +{file.versions.length - 5} versões mais antigas
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Shared With */}
            {file.shared_with && file.shared_with.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Compartilhado com ({file.shared_with.length})
                </h3>
                <div className="space-y-2">
                  {file.shared_with.slice(0, 5).map((share) => (
                    <div key={share.id} className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-gray-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {share.shared_with.username}
                        </p>
                        <p className="text-xs text-gray-500">
                          {share.permission} • {formatDate(share.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                  {file.shared_with.length > 5 && (
                    <p className="text-sm text-gray-500 text-center">
                      +{file.shared_with.length - 5} pessoas
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Ações</h3>
              <div className="space-y-2">
                <button
                  onClick={handleDownload}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
                
                <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
                  <Share2 className="w-4 h-4" />
                  Compartilhar
                </button>
                
                <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md">
                  <Edit className="w-4 h-4" />
                  Editar
                </button>
                
                <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md">
                  <Trash2 className="w-4 h-4" />
                  Excluir
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};