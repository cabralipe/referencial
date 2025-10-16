/**
 * Modal para criar nova pasta
 */

import React, { useState, useCallback } from 'react';
import { X, Folder, AlertCircle } from 'lucide-react';
import { useMediaFolders } from '../../hooks/useMediaLibrary';

interface CreateFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFolderCreate: () => void;
  parentFolder?: string | null;
}

export const CreateFolderModal: React.FC<CreateFolderModalProps> = ({
  isOpen,
  onClose,
  onFolderCreate,
  parentFolder = null
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { createFolder, folders } = useMediaFolders();

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Nome da pasta é obrigatório');
      return;
    }

    // Verificar se já existe uma pasta com o mesmo nome no mesmo nível
    const existingFolder = folders.find(
      folder => 
        folder.name.toLowerCase() === name.trim().toLowerCase() && 
        folder.parent === parentFolder
    );

    if (existingFolder) {
      setError('Já existe uma pasta com este nome neste local');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await createFolder({
        name: name.trim(),
        description: description.trim() || undefined,
        parent: parentFolder,
        is_public: isPublic
      });

      // Reset form
      setName('');
      setDescription('');
      setIsPublic(false);
      
      onFolderCreate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao criar pasta');
    } finally {
      setLoading(false);
    }
  }, [name, description, isPublic, parentFolder, folders, createFolder, onFolderCreate]);

  const handleClose = useCallback(() => {
    setName('');
    setDescription('');
    setIsPublic(false);
    setError(null);
    onClose();
  }, [onClose]);

  const parentFolderName = parentFolder 
    ? folders.find(f => f.id === parentFolder)?.name 
    : null;

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
        <div className="inline-block w-full max-w-md p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
                <Folder className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Nova Pasta
                </h3>
                {parentFolderName && (
                  <p className="text-sm text-gray-500">
                    em {parentFolderName}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-2 p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Folder Name */}
            <div>
              <label htmlFor="folder-name" className="block text-sm font-medium text-gray-700 mb-1">
                Nome da pasta *
              </label>
              <input
                id="folder-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Digite o nome da pasta"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                maxLength={100}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                {name.length}/100 caracteres
              </p>
            </div>

            {/* Description */}
            <div>
              <label htmlFor="folder-description" className="block text-sm font-medium text-gray-700 mb-1">
                Descrição (opcional)
              </label>
              <textarea
                id="folder-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descreva o conteúdo desta pasta"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                maxLength={500}
              />
              <p className="mt-1 text-xs text-gray-500">
                {description.length}/500 caracteres
              </p>
            </div>

            {/* Visibility */}
            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isPublic}
                  onChange={(e) => setIsPublic(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Tornar pasta pública
                </span>
              </label>
              <p className="mt-1 text-xs text-gray-500">
                Pastas públicas podem ser visualizadas por outros usuários
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading || !name.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2 inline-block" />
                    Criando...
                  </>
                ) : (
                  'Criar Pasta'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};