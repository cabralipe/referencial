import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';

export interface MediaPermissions {
  can_upload: boolean;
  can_create_folders: boolean;
  can_manage_tags: boolean;
  can_share_files: boolean;
  can_delete_own: boolean;
  can_delete_others: boolean;
}

export interface UserProfile {
  id: number;
  user: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    email: string;
  };
  storage_quota: number;
  storage_used: number;
  storage_used_mb: number;
  storage_quota_mb: number;
  storage_percentage: number;
  default_folder_view: string;
  auto_tag_enabled: boolean;
  media_role: 'admin' | 'editor' | 'viewer' | 'guest';
  effective_media_role: 'admin' | 'editor' | 'viewer' | 'guest';
  permissions: MediaPermissions;
  can_upload: boolean;
  can_create_folders: boolean;
  can_manage_tags: boolean;
  can_share_files: boolean;
  can_delete_own: boolean;
  can_delete_others: boolean;
}

export interface UseMediaPermissionsResult {
  profile: UserProfile | null;
  permissions: MediaPermissions | null;
  role: string | null;
  isLoading: boolean;
  error: Error | null;
  canUpload: boolean;
  canCreateFolders: boolean;
  canManageTags: boolean;
  canShareFiles: boolean;
  canDeleteOwn: boolean;
  canDeleteOthers: boolean;
  canEditFile: (fileOwnerId: number) => boolean;
  canDeleteFile: (fileOwnerId: number) => boolean;
  isAdmin: boolean;
  isEditor: boolean;
  isViewer: boolean;
  isGuest: boolean;
}

export function useMediaPermissions(): UseMediaPermissionsResult {
  const { isAuthenticated, user } = useAuth();
  const apiClient = useApiClient();

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['media-profile'],
    queryFn: async () => {
      const response = await apiClient.get('/v1/media/profile/me/');
      return response.data as UserProfile;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutos
    cacheTime: 10 * 60 * 1000, // 10 minutos
  });

  const permissions = profile?.permissions || null;
  const role = profile?.effective_media_role || null;

  // Funções de conveniência para verificar permissões
  const canUpload = permissions?.can_upload || false;
  const canCreateFolders = permissions?.can_create_folders || false;
  const canManageTags = permissions?.can_manage_tags || false;
  const canShareFiles = permissions?.can_share_files || false;
  const canDeleteOwn = permissions?.can_delete_own || false;
  const canDeleteOthers = permissions?.can_delete_others || false;

  // Verificações de papel
  const isAdmin = role === 'admin';
  const isEditor = role === 'editor';
  const isViewer = role === 'viewer';
  const isGuest = role === 'guest';

  // Funções para verificar permissões específicas de arquivos
  const canEditFile = (fileOwnerId: number): boolean => {
    if (!user || !permissions) return false;
    
    // Admin pode editar qualquer arquivo
    if (isAdmin) return true;
    
    // Editor pode editar seus próprios arquivos
    if (isEditor && user.id === fileOwnerId) return true;
    
    return false;
  };

  const canDeleteFile = (fileOwnerId: number): boolean => {
    if (!user || !permissions) return false;
    
    // Admin pode deletar qualquer arquivo
    if (canDeleteOthers) return true;
    
    // Usuário pode deletar seus próprios arquivos se tiver permissão
    if (canDeleteOwn && user.id === fileOwnerId) return true;
    
    return false;
  };

  return {
    profile,
    permissions,
    role,
    isLoading,
    error: error as Error | null,
    canUpload,
    canCreateFolders,
    canManageTags,
    canShareFiles,
    canDeleteOwn,
    canDeleteOthers,
    canEditFile,
    canDeleteFile,
    isAdmin,
    isEditor,
    isViewer,
    isGuest,
  };
}