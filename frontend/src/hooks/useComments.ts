import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type {
  Comment,
  CommentTargetType,
  CommentFilter,
  CreateCommentPayload,
  UpdateCommentPayload,
  CommentsResponse,
  CommentResponse,
  UseCommentsResult,
  UseCreateCommentResult,
  UseUpdateCommentResult,
  UseDeleteCommentResult,
  PaginatedResponse
} from '@/types/comments';

// Hook principal para buscar comentários
export function useComments(
  targetType: CommentTargetType,
  targetId: string,
  filter?: CommentFilter
): UseCommentsResult {
  const client = useApiClient();

  const queryResult = useInfiniteQuery({
    queryKey: ['comments', targetType, targetId, filter],
    queryFn: async ({ pageParam = 1 }) => {
      const params = new URLSearchParams();
      params.append('alvo_tipo', targetType);
      params.append('alvo_id', targetId);
      params.append('page', pageParam.toString());
      params.append('page_size', '50');
      
      if (filter?.resolvido !== undefined) {
        params.append('resolvido', filter.resolvido.toString());
      }
      if (filter?.autor) {
        params.append('autor', filter.autor.toString());
      }
      if (filter?.search) {
        params.append('search', filter.search);
      }
      if (filter?.parent_id !== undefined) {
        params.append('parent_id', filter.parent_id.toString());
      }
      if (filter?.dateRange) {
        params.append('created_at__gte', filter.dateRange.start);
        params.append('created_at__lte', filter.dateRange.end);
      }

      const response = await client.get<CommentsResponse>(`/comentarios?${params}`);
      return response.data;
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.next) {
        const url = new URL(lastPage.next);
        return url.searchParams.get('page');
      }
      return undefined;
    },
    staleTime: 30000,
    enabled: !!targetType && !!targetId,
  });

  const comments = queryResult.data?.pages.flatMap(page => page.results) || [];

  return {
    comments,
    isLoading: queryResult.isLoading,
    error: queryResult.error,
    hasNextPage: queryResult.hasNextPage || false,
    fetchNextPage: queryResult.fetchNextPage,
    refetch: queryResult.refetch,
  };
}

// Hook para buscar um comentário específico
export function useComment(commentId: number) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['comment', commentId],
    queryFn: async () => {
      const response = await client.get<CommentResponse>(`/comentarios/${commentId}`);
      return response.data;
    },
    enabled: !!commentId,
    staleTime: 30000,
  });
}

// Hook para criar comentários
export function useCreateComment(): UseCreateCommentResult {
  const client = useApiClient();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (payload: CreateCommentPayload) => {
      const response = await client.post<CommentResponse>('/comentarios', payload);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ 
        queryKey: ['comments', data.alvo_tipo, data.alvo_id] 
      });
      
      // Se é uma resposta, também invalidar o comentário pai
      if (data.parent_id) {
        queryClient.invalidateQueries({ 
          queryKey: ['comment', data.parent_id] 
        });
      }

      toast.success('Comentário adicionado com sucesso!');
    },
    onError: (error: any) => {
      console.error('Erro ao criar comentário:', error);
      toast.error(error.response?.data?.message || 'Erro ao adicionar comentário');
    },
  });

  return {
    createComment: mutation.mutateAsync,
    isCreating: mutation.isPending,
    error: mutation.error,
  };
}

// Hook para atualizar comentários
export function useUpdateComment(): UseUpdateCommentResult {
  const client = useApiClient();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ 
      id, 
      payload, 
      etag 
    }: { 
      id: number; 
      payload: UpdateCommentPayload; 
      etag: string;
    }) => {
      const response = await client.put<CommentResponse>(`/comentarios/${id}`, payload, {
        headers: { 'If-Match': etag },
      });
      return response.data;
    },
    onSuccess: (data) => {
      // Atualizar cache do comentário específico
      queryClient.setQueryData(['comment', data.id], data);
      
      // Invalidar lista de comentários
      queryClient.invalidateQueries({ 
        queryKey: ['comments', data.alvo_tipo, data.alvo_id] 
      });

      const action = data.resolvido ? 'resolvido' : 'atualizado';
      toast.success(`Comentário ${action} com sucesso!`);
    },
    onError: (error: any) => {
      console.error('Erro ao atualizar comentário:', error);
      toast.error(error.response?.data?.message || 'Erro ao atualizar comentário');
    },
  });

  return {
    updateComment: mutation.mutateAsync,
    isUpdating: mutation.isPending,
    error: mutation.error,
  };
}

// Hook para deletar comentários
export function useDeleteComment(): UseDeleteCommentResult {
  const client = useApiClient();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ id, etag }: { id: number; etag: string }) => {
      await client.delete(`/comentarios/${id}`, {
        headers: { 'If-Match': etag },
      });
      return id;
    },
    onSuccess: (deletedId) => {
      // Remover do cache
      queryClient.removeQueries({ queryKey: ['comment', deletedId] });
      
      // Invalidar listas de comentários
      queryClient.invalidateQueries({ 
        queryKey: ['comments'] 
      });

      toast.success('Comentário deletado com sucesso!');
    },
    onError: (error: any) => {
      console.error('Erro ao deletar comentário:', error);
      toast.error(error.response?.data?.message || 'Erro ao deletar comentário');
    },
  });

  return {
    deleteComment: mutation.mutateAsync,
    isDeleting: mutation.isPending,
    error: mutation.error,
  };
}

// Hook para resolver/reabrir comentários
export function useResolveComment() {
  const updateComment = useUpdateComment();

  const resolveComment = async (comment: Comment) => {
    return updateComment.updateComment(comment.id, { resolvido: true }, comment.etag);
  };

  const reopenComment = async (comment: Comment) => {
    return updateComment.updateComment(comment.id, { resolvido: false }, comment.etag);
  };

  return {
    resolveComment,
    reopenComment,
    isResolving: updateComment.isUpdating,
    error: updateComment.error,
  };
}

// Hook para buscar estatísticas de comentários
export function useCommentStats(targetType: CommentTargetType, targetId: string) {
  const { comments } = useComments(targetType, targetId);

  const stats = {
    total: comments.length,
    unresolved: comments.filter(c => !c.resolvido).length,
    resolved: comments.filter(c => c.resolvido).length,
    byAuthor: comments.reduce((acc, comment) => {
      acc[comment.autor.id] = (acc[comment.autor.id] || 0) + 1;
      return acc;
    }, {} as Record<number, number>),
    byDate: comments.reduce((acc, comment) => {
      const date = new Date(comment.created_at).toISOString().split('T')[0];
      acc[date] = (acc[date] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
  };

  return stats;
}

// Hook para verificar permissões de comentários
export function useCommentPermissions() {
  const { user } = useAuth();

  const permissions = {
    canCreate: !!user && ['MEMBRO_GT', 'ARTICULADOR', 'ADMIN_CLIENTE'].includes(user.role),
    canEdit: !!user,
    canDelete: !!user && ['ARTICULADOR', 'ADMIN_CLIENTE'].includes(user.role),
    canResolve: !!user && ['ARTICULADOR', 'ADMIN_CLIENTE'].includes(user.role),
    canMention: !!user && ['MEMBRO_GT', 'ARTICULADOR', 'ADMIN_CLIENTE'].includes(user.role),
    canViewResolved: !!user,
  };

  const canEditComment = (comment: Comment) => {
    return permissions.canEdit && user?.id === comment.autor.id;
  };

  const canDeleteComment = (comment: Comment) => {
    return permissions.canDelete || (permissions.canEdit && user?.id === comment.autor.id);
  };

  const canResolveComment = (comment: Comment) => {
    return permissions.canResolve && !comment.resolvido;
  };

  const canReopenComment = (comment: Comment) => {
    return permissions.canResolve && comment.resolvido;
  };

  return {
    ...permissions,
    canEditComment,
    canDeleteComment,
    canResolveComment,
    canReopenComment,
  };
}

// Hook para buscar threads de comentários (comentários com suas respostas)
export function useCommentThreads(targetType: CommentTargetType, targetId: string) {
  const { comments: allComments, ...rest } = useComments(targetType, targetId);

  // Organizar comentários em threads
  const threads = allComments
    .filter(comment => !comment.parent_id) // Apenas comentários principais
    .map(parentComment => {
      const replies = allComments
        .filter(comment => comment.parent_id === parentComment.id)
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

      return {
        parent: parentComment,
        replies,
        totalReplies: replies.length,
        unresolvedReplies: replies.filter(r => !r.resolvido).length,
      };
    })
    .sort((a, b) => new Date(b.parent.created_at).getTime() - new Date(a.parent.created_at).getTime());

  return {
    threads,
    ...rest,
  };
}

// Hook para buscar comentários não resolvidos (para dashboard)
export function useUnresolvedComments(gtId?: number) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['comments', 'unresolved', gtId],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('resolvido', 'false');
      params.append('page_size', '100');
      
      if (gtId) {
        params.append('gt', gtId.toString());
      }

      const response = await client.get<CommentsResponse>(`/comentarios?${params}`);
      return response.data.results;
    },
    staleTime: 60000, // 1 minuto
    enabled: true,
  });
}