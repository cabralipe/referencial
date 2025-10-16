import { User } from './auth';
import { PaginatedResponse } from './api';

// Tipos base para comentários
export type CommentTargetType = 'resposta' | 'texto_unico' | 'quadro';
export type CommentStatus = 'aberto' | 'resolvido' | 'em_andamento';

// Dados de ancoragem para comentários
export interface CommentAnchor {
  type: 'text_selection' | 'paragraph' | 'cell' | 'general';
  startOffset?: number;
  endOffset?: number;
  selectedText?: string;
  paragraphIndex?: number;
  cellId?: string;
  coordinates?: { x: number; y: number };
}

// Interface principal do comentário
export interface Comment {
  id: string;
  alvo_tipo: CommentTargetType;
  alvo_id: string;
  anchor_json: CommentAnchor;
  conteudo_html: string;
  autor: User;
  autor_id: number;
  status: CommentStatus;
  resolvido: boolean; // Deprecated - use status instead
  resolvido_por: User | null;
  resolved_by: number | null;
  resolved_by_name?: string;
  resolved_at: string | null;
  resolution_reason?: string;
  mentions_ids: number[];
  mentions?: User[];
  created_at: string;
  updated_at: string;
  etag: string;
  replies?: Comment[]; // Para threads aninhadas (calculado no frontend)
  parent_id?: number; // ID do comentário pai
}

// Payloads para API
export interface CreateCommentPayload {
  alvo_tipo: CommentTargetType;
  alvo_id: string;
  anchor_json: CommentAnchor;
  conteudo_html: string;
  mentions?: number[];
  parent_id?: number; // Para replies
}

export interface UpdateCommentPayload {
  conteudo_html?: string;
  status?: CommentStatus;
  resolvido?: boolean; // Deprecated - use status instead
  resolved_by?: number | null;
  resolved_at?: string | null;
  resolution_reason?: string;
  mentions?: number[];
}

// Estados da interface
export interface CommentState {
  selectedComment: Comment | null;
  isEditing: boolean;
  showResolved: boolean;
  filter: CommentFilter;
  realtimeEnabled: boolean;
}

export interface CommentFilter {
  status?: CommentStatus | CommentStatus[];
  resolvido?: boolean; // Deprecated - use status instead
  autor?: number;
  search?: string;
  dateRange?: { start: string; end: string };
  parent_id?: number; // Para filtrar apenas comentários principais ou replies
}

// Eventos WebSocket
export interface CommentWebSocketEvent {
  type: 'comentario_criado' | 'comentario_atualizado' | 'comentario_deletado' | 'mencao_criada';
  payload: {
    comentario_id: number;
    alvo_tipo: CommentTargetType;
    alvo_id: string;
    conteudo_html?: string;
    autor?: User;
    mentions_ids?: number[];
    parent_id?: number;
  };
}

// Tipos para menções
export interface MentionUser {
  id: number;
  name: string;
  email: string;
  avatar?: string;
}

export interface MentionSuggestion {
  user: MentionUser;
  trigger: string; // '@' character position
  index: number;
}

// Tipos para editor de comentários
export interface CommentEditorState {
  content: string;
  mentions: number[];
  isSubmitting: boolean;
  showPreview: boolean;
}

// Tipos para filtros e busca
export interface CommentSearchParams {
  alvo_tipo: CommentTargetType;
  alvo_id: string;
  status?: CommentStatus | CommentStatus[];
  resolvido?: boolean; // Deprecated - use status instead
  autor?: number;
  search?: string;
  page?: number;
  page_size?: number;
  ordering?: string;
}

// Tipos para estatísticas de comentários
export interface CommentStats {
  total: number;
  unresolved: number;
  resolved: number;
  byAuthor: Record<number, number>;
  byDate: Record<string, number>;
}

// Tipos para permissões
export interface CommentPermissions {
  canCreate: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canResolve: boolean;
  canMention: boolean;
  canViewResolved: boolean;
}

// Tipos para configuração do sistema
export interface CommentSystemConfig {
  enabled: boolean;
  maxLength: number;
  allowedFormats: string[];
  mentionTrigger: string;
  autoSaveInterval: number;
  realtimeEnabled: boolean;
}

// Response types
export type CommentsResponse = PaginatedResponse<Comment>;
export type CommentResponse = Comment;

// Utility types
export type CommentWithReplies = Comment & {
  replies: Comment[];
  replyCount: number;
};

export type CommentThread = {
  parent: Comment;
  replies: Comment[];
  totalReplies: number;
  unresolvedReplies: number;
};

// Hook return types
export interface UseCommentsResult {
  comments: Comment[];
  isLoading: boolean;
  error: Error | null;
  hasNextPage: boolean;
  fetchNextPage: () => void;
  refetch: () => void;
}

export interface UseCreateCommentResult {
  createComment: (payload: CreateCommentPayload) => Promise<Comment>;
  isCreating: boolean;
  error: Error | null;
}

export interface UseUpdateCommentResult {
  updateComment: (id: number, payload: UpdateCommentPayload, etag: string) => Promise<Comment>;
  isUpdating: boolean;
  error: Error | null;
}

export interface UseDeleteCommentResult {
  deleteComment: (id: number, etag: string) => Promise<void>;
  isDeleting: boolean;
  error: Error | null;
}

// Component prop types
export interface CommentCardProps {
  comment: Comment;
  onReply?: (comment: Comment) => void;
  onResolve?: (comment: Comment) => void;
  onEdit?: (comment: Comment) => void;
  onDelete?: (comment: Comment) => void;
  showActions?: boolean;
  isNested?: boolean;
  maxNestingLevel?: number;
}

export interface CommentEditorProps {
  targetType: CommentTargetType;
  targetId: string;
  anchor?: CommentAnchor;
  parentComment?: Comment;
  initialContent?: string;
  onSave?: (comment: Comment) => void;
  onCancel?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export interface CommentSidebarProps {
  targetType: CommentTargetType;
  targetId: string;
  isOpen: boolean;
  onOpenChange?: (open: boolean) => void;
  onClose?: () => void;
  position?: 'left' | 'right';
  mode?: 'sidebar' | 'modal';
  showTrigger?: boolean;
  isPinned?: boolean;
  onPinChange?: (pinned: boolean) => void;
  className?: string;
  initialFilter?: CommentFilter;
}

export interface CommentInlineProps {
  targetType: CommentTargetType;
  targetId: string;
  children: React.ReactNode;
  enableTextSelection?: boolean;
  showIndicators?: boolean;
}

export interface CommentListProps {
  comments: Comment[];
  onReply?: (comment: Comment) => void;
  onResolve?: (comment: Comment) => void;
  onEdit?: (comment: Comment) => void;
  onDelete?: (comment: Comment) => void;
  showReplies?: boolean;
  maxNestingLevel?: number;
}

export interface CommentFiltersProps {
  filter: CommentFilter;
  onChange: (filter: CommentFilter) => void;
  totalCount: number;
  unresolvedCount: number;
  availableAuthors?: User[];
}

export interface CommentMentionsProps {
  users: MentionUser[];
  onSelect: (user: MentionUser) => void;
  trigger: string;
  isVisible: boolean;
  position?: { x: number; y: number };
}

export interface CommentResolutionProps {
  comment: Comment;
  onResolve: (comment: Comment) => void;
  onReopen: (comment: Comment) => void;
  canResolve: boolean;
}

// Error types
export interface CommentError {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, any>;
}

export interface CommentValidationError extends CommentError {
  field: string;
  value: any;
}

// Constants
export const COMMENT_MAX_LENGTH = 5000;
export const COMMENT_MAX_NESTING_LEVEL = 3;
export const COMMENT_AUTO_SAVE_INTERVAL = 3000;
export const COMMENT_MENTION_TRIGGER = '@';
export const COMMENT_DEBOUNCE_DELAY = 300;

// Enums
export enum CommentStatus {
  ACTIVE = 'active',
  RESOLVED = 'resolved',
  DRAFT = 'draft',
  DELETED = 'deleted'
}

export enum CommentAction {
  CREATE = 'create',
  EDIT = 'edit',
  DELETE = 'delete',
  RESOLVE = 'resolve',
  REOPEN = 'reopen',
  REPLY = 'reply',
  MENTION = 'mention'
}

export enum CommentEventType {
  CREATED = 'comentario_criado',
  UPDATED = 'comentario_atualizado',
  DELETED = 'comentario_deletado',
  MENTION_CREATED = 'mencao_criada',
  USER_TYPING = 'user_typing',
  USER_STOPPED_TYPING = 'user_stopped_typing'
}

// WebSocket types
export interface CommentWebSocketEvent {
  event_type: CommentEventType;
  target_type: CommentTargetType;
  target_id: string;
  comment?: Comment;
  user_id?: number;
  user_name?: string;
  data?: any;
}

export interface UseCommentRealtimeResult {
  isConnected: boolean;
  sendTypingIndicator: () => void;
  sendStoppedTypingIndicator: () => void;
  disconnect: () => void;
}

export interface CommentRealtimeConfig {
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}