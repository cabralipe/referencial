/**
 * Tipos TypeScript para a biblioteca de mídia
 */

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface UserProfile {
  id: string;
  user: User;
  storage_used: number;
  storage_quota: number;
  storage_used_mb: number;
  storage_quota_mb: number;
  storage_percentage: number;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  name: string;
  color: string;
  created_by?: User;
  files_count: number;
  created_at: string;
  updated_at: string;
}

export interface MediaFolder {
  id: string;
  name: string;
  description?: string;
  parent?: string;
  parent_name?: string;
  owner: User;
  is_public: boolean;
  files_count: number;
  total_size: number;
  created_at: string;
  updated_at: string;
}

export interface FileVersion {
  id: string;
  file: string;
  version_number: string;
  file_data: string;
  file_size: number;
  change_description?: string;
  created_at: string;
}

export interface FileTag {
  id: string;
  file: string;
  tag: Tag;
  created_at: string;
}

export interface FileShare {
  id: string;
  file: string;
  shared_with: User;
  permission_level: 'view' | 'edit' | 'admin';
  expires_at?: string;
  created_at: string;
}

export interface MediaFile {
  id: string;
  name: string;
  original_name: string;
  file_type: string;
  file_size: number;
  file_size_mb: number;
  file: string;
  thumbnail?: string;
  folder?: string;
  folder_name?: string;
  owner: User;
  is_public: boolean;
  metadata: Record&lt;string, any&gt;;
  tags: FileTag[];
  versions: FileVersion[];
  shares: FileShare[];
  tags_count: number;
  extension: string;
  is_image: boolean;
  is_video: boolean;
  is_audio: boolean;
  is_document: boolean;
  created_at: string;
  updated_at: string;
}

export interface MediaFileUpload {
  name: string;
  file: File;
  folder?: string;
  is_public?: boolean;
  tags?: string[];
}

export interface MediaLibraryStats {
  total_files: number;
  total_size: number;
  total_size_mb: number;
  files_by_type: Record&lt;string, number&gt;;
  storage_used: number;
  storage_quota: number;
  storage_percentage: number;
}

export interface MediaLibraryFilters {
  search?: string;
  folder?: string;
  file_type?: string;
  tags?: string[];
  is_public?: boolean;
  owner?: number;
  ordering?: string;
}

export interface PaginatedResponse&lt;T&gt; {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

export type MediaFileResponse = PaginatedResponse&lt;MediaFile&gt;;
export type MediaFolderResponse = PaginatedResponse&lt;MediaFolder&gt;;
export type TagResponse = PaginatedResponse&lt;Tag&gt;;

export interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  result?: MediaFile;
}

export interface FolderTreeNode {
  id: string;
  name: string;
  children: FolderTreeNode[];
  files_count: number;
  is_public: boolean;
}

export interface MediaLibraryView {
  type: 'grid' | 'list';
  size: 'small' | 'medium' | 'large';
}

export interface MediaLibrarySort {
  field: 'name' | 'created_at' | 'updated_at' | 'file_size' | 'file_type';
  direction: 'asc' | 'desc';
}