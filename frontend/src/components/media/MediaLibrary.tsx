/**
 * Componente principal da biblioteca de mídia
 */

import React, { useState, useCallback } from 'react';
import { Search, Grid, List, Upload, FolderPlus, Filter, SortAsc, Lock } from 'lucide-react';
import { useMediaFiles, useMediaFolders, useMediaTags } from '../../hooks/useMediaLibrary';
import { useMediaPermissions } from '../../hooks/useMediaPermissions';
import { MediaFileGrid } from './MediaFileGrid';
import { MediaFileList } from './MediaFileList';
import { FolderNavigation } from './FolderNavigation';
import { MediaFilters } from './MediaFilters';
import { FileUploadModal } from './FileUploadModal';
import { CreateFolderModal } from './CreateFolderModal';
import type { MediaLibraryView, MediaLibrarySort, MediaLibraryFilters } from '../../types/media';

interface MediaLibraryProps {
  className?: string;
  initialFolderId?: string;
  showFolderNavigation?: boolean;
}

export const MediaLibrary: React.FC<MediaLibraryProps> = ({ 
  className = '',
  initialFolderId,
  showFolderNavigation = true
}) => {
  console.log('📚 Renderizando componente MediaLibrary');
  
  const [view, setView] = useState<MediaLibraryView>('grid');
  const [sort, setSort] = useState<MediaLibrarySort>('created_at');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<string | null>(initialFolderId || null);
  const [showFilters, setShowFilters] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [filters, setFilters] = useState<MediaLibraryFilters>({
    folder: initialFolderId
  });

  // Permissões do usuário
  const { 
    canUpload, 
    canCreateFolders, 
    canManageTags,
    isLoading: permissionsLoading,
    role,
    isGuest 
  } = useMediaPermissions();

  // Hooks
  const { folders, loading: foldersLoading } = useMediaFolders();
  const { tags, loading: tagsLoading } = useMediaTags();
  const { 
    files, 
    loading: filesLoading, 
    hasMore, 
    loadMore, 
    refresh: refreshFiles,
    deleteFile,
    updateFile 
  } = useMediaFiles({
    ...filters,
    folder: selectedFolder,
    search: searchTerm,
    ordering: sort
  });

  // Handlers
  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term);
  }, []);

  const handleFilterChange = useCallback((newFilters: MediaLibraryFilters) => {
    setFilters(newFilters);
  }, []);

  const handleFolderSelect = useCallback((folderId: string | null) => {
    setSelectedFolder(folderId);
  }, []);

  const handleFileDelete = useCallback(async (fileId: string) => {
    try {
      await deleteFile(fileId);
    } catch (error) {
      console.error('Erro ao excluir arquivo:', error);
    }
  }, [deleteFile]);

  const handleFileUpdate = useCallback(async (fileId: string, data: any) => {
    try {
      await updateFile(fileId, data);
    } catch (error) {
      console.error('Erro ao atualizar arquivo:', error);
    }
  }, [updateFile]);

  const handleUploadComplete = useCallback(() => {
    refreshFiles();
    setShowUploadModal(false);
  }, [refreshFiles]);

  const handleFolderCreate = useCallback(() => {
    setShowCreateFolderModal(false);
  }, []);

  const loading = filesLoading || foldersLoading || tagsLoading || permissionsLoading;

  // Mostrar indicador de acesso limitado para guests
  const showAccessIndicator = isGuest || (!canUpload && !canCreateFolders);

  return (
    <div className={`media-library ${className}`}>
      {/* Header */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">Biblioteca de Mídia</h1>
            {showAccessIndicator && (
              <div className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-amber-700 bg-amber-100 rounded-full">
                <Lock className="w-3 h-3" />
                Acesso {role === 'guest' ? 'Público' : 'Limitado'}
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {canCreateFolders && (
              <button
                onClick={() => setShowCreateFolderModal(true)}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <FolderPlus className="w-4 h-4" />
                Nova Pasta
              </button>
            )}
            
            {canUpload && (
              <button
                onClick={() => setShowUploadModal(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <Upload className="w-4 h-4" />
                Upload
              </button>
            )}
            
            {!canUpload && !canCreateFolders && (
              <div className="text-sm text-gray-500 italic">
                Apenas visualização
              </div>
            )}
          </div>
        </div>

        {/* Search and Controls */}
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Pesquisar arquivos..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md border ${
                showFilters 
                  ? 'bg-blue-50 text-blue-700 border-blue-200' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
            >
              <Filter className="w-4 h-4" />
              Filtros
            </button>

            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as MediaLibrarySort)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="created_at">Mais recentes</option>
              <option value="-created_at">Mais antigos</option>
              <option value="name">Nome A-Z</option>
              <option value="-name">Nome Z-A</option>
              <option value="size">Menor tamanho</option>
              <option value="-size">Maior tamanho</option>
            </select>

            <div className="flex border border-gray-300 rounded-md">
              <button
                onClick={() => setView('grid')}
                className={`p-2 ${
                  view === 'grid' 
                    ? 'bg-blue-50 text-blue-600' 
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <Grid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setView('list')}
                className={`p-2 ${
                  view === 'list' 
                    ? 'bg-blue-50 text-blue-600' 
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <MediaFilters
            filters={filters}
            tags={tags}
            onChange={handleFilterChange}
          />
        )}
      </div>

      {/* Content */}
      <div className={showFolderNavigation ? "flex gap-6" : ""}>
        {/* Sidebar - Folder Navigation */}
        {showFolderNavigation && (
          <div className="w-64 flex-shrink-0">
            <FolderNavigation
              folders={folders}
              selectedFolder={selectedFolder}
              onFolderSelect={handleFolderSelect}
              loading={foldersLoading}
            />
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {view === 'grid' ? (
                <MediaFileGrid
                  files={files}
                  onFileDelete={handleFileDelete}
                  onFileUpdate={handleFileUpdate}
                  hasMore={hasMore}
                  onLoadMore={loadMore}
                />
              ) : (
                <MediaFileList
                  files={files}
                  onFileDelete={handleFileDelete}
                  onFileUpdate={handleFileUpdate}
                  hasMore={hasMore}
                  onLoadMore={loadMore}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Modals */}
      {canUpload && (
        <FileUploadModal
          isOpen={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          onUploadComplete={handleUploadComplete}
          folderId={selectedFolder}
        />
      )}

      {canCreateFolders && (
        <CreateFolderModal
          isOpen={showCreateFolderModal}
          onClose={() => setShowCreateFolderModal(false)}
          onFolderCreate={handleFolderCreate}
          parentFolderId={selectedFolder}
        />
      )}
    </div>
  );
};