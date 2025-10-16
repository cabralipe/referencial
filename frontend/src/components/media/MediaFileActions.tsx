/**
 * Modal de ações para arquivos de mídia
 */

import React, { useState, useCallback } from 'react';
import { 
  X, 
  Download, 
  Share2, 
  Edit, 
  Trash2, 
  Copy, 
  Move,
  Eye,
  EyeOff,
  Tag as TagIcon,
  Upload,
  AlertCircle,
  Check,
  Lock
} from 'lucide-react';
import { MediaFile } from '../../types/media';
import { useMediaFolders, useMediaTags } from '../../hooks/useMediaLibrary';
import { useMediaPermissions } from '../../hooks/useMediaPermissions';

interface MediaFileActionsProps {
  file: MediaFile;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (fileId: string) => void;
  onUpdate: (fileId: string, data: Partial<MediaFile>) => void;
}

type ActionTab = 'edit' | 'share' | 'move' | 'versions' | 'delete';

export const MediaFileActions: React.FC<MediaFileActionsProps> = ({
  file,
  isOpen,
  onClose,
  onDelete,
  onUpdate
}) => {
  const [activeTab, setActiveTab] = useState<ActionTab>('edit');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Permissões do usuário
  const { 
    canEditFile, 
    canDeleteFile, 
    canShareFiles, 
    canManageTags,
    isViewer,
    isGuest 
  } = useMediaPermissions();

  const canEdit = canEditFile(file.owner?.id || 0);
  const canDelete = canDeleteFile(file.owner?.id || 0);
  const canShare = canShareFiles;

  // Edit form state
  const [editForm, setEditForm] = useState({
    name: file.name,
    description: file.description || '',
    is_public: file.is_public,
    tags: file.tags?.map(tag => tag.id) || []
  });

  // Share form state
  const [shareForm, setShareForm] = useState({
    email: '',
    permission: 'view' as 'view' | 'edit'
  });

  // Move form state
  const [moveForm, setMoveForm] = useState({
    folder: file.folder?.id || ''
  });

  // Delete confirmation
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  const { folders } = useMediaFolders();
  const { tags } = useMediaTags();

  const handleDownload = useCallback(() => {
    const link = document.createElement('a');
    link.href = file.file_url;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [file]);

  const handleEdit = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await onUpdate(file.id, {
        name: editForm.name,
        description: editForm.description || undefined,
        is_public: editForm.is_public,
        tags: editForm.tags
      });
      
      setSuccess('Arquivo atualizado com sucesso!');
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao atualizar arquivo');
    } finally {
      setLoading(false);
    }
  }, [editForm, file.id, onUpdate, onClose]);

  const handleShare = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Implementar lógica de compartilhamento
      console.log('Compartilhar arquivo:', { fileId: file.id, ...shareForm });
      setSuccess('Arquivo compartilhado com sucesso!');
      setShareForm({ email: '', permission: 'view' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao compartilhar arquivo');
    } finally {
      setLoading(false);
    }
  }, [shareForm, file.id]);

  const handleMove = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await onUpdate(file.id, {
        folder: moveForm.folder || null
      });
      
      setSuccess('Arquivo movido com sucesso!');
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao mover arquivo');
    } finally {
      setLoading(false);
    }
  }, [moveForm, file.id, onUpdate, onClose]);

  const handleDelete = useCallback(async () => {
    if (deleteConfirmation !== file.name) {
      setError('Digite o nome do arquivo corretamente para confirmar');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await onDelete(file.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao excluir arquivo');
    } finally {
      setLoading(false);
    }
  }, [deleteConfirmation, file.name, file.id, onDelete, onClose]);

  const handleTagToggle = useCallback((tagId: string) => {
    setEditForm(prev => {
      const currentTags = prev.tags || [];
      const newTags = currentTags.includes(tagId)
        ? currentTags.filter(id => id !== tagId)
        : [...currentTags, tagId];
      
      return { ...prev, tags: newTags };
    });
  }, []);

  if (!isOpen) return null;

  // Filtrar abas baseado nas permissões
  const allTabs = [
    { id: 'edit', label: 'Editar', icon: Edit, enabled: canEdit },
    { id: 'share', label: 'Compartilhar', icon: Share2, enabled: canShare },
    { id: 'move', label: 'Mover', icon: Move, enabled: canEdit },
    { id: 'versions', label: 'Versões', icon: Upload, enabled: canEdit },
    { id: 'delete', label: 'Excluir', icon: Trash2, enabled: canDelete }
  ] as const;

  const tabs = allTabs.filter(tab => tab.enabled);

  // Se não há abas disponíveis, mostrar apenas visualização
  if (tabs.length === 0) {
    return (
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
          <div 
            className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
            onClick={onClose}
          />
          <div className="inline-block w-full max-w-md p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Visualização do Arquivo
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg mb-4">
              <Lock className="w-8 h-8 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">Acesso limitado - apenas visualização</p>
              </div>
            </div>
            <button
              onClick={handleDownload}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-md"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="inline-block w-full max-w-2xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-medium text-gray-900">
              Ações do Arquivo
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* File Info */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg mb-6">
            {file.thumbnail_url ? (
              <img
                src={file.thumbnail_url}
                alt={file.name}
                className="w-12 h-12 object-cover rounded"
              />
            ) : (
              <div className="w-12 h-12 bg-gray-200 rounded flex items-center justify-center">
                <Edit className="w-6 h-6 text-gray-400" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {file.name}
              </p>
              <p className="text-xs text-gray-500">
                {file.file_type} • {new Date(file.created_at).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-6">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Messages */}
          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-3 mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md">
              <Check className="w-4 h-4 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Tab Content */}
          <div className="space-y-4">
            {activeTab === 'edit' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nome do arquivo
                  </label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Descrição
                  </label>
                  <textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Adicione uma descrição..."
                  />
                </div>

                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={editForm.is_public}
                      onChange={(e) => setEditForm(prev => ({ ...prev, is_public: e.target.checked }))}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">Tornar arquivo público</span>
                  </label>
                </div>

                {tags.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tags
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {tags.map((tag) => (
                        <button
                          key={tag.id}
                          onClick={() => handleTagToggle(tag.id)}
                          className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border transition-colors ${
                            editForm.tags.includes(tag.id)
                              ? 'border-current'
                              : 'border-gray-200 hover:border-current'
                          }`}
                          style={{
                            backgroundColor: editForm.tags.includes(tag.id) 
                              ? tag.color + '40' 
                              : 'transparent',
                            color: tag.color
                          }}
                        >
                          <TagIcon className="w-3 h-3" />
                          {tag.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleEdit}
                    disabled={loading}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Salvando...' : 'Salvar'}
                  </button>
                </div>
              </>
            )}

            {activeTab === 'share' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email do usuário
                  </label>
                  <input
                    type="email"
                    value={shareForm.email}
                    onChange={(e) => setShareForm(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="usuario@exemplo.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Permissão
                  </label>
                  <select
                    value={shareForm.permission}
                    onChange={(e) => setShareForm(prev => ({ ...prev, permission: e.target.value as 'view' | 'edit' }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="view">Visualizar</option>
                    <option value="edit">Editar</option>
                  </select>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleShare}
                    disabled={loading || !shareForm.email}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Compartilhando...' : 'Compartilhar'}
                  </button>
                </div>
              </>
            )}

            {activeTab === 'move' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Pasta de destino
                  </label>
                  <select
                    value={moveForm.folder}
                    onChange={(e) => setMoveForm(prev => ({ ...prev, folder: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Raiz (sem pasta)</option>
                    {folders.map((folder) => (
                      <option key={folder.id} value={folder.id}>
                        {folder.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleMove}
                    disabled={loading}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Movendo...' : 'Mover'}
                  </button>
                </div>
              </>
            )}

            {activeTab === 'versions' && (
              <>
                <div className="text-center py-8">
                  <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-500">Funcionalidade de versões em desenvolvimento</p>
                </div>
              </>
            )}

            {activeTab === 'delete' && (
              <>
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="w-5 h-5 text-red-600" />
                    <h4 className="text-sm font-medium text-red-800">
                      Atenção: Esta ação não pode ser desfeita
                    </h4>
                  </div>
                  <p className="text-sm text-red-700">
                    O arquivo será permanentemente excluído e não poderá ser recuperado.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Digite o nome do arquivo para confirmar:
                  </label>
                  <input
                    type="text"
                    value={deleteConfirmation}
                    onChange={(e) => setDeleteConfirmation(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                    placeholder={file.name}
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={loading || deleteConfirmation !== file.name}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    {loading ? 'Excluindo...' : 'Excluir Arquivo'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};