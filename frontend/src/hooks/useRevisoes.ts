import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient, ApiError } from '@/api/client';
import type { PaginatedResponse, Revisao } from '@/api/types';

interface UseRevisoesParams {
  alvoTipo?: string;
  alvoId?: number;
  status?: string;
  pageSize?: number;
}

export function useRevisoes({ alvoId, alvoTipo, status, pageSize = 200 }: UseRevisoesParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['revisoes', { alvoId, alvoTipo, status, pageSize }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Revisao>>('/revisoes', {
        query: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          status,
          page_size: pageSize,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface CreateRevisaoInput {
  alvoTipo: string;
  alvoId: number;
  parecerHtml?: string;
  revisor?: number | null;
  status?: string;
}

export function useCreateRevisao() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ alvoTipo, alvoId, parecerHtml, revisor, status }: CreateRevisaoInput) => {
      const response = await client.post<Revisao>('/revisoes', {
        body: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          parecer_html: parecerHtml,
          revisor,
          status,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['revisoes'] });
    },
  });
}

interface UpdateRevisaoInput {
  revisaoId: number;
  payload: Partial<{
    status: string;
    parecer_html: string;
    revisor: number | null;
  }>;
  etag?: string;
}

export function useUpdateRevisao() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ revisaoId, payload, etag }: UpdateRevisaoInput) => {
      if (!etag) {
        throw new ApiError('É necessário informar o ETag da revisão para atualizar.', 428);
      }
      const response = await client.patch<Revisao>(`/revisoes/${revisaoId}`, {
        body: payload,
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['revisoes'] });
    },
  });
}

interface DeleteRevisaoInput {
  revisaoId: number;
}

export function useDeleteRevisao() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ revisaoId }: DeleteRevisaoInput) => {
      await client.del(`/revisoes/${revisaoId}`);
      return revisaoId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['revisoes'] });
    },
  });
}

interface SubmitRevisaoInput {
  revisaoId: number;
  etag?: string;
}

export function useSubmitRevisao() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ revisaoId, etag }: SubmitRevisaoInput) => {
      if (!etag) {
        throw new ApiError('É necessário informar o ETag da revisão para submeter.', 428);
      }
      const response = await client.post<Revisao>(`/revisoes/${revisaoId}/submit`, {
        body: {},
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['revisoes'] });
    },
  });
}
