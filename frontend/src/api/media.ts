/**
 * API client para operações de mídia
 */

import { useMemo } from 'react';
import { useApiClient } from './client';
import type {
  MediaFile,
  MediaFolder,
  Tag,
  FileVersion,
  FileShare,
  UserProfile,
  MediaLibraryStats,
  MediaFileResponse,
  MediaFolderResponse,
  TagResponse,
  PaginatedResponse,
  MediaLibraryFilters,
  MediaFileUpload
} from '../types/media';

const MEDIA_BASE_URL = '/v1/media';

// Função para criar a API de mídia
const createMediaApi = (apiClient: ReturnType<typeof useApiClient>) => ({
  // Arquivos de mídia
  files: {
    list: async (filters?: MediaLibraryFilters): Promise<MediaFileResponse> => {
      const params = new URLSearchParams();
      
      if (filters?.search) params.append('search', filters.search);
      if (filters?.folder) params.append('folder', filters.folder);
      if (filters?.file_type) params.append('file_type', filters.file_type);
      if (filters?.is_public !== undefined) params.append('is_public', String(filters.is_public));
      if (filters?.owner) params.append('owner', String(filters.owner));
      if (filters?.ordering) params.append('ordering', filters.ordering);
      if (filters?.tags?.length) {
        filters.tags.forEach(tag => params.append('tags', tag));
      }

      const response = await apiClient.get(`${MEDIA_BASE_URL}/files/?${params}`);
      return response.data;
    },

    get: async (id: string): Promise<MediaFile> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/files/${id}/`);
      return response.data;
    },

    create: async (data: MediaFileUpload): Promise<MediaFile> => {
      const formData = new FormData();
      formData.append('name', data.name);
      formData.append('file', data.file);
      
      if (data.folder) formData.append('folder', data.folder);
      if (data.is_public !== undefined) formData.append('is_public', String(data.is_public));
      if (data.tags?.length) {
        data.tags.forEach(tag => formData.append('tags', tag));
      }

      const response = await apiClient.post(`${MEDIA_BASE_URL}/files/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },

    update: async (id: string, data: Partial<MediaFile>): Promise<MediaFile> => {
      const response = await apiClient.patch(`${MEDIA_BASE_URL}/files/${id}/`, data);
      return response.data;
    },

    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`${MEDIA_BASE_URL}/files/${id}/`);
    },

    move: async (id: string, folderId?: string): Promise<MediaFile> => {
      const response = await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/move/`, {
        folder: folderId
      });
      return response.data;
    },

    copy: async (id: string, name: string, folderId?: string): Promise<MediaFile> => {
      const response = await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/copy/`, {
        name,
        folder: folderId
      });
      return response.data;
    },

    addTag: async (id: string, tagId: string): Promise<void> => {
      await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/add_tag/`, {
        tag_id: tagId
      });
    },

    removeTag: async (id: string, tagId: string): Promise<void> => {
      await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/remove_tag/`, {
        tag_id: tagId
      });
    },

    share: async (id: string, userId: number, permission: string, expiresAt?: string): Promise<FileShare> => {
      const response = await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/share/`, {
        user_id: userId,
        permission_level: permission,
        expires_at: expiresAt
      });
      return response.data;
    },

    unshare: async (id: string, shareId: string): Promise<void> => {
      await apiClient.delete(`${MEDIA_BASE_URL}/files/${id}/shares/${shareId}/`);
    },

    createVersion: async (id: string, file: File, description?: string): Promise<FileVersion> => {
      const formData = new FormData();
      formData.append('file_data', file);
      if (description) formData.append('change_description', description);

      const response = await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/create_version/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },

    restoreVersion: async (id: string, versionId: string): Promise<MediaFile> => {
      const response = await apiClient.post(`${MEDIA_BASE_URL}/files/${id}/restore_version/`, {
        version_id: versionId
      });
      return response.data;
    }
  },

  // Pastas
  folders: {
    list: async (): Promise<MediaFolderResponse> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/folders/`);
      return response.data;
    },

    get: async (id: string): Promise<MediaFolder> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/folders/${id}/`);
      return response.data;
    },

    create: async (data: Partial<MediaFolder>): Promise<MediaFolder> => {
      const response = await apiClient.post(`${MEDIA_BASE_URL}/folders/`, data);
      return response.data;
    },

    update: async (id: string, data: Partial<MediaFolder>): Promise<MediaFolder> => {
      const response = await apiClient.patch(`${MEDIA_BASE_URL}/folders/${id}/`, data);
      return response.data;
    },

    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`${MEDIA_BASE_URL}/folders/${id}/`);
    },

    getFiles: async (id: string, filters?: MediaLibraryFilters): Promise<MediaFileResponse> => {
      const params = new URLSearchParams();
      
      if (filters?.search) params.append('search', filters.search);
      if (filters?.file_type) params.append('file_type', filters.file_type);
      if (filters?.ordering) params.append('ordering', filters.ordering);

      const response = await apiClient.get(`${MEDIA_BASE_URL}/folders/${id}/files/?${params}`);
      return response.data;
    }
  },

  // Tags
  tags: {
    list: async (): Promise<TagResponse> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/tags/`);
      return response.data;
    },

    get: async (id: string): Promise<Tag> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/tags/${id}/`);
      return response.data;
    },

    create: async (data: Partial<Tag>): Promise<Tag> => {
      const response = await apiClient.post(`${MEDIA_BASE_URL}/tags/`, data);
      return response.data;
    },

    update: async (id: string, data: Partial<Tag>): Promise<Tag> => {
      const response = await apiClient.patch(`${MEDIA_BASE_URL}/tags/${id}/`, data);
      return response.data;
    },

    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`${MEDIA_BASE_URL}/tags/${id}/`);
    },

    getFiles: async (id: string, filters?: MediaLibraryFilters): Promise<MediaFileResponse> => {
      const params = new URLSearchParams();
      
      if (filters?.search) params.append('search', filters.search);
      if (filters?.ordering) params.append('ordering', filters.ordering);

      const response = await apiClient.get(`${MEDIA_BASE_URL}/tags/${id}/files/?${params}`);
      return response.data;
    }
  },

  // Versões de arquivo
  versions: {
    list: async (fileId: string): Promise<PaginatedResponse<FileVersion>> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/file-versions/?file=${fileId}`);
      return response.data;
    },

    get: async (id: string): Promise<FileVersion> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/file-versions/${id}/`);
      return response.data;
    },

    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`${MEDIA_BASE_URL}/file-versions/${id}/`);
    }
  },

  // Compartilhamentos
  shares: {
    list: async (fileId?: string): Promise<PaginatedResponse<FileShare>> => {
      const params = fileId ? `?file=${fileId}` : '';
      const response = await apiClient.get(`${MEDIA_BASE_URL}/file-shares/${params}`);
      return response.data;
    },

    get: async (id: string): Promise<FileShare> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/file-shares/${id}/`);
      return response.data;
    },

    update: async (id: string, data: Partial<FileShare>): Promise<FileShare> => {
      const response = await apiClient.patch(`${MEDIA_BASE_URL}/file-shares/${id}/`, data);
      return response.data;
    },

    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`${MEDIA_BASE_URL}/file-shares/${id}/`);
    }
  },

  // Perfil do usuário
  profile: {
    get: async (): Promise<UserProfile> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/user-profile/me/`);
      return response.data;
    },

    update: async (data: Partial<UserProfile>): Promise<UserProfile> => {
      const response = await apiClient.patch(`${MEDIA_BASE_URL}/user-profile/me/`, data);
      return response.data;
    },

    getStats: async (): Promise<MediaLibraryStats> => {
      const response = await apiClient.get(`${MEDIA_BASE_URL}/user-profile/stats/`);
      return response.data;
    }
  }
});

// Hook para usar a API de mídia
export const useMediaApi = () => {
  const apiClient = useApiClient();
  
  return useMemo(() => createMediaApi(apiClient), [apiClient]);
};