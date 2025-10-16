import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { useApiClient } from '@/api/client';
import type { 
  PaginatedResponse, 
  Review, 
  ReviewFilter, 
  CreateReviewPayload, 
  UpdateReviewPayload,
  ReviewTargetType 
} from '@/api/types';

// Hook to fetch reviews with optional filtering
export function useReviews(filter?: ReviewFilter) {
  const client = useApiClient();
  
  return useQuery({
    queryKey: ['reviews', filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (filter?.status) params.append('status', filter.status);
      if (filter?.alvo_tipo) params.append('alvo_tipo', filter.alvo_tipo);
      if (filter?.alvo_id) params.append('alvo_id', filter.alvo_id);
      if (filter?.revisor) params.append('revisor', filter.revisor.toString());
      if (filter?.solicitante) params.append('solicitante', filter.solicitante.toString());
      
      const queryString = params.toString();
      const url = queryString ? `/revisoes?${queryString}` : '/revisoes';
      
      const response = await client.get<PaginatedResponse<Review>>(url);
      return response.data;
    },
    staleTime: 30000, // 30 seconds
  });
}

// Hook to fetch a single review by ID
export function useReview(reviewId: number | null) {
  const client = useApiClient();
  
  return useQuery({
    enabled: Boolean(reviewId),
    queryKey: ['review', reviewId],
    queryFn: async () => {
      if (!reviewId) return null;
      const response = await client.get<Review>(`/revisoes/${reviewId}`);
      return response.data;
    },
    staleTime: 30000,
  });
}

// Hook to fetch reviews for a specific target
export function useReviewsForTarget(targetType: ReviewTargetType, targetId: string) {
  return useReviews({
    alvo_tipo: targetType,
    alvo_id: targetId,
  });
}

// Hook to create a new review
export function useCreateReview() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: CreateReviewPayload) => {
      const response = await client.post<Review>('/revisoes', {
        body: payload,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.setQueryData(['review', data.id], data);
      toast.success('Revisão solicitada com sucesso!');
    },
    onError: (error: any) => {
      console.error('Error creating review:', error);
      toast.error('Erro ao solicitar revisão. Tente novamente.');
    },
  });
}

// Hook to update an existing review
interface UpdateReviewInput {
  id: number;
  payload: UpdateReviewPayload;
  etag: string;
}

export function useUpdateReview() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, payload, etag }: UpdateReviewInput) => {
      const response = await client.put<Review>(`/revisoes/${id}`, {
        body: payload,
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['review', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Revisão atualizada com sucesso!');
    },
    onError: (error: any) => {
      console.error('Error updating review:', error);
      toast.error('Erro ao atualizar revisão. Tente novamente.');
    },
  });
}

// Hook to delete a review
export function useDeleteReview() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (reviewId: number) => {
      await client.delete(`/revisoes/${reviewId}`);
      return reviewId;
    },
    onSuccess: (reviewId) => {
      queryClient.removeQueries({ queryKey: ['review', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Revisão removida com sucesso!');
    },
    onError: (error: any) => {
      console.error('Error deleting review:', error);
      toast.error('Erro ao remover revisão. Tente novamente.');
    },
  });
}

// Hook for review workflow actions (approve/reject)
export function useReviewActions() {
  const updateReview = useUpdateReview();
  
  const approveReview = async (review: Review, parecer?: string) => {
    return updateReview.mutateAsync({
      id: review.id,
      payload: {
        status: 'aprovado',
        parecer_html: parecer || review.parecer_html,
      },
      etag: review.etag,
    });
  };
  
  const rejectReview = async (review: Review, parecer: string) => {
    return updateReview.mutateAsync({
      id: review.id,
      payload: {
        status: 'reprovado',
        parecer_html: parecer,
      },
      etag: review.etag,
    });
  };
  
  const submitForReview = async (review: Review) => {
    return updateReview.mutateAsync({
      id: review.id,
      payload: {
        status: 'em_revisao',
      },
      etag: review.etag,
    });
  };
  
  return {
    approveReview,
    rejectReview,
    submitForReview,
    isLoading: updateReview.isPending,
  };
}