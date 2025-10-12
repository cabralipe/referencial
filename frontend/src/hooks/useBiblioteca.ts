import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { BlocoTexto, Midia, PaginatedResponse } from '@/api/types';

interface UseMidiasParams {
  query?: string;
  tags?: string[];
}

export function useMidias({ query, tags }: UseMidiasParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['midias', { query, tags }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Midia>>('/midias', {
        query: {
          query,
          tags: tags?.join(','),
          page_size: 50,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface UseBlocosParams {
  query?: string;
  tags?: string[];
}

export function useBlocos({ query, tags }: UseBlocosParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['blocos', { query, tags }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<BlocoTexto>>('/blocos', {
        query: {
          query,
          tags: tags?.join(','),
          page_size: 50,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface CreateBlocoInput {
  titulo: string;
  conteudo_html: string;
  tags?: string[];
}

export function useCreateBloco() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ titulo, conteudo_html, tags }: CreateBlocoInput) => {
      const response = await client.post<BlocoTexto>('/blocos', {
        body: {
          titulo,
          conteudo_html,
          tags,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocos'] });
    },
  });
}

interface UpdateBlocoInput {
  blocoId: number;
  conteudo_html?: string;
  titulo?: string;
  tags?: string[];
  etag: string;
}

export function useUpdateBloco() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ blocoId, conteudo_html, titulo, tags, etag }: UpdateBlocoInput) => {
      const response = await client.put<BlocoTexto>(`/blocos/${blocoId}`, {
        body: {
          conteudo_html,
          titulo,
          tags,
        },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blocos'] });
    },
  });
}
