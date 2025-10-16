/**
 * Modal para upload de arquivos
 */

import React, { useState, useRef, useCallback } from 'react';
import { 
  X, 
  Upload, 
  Folder, 
  Tag as TagIcon, 
  Eye, 
  EyeOff, 
  Trash2,
  CheckCircle,
  AlertCircle,
  Loader
} from 'lucide-react';
import { toast } from 'sonner';
import { useFileUpload, useMediaFolders, useMediaTags } from '../../hooks/useMediaLibrary';
import { formatFileSize, getFileIcon } from '../../utils/media';
import type { MediaFileUpload, UploadProgress } from '../../types/media';

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
  defaultFolder?: string | null;
}

interface FileItemProps {
  file: File;
  onRemove: () => void;
}

const FileItem: React.FC<FileItemProps> = ({ file, onRemove }) => {
  const FileIcon = getFileIcon(file.type);
  
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border">
        <FileIcon className="w-5 h-5 text-gray-500" />
      </div>
      
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {file.name}
        </p>
        <p className="text-xs text-gray-500">
          {formatFileSize(file.size)}
        </p>
      </div>
      
      <button
        onClick={onRemove}
        className="text-gray-400 hover:text-red-500 transition-colors"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
};

interface UploadProgressItemProps {
  upload: UploadProgress;
}

const UploadProgressItem: React.FC<UploadProgressItemProps> = ({ upload }) => {
  const FileIcon = getFileIcon(upload.file.type);
  
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border">
        <FileIcon className="w-5 h-5 text-gray-500" />
      </div>
      
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {upload.file.name}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all ${
                upload.status === 'completed' ? 'bg-green-500' :
                upload.status === 'error' ? 'bg-red-500' :
                'bg-blue-500'
              }`}
              style={{ width: `${upload.progress}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">
            {upload.progress}%
          </span>
        </div>
      </div>
      
      <div className="flex items-center">
        {upload.status === 'uploading' && (
          <Loader className="w-4 h-4 text-blue-500 animate-spin" />
        )}
        {upload.status === 'completed' && (
          <CheckCircle className="w-4 h-4 text-green-500" />
        )}
        {upload.status === 'error' && (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
      </div>
    </div>
  );
};

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onComplete,
  defaultFolder = null
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadOptions, setUploadOptions] = useState<Partial<MediaFileUpload>>({
    folder: defaultFolder,
    is_public: false,
    tags: []
  });
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { uploads, uploadFiles, clearUploads } = useFileUpload();
  const { folders } = useMediaFolders();
  const { tags } = useMediaTags();

  // Drag and drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const files = Array.from(e.dataTransfer.files);
      setSelectedFiles(prev => [...prev, ...files]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setSelectedFiles(prev => [...prev, ...files]);
    }
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    try {
      await uploadFiles(selectedFiles, uploadOptions);
      setSelectedFiles([]);
      onComplete();
    } catch (error) {
      console.error('Erro no upload:', error);
      toast.error('Erro ao fazer upload dos arquivos');
    }
  }, [selectedFiles, uploadOptions, uploadFiles, onComplete]);

  const handleClose = useCallback(() => {
    setSelectedFiles([]);
    clearUploads();
    onClose();
  }, [clearUploads, onClose]);

  const handleTagToggle = useCallback((tagId: string) => {
    setUploadOptions(prev => {
      const currentTags = prev.tags || [];
      const newTags = currentTags.includes(tagId)
        ? currentTags.filter(id => id !== tagId)
        : [...currentTags, tagId];
      
      return { ...prev, tags: newTags };
    });
  }, []);

  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  const hasUploads = uploads.length > 0;
  const isUploading = uploads.some(upload => upload.status === 'uploading');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={handleClose}
        />

        {/* Modal */}
        <div className="inline-block w-full max-w-2xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-medium text-gray-900">
              Upload de Arquivos
            </h3>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {!hasUploads ? (
            <>
              {/* Drop Zone */}
              <div
                className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-blue-400 bg-blue-50' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p className="mb-2 text-lg font-medium text-gray-900">
                  Arraste arquivos aqui ou clique para selecionar
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  Suporte para imagens, vídeos, áudios e documentos
                </p>
                
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Selecionar Arquivos
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar"
                />
              </div>

              {/* Selected Files */}
              {selectedFiles.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-medium text-gray-900">
                      Arquivos Selecionados ({selectedFiles.length})
                    </h4>
                    <span className="text-sm text-gray-500">
                      Total: {formatFileSize(totalSize)}
                    </span>
                  </div>

                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {selectedFiles.map((file, index) => (
                      <FileItem
                        key={`${file.name}-${index}`}
                        file={file}
                        onRemove={() => removeFile(index)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Upload Options */}
              {selectedFiles.length > 0 && (
                <div className="mt-6 space-y-4">
                  <h4 className="text-sm font-medium text-gray-900">Opções de Upload</h4>

                  {/* Folder Selection */}
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Folder className="w-4 h-4" />
                      Pasta de destino
                    </label>
                    <select
                      value={uploadOptions.folder || ''}
                      onChange={(e) => setUploadOptions(prev => ({ 
                        ...prev, 
                        folder: e.target.value || null 
                      }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Raiz</option>
                      {folders.map((folder) => (
                        <option key={folder.id} value={folder.id}>
                          {folder.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Visibility */}
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      {uploadOptions.is_public ? (
                        <Eye className="w-4 h-4" />
                      ) : (
                        <EyeOff className="w-4 h-4" />
                      )}
                      Visibilidade
                    </label>
                    <div className="flex items-center gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="visibility"
                          checked={!uploadOptions.is_public}
                          onChange={() => setUploadOptions(prev => ({ ...prev, is_public: false }))}
                          className="text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">Privado</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="visibility"
                          checked={uploadOptions.is_public}
                          onChange={() => setUploadOptions(prev => ({ ...prev, is_public: true }))}
                          className="text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">Público</span>
                      </label>
                    </div>
                  </div>

                  {/* Tags */}
                  {tags.length > 0 && (
                    <div>
                      <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                        <TagIcon className="w-4 h-4" />
                        Tags
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {tags.map((tag) => {
                          const isSelected = uploadOptions.tags?.includes(tag.id);
                          return (
                            <button
                              key={tag.id}
                              onClick={() => handleTagToggle(tag.id)}
                              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors ${
                                isSelected
                                  ? 'text-white'
                                  : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
                              }`}
                              style={{
                                backgroundColor: isSelected ? tag.color : undefined
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

                  {/* Upload Button */}
                  <div className="flex items-center justify-end gap-3 pt-4 border-t">
                    <button
                      onClick={handleClose}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={handleUpload}
                      disabled={selectedFiles.length === 0}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Fazer Upload ({selectedFiles.length})
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Upload Progress */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-900">
                  Progresso do Upload
                </h4>
                {!isUploading && (
                  <button
                    onClick={handleClose}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Fechar
                  </button>
                )}
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {uploads.map((upload, index) => (
                  <UploadProgressItem
                    key={`${upload.file.name}-${index}`}
                    upload={upload}
                  />
                ))}
              </div>

              {isUploading && (
                <div className="text-center text-sm text-gray-500">
                  Fazendo upload dos arquivos...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};