import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { BlocoTexto, Midia, PaginatedResponse } from '@/api/types';

interface UseMidiasParams {
  query?: string;
  tags?: string[];
  gtId?: number | null;
  perguntaId?: number | null;
}

export function useMidias({ query, tags, gtId, perguntaId }: UseMidiasParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['midias', { query, tags, gtId, perguntaId }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Midia>>('/midias', {
        query: {
          query,
          tags: tags?.join(','),
          gt_id: gtId ?? undefined,
          pergunta_id: perguntaId ?? undefined,
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
  gtId?: number | null;
  perguntaId?: number | null;
}

export function useBlocos({ query, tags, gtId, perguntaId }: UseBlocosParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['blocos', { query, tags, gtId, perguntaId }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<BlocoTexto>>('/blocos', {
        query: {
          query,
          tags: tags?.join(','),
          gt_id: gtId ?? undefined,
          pergunta_id: perguntaId ?? undefined,
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
  gt?: number | null;
  pergunta?: number | null;
}

export function useCreateBloco() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ titulo, conteudo_html, tags, gt, pergunta }: CreateBlocoInput) => {
      const response = await client.post<BlocoTexto>('/blocos', {
        body: {
          titulo,
          conteudo_html,
          tags,
          gt,
          pergunta,
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
  gt?: number | null;
  pergunta?: number | null;
  etag: string;
}

export function useUpdateBloco() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ blocoId, conteudo_html, titulo, tags, gt, pergunta, etag }: UpdateBlocoInput) => {
      const response = await client.put<BlocoTexto>(`/blocos/${blocoId}`, {
        body: {
          conteudo_html,
          titulo,
          tags,
          gt,
          pergunta,
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

interface CreateMidiaInput {
  url: string;
  legenda?: string | null;
  tags?: string[];
  gt?: number | null;
  pergunta?: number | null;
}

export function useCreateMidia() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ url, legenda, tags, gt, pergunta }: CreateMidiaInput) => {
      const response = await client.post<Midia>('/midias', {
        body: {
          url,
          legenda,
          tags,
          gt,
          pergunta,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['midias'] });
    },
  });
}
