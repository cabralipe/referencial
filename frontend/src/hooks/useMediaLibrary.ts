/**
 * Hooks personalizados para a biblioteca de mídia
 */

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useMediaApi } from '../api/media';
import { useMediaWebSocket } from './useMediaWebSocket';
import type {
  MediaFile,
  MediaFolder,
  Tag,
  MediaLibraryFilters,
  MediaLibrarySort,
  PaginatedResponse,
  UploadProgress,
  MediaLibraryStats,
  MediaFileUpload,
  UserProfile
} from '../types/media';

// Hook para gerenciar arquivos de mídia
export const useMediaFiles = (filters?: MediaLibraryFilters) => {
  const mediaApi = useMediaApi();
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);

  // WebSocket integration
  const { subscribeToFolder, unsubscribeFromFolder } = useMediaWebSocket({
    onFileUploaded: (payload) => {
      // Adicionar novo arquivo à lista se corresponder aos filtros
      if (!filters?.folder || payload.folder_id === filters.folder) {
        setFiles(prev => [payload, ...prev]);
      }
    },
    onFileUpdated: (payload) => {
      setFiles(prev => prev.map(file => 
        file.id === payload.id ? { ...file, ...payload } : file
      ));
    },
    onFileDeleted: (payload) => {
      setFiles(prev => prev.filter(file => file.id !== payload.id));
    },
    onFileMoved: (payload) => {
      // Remover arquivo se foi movido para fora da pasta atual
      if (filters?.folder && payload.new_folder_id !== filters.folder) {
        setFiles(prev => prev.filter(file => file.id !== payload.id));
      }
      // Atualizar folder_id se ainda está na lista
      else {
        setFiles(prev => prev.map(file => 
          file.id === payload.id ? { ...file, folder_id: payload.new_folder_id } : file
        ));
      }
    },
    showToasts: false // Evitar toasts duplicados
  });

  const loadFiles = useCallback(async (reset = false) => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const currentPage = reset ? 1 : page;
      const response = await mediaApi.files.list({
        ...filters,
        page: currentPage
      });
      
      if (reset) {
        setFiles(response.results);
        setPage(2);
      } else {
        setFiles(prev => [...prev, ...response.results]);
        setPage(prev => prev + 1);
      }
      
      setHasMore(!!response.next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar arquivos');
    } finally {
      setLoading(false);
    }
  }, [filters, loading, page]);

  // Subscribe/unsubscribe to folder updates
  useEffect(() => {
    if (filters?.folder) {
      subscribeToFolder(filters.folder);
      return () => unsubscribeFromFolder(filters.folder);
    }
  }, [filters?.folder, subscribeToFolder, unsubscribeFromFolder]);

  const loadMore = useCallback(async () => {
    if (!hasMore || loading) return;
    await loadFiles(false);
  }, [hasMore, loading, loadFiles]);

  const refresh = useCallback(() => {
    loadFiles(true);
  }, [loadFiles]);

  const deleteFile = useCallback(async (id: string) => {
    try {
      await mediaApi.files.delete(id);
      setFiles(prev => prev.filter(file => file.id !== id));
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao excluir arquivo');
    }
  }, []);

  const updateFile = useCallback(async (id: string, data: Partial<MediaFile>) => {
    try {
      const updatedFile = await mediaApi.files.update(id, data);
      setFiles(prev => prev.map(file => file.id === id ? updatedFile : file));
      return updatedFile;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao atualizar arquivo');
    }
  }, []);

  useEffect(() => {
    loadFiles(true);
  }, [loadFiles]);

  return {
    files,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
    deleteFile,
    updateFile
  };
};

// Hook para gerenciar pastas
export const useMediaFolders = () => {
  const mediaApi = useMediaApi();
  const [folders, setFolders] = useState<MediaFolder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket integration
  useMediaWebSocket({
    onFolderCreated: (payload) => {
      setFolders(prev => [payload, ...prev]);
    },
    onFolderUpdated: (payload) => {
      setFolders(prev => prev.map(folder => 
        folder.id === payload.id ? { ...folder, ...payload } : folder
      ));
    },
    onFolderDeleted: (payload) => {
      setFolders(prev => prev.filter(folder => folder.id !== payload.id));
    },
    showToasts: false
  });

  const loadFolders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await mediaApi.folders.list();
      setFolders(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar pastas');
    } finally {
      setLoading(false);
    }
  }, [mediaApi]);

  const createFolder = useCallback(async (data: Partial<MediaFolder>) => {
    try {
      const newFolder = await mediaApi.folders.create(data);
      setFolders(prev => [...prev, newFolder]);
      return newFolder;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao criar pasta');
    }
  }, [mediaApi]);

  const updateFolder = useCallback(async (id: string, data: Partial<MediaFolder>) => {
    try {
      const updatedFolder = await mediaApi.folders.update(id, data);
      setFolders(prev => prev.map(folder => folder.id === id ? updatedFolder : folder));
      return updatedFolder;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao atualizar pasta');
    }
  }, [mediaApi]);

  const deleteFolder = useCallback(async (id: string) => {
    try {
      await mediaApi.folders.delete(id);
      setFolders(prev => prev.filter(folder => folder.id !== id));
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao excluir pasta');
    }
  }, [mediaApi]);

  useEffect(() => {
    loadFolders();
  }, [loadFolders]);

  return {
    folders,
    loading,
    error,
    refresh: loadFolders,
    createFolder,
    updateFolder,
    deleteFolder
  };
};

// Hook para gerenciar tags
export const useMediaTags = () => {
  const mediaApi = useMediaApi();
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTags = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await mediaApi.tags.list();
      setTags(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar tags');
    } finally {
      setLoading(false);
    }
  }, [mediaApi]);

  const createTag = useCallback(async (data: Partial<Tag>) => {
    try {
      const newTag = await mediaApi.tags.create(data);
      setTags(prev => [...prev, newTag]);
      return newTag;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao criar tag');
    }
  }, [mediaApi]);

  const updateTag = useCallback(async (id: string, data: Partial<Tag>) => {
    try {
      const updatedTag = await mediaApi.tags.update(id, data);
      setTags(prev => prev.map(tag => tag.id === id ? updatedTag : tag));
      return updatedTag;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao atualizar tag');
    }
  }, [mediaApi]);

  const deleteTag = useCallback(async (id: string) => {
    try {
      await mediaApi.tags.delete(id);
      setTags(prev => prev.filter(tag => tag.id !== id));
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Erro ao excluir tag');
    }
  }, [mediaApi]);

  useEffect(() => {
    loadTags();
  }, [loadTags]);

  return {
    tags,
    loading,
    error,
    refresh: loadTags,
    createTag,
    updateTag,
    deleteTag
  };
};

// Hook para upload de arquivos
export const useFileUpload = () => {
  const mediaApi = useMediaApi();
  const [uploads, setUploads] = useState<UploadProgress[]>([]);

  const uploadFiles = useCallback(async (files: File[], options?: Partial<MediaFileUpload>) => {
    const newUploads: UploadProgress[] = files.map(file => ({
      file,
      progress: 0,
      status: 'pending'
    }));

    setUploads(prev => [...prev, ...newUploads]);

    const uploadPromises = files.map(async (file, index) => {
      const uploadIndex = uploads.length + index;
      
      try {
        // Atualizar status para uploading
        setUploads(prev => prev.map((upload, i) => 
          i === uploadIndex ? { ...upload, status: 'uploading' } : upload
        ));

        const uploadData: MediaFileUpload = {
          name: options?.name || file.name,
          file,
          folder: options?.folder,
          is_public: options?.is_public,
          tags: options?.tags
        };

        const result = await mediaApi.files.create(uploadData);

        // Atualizar status para completed
        setUploads(prev => prev.map((upload, i) => 
          i === uploadIndex ? { 
            ...upload, 
            status: 'completed', 
            progress: 100,
            result 
          } : upload
        ));

        return result;
      } catch (error) {
        // Atualizar status para error
        setUploads(prev => prev.map((upload, i) => 
          i === uploadIndex ? { 
            ...upload, 
            status: 'error',
            error: error instanceof Error ? error.message : 'Erro no upload'
          } : upload
        ));
        
        throw error;
      }
    });

    return Promise.allSettled(uploadPromises);
  }, [uploads.length, mediaApi]);

  const clearUploads = useCallback(() => {
    setUploads([]);
  }, []);

  const removeUpload = useCallback((index: number) => {
    setUploads(prev => prev.filter((_, i) => i !== index));
  }, []);

  return {
    uploads,
    uploadFiles,
    clearUploads,
    removeUpload
  };
};

// Hook para estatísticas da biblioteca
export const useMediaStats = () => {
  const mediaApi = useMediaApi();
  const [stats, setStats] = useState<MediaLibraryStats | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statsResponse, profileResponse] = await Promise.all([
        mediaApi.profile.getStats(),
        mediaApi.profile.get()
      ]);
      
      setStats(statsResponse);
      setProfile(profileResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar estatísticas');
    } finally {
      setLoading(false);
    }
  }, [mediaApi]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return {
    stats,
    profile,
    loading,
    error,
    refresh: loadStats
  };
};

// Hook principal que combina todos os outros
export const useMediaLibrary = (filters?: MediaLibraryFilters) => {
  const files = useMediaFiles(filters);
  const folders = useMediaFolders();
  const tags = useMediaTags();
  const upload = useFileUpload();
  const stats = useMediaStats();

  return {
    ...files,
    folders: folders.folders,
    tags: tags.tags,
    upload,
    stats: stats.stats,
    profile: stats.profile,
    isLoading: files.loading || folders.loading || tags.loading || stats.loading,
    refresh: () => {
      files.refresh();
      folders.refresh();
      tags.refresh();
      stats.refresh();
    }
  };
};