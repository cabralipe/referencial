// Core comment components
export { CommentCard } from './CommentCard';
export { CommentEditor } from './CommentEditor';
export { CommentList } from './CommentList';
export { CommentThread } from './CommentThread';

// Sidebar and layout components
export { 
  CommentSidebar, 
  CommentSidebarTrigger, 
  useCommentSidebar 
} from './CommentSidebar';

// Inline commenting components
export { CommentInline, useCommentInline } from './CommentInline';

// Mention components
export { CommentMentions, useMentions } from './CommentMentions';

// Resolution components
export { CommentResolution } from './CommentResolution';

// Re-export hooks for convenience
export {
  useComments,
  useComment,
  useCreateComment,
  useUpdateComment,
  useDeleteComment,
  useResolveComment,
  useCommentStats,
  useCommentPermissions,
  useCommentThreads,
  useUnresolvedComments,
} from '@/hooks/useComments';

export {
  useCommentRealtime,
  useTypingIndicators,
} from '@/hooks/useCommentRealtime';

// Re-export types for convenience
export type {
  Comment,
  CommentTargetType,
  CommentAnchor,
  CommentFilter,
  CreateCommentPayload,
  UpdateCommentPayload,
  CommentCardProps,
  CommentEditorProps,
  CommentListProps,
  CommentThreadProps,
  CommentSidebarProps,
  CommentInlineProps,
} from '@/types/comments';