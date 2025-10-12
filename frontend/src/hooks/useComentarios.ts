import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient, ApiError } from '@/api/client';
import type { Comentario, PaginatedResponse } from '@/api/types';

interface UseComentariosParams {
  alvoTipo?: string;
  alvoId?: number;
  resolvido?: boolean;
}

export function useComentarios({ alvoId, alvoTipo, resolvido }: UseComentariosParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['comentarios', { alvoId, alvoTipo, resolvido }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Comentario>>('/comentarios', {
        query: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          resolvido,
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface CreateComentarioInput {
  alvoTipo: string;
  alvoId: number;
  conteudoHtml: string;
  anchorJson?: string | null;
  mentions?: number[];
}

export function useCreateComentario() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ alvoTipo, alvoId, conteudoHtml, anchorJson, mentions }: CreateComentarioInput) => {
      const response = await client.post<Comentario>('/comentarios', {
        body: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          conteudo_html: conteudoHtml,
          anchor_json: anchorJson,
          mentions,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comentarios'] });
    },
  });
}

interface UpdateComentarioInput {
  comentarioId: number;
  payload: Partial<{
    conteudo_html: string;
    resolvido: boolean;
    anchor_json: string | null;
    mentions: number[];
  }>;
  etag?: string;
}

export function useUpdateComentario() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ comentarioId, payload, etag }: UpdateComentarioInput) => {
      if (!etag) {
        throw new ApiError('Informe o ETag atual do comentário para atualizar.', 428);
      }
      const response = await client.put<Comentario>(`/comentarios/${comentarioId}`, {
        body: payload,
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comentarios'] });
    },
  });
}
