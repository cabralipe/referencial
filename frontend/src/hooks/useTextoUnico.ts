import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse, TextoUnico, CreateTextoUnicoPayload, UpdateTextoUnicoPayload } from '@/api/types';

interface UseTextoUnicoParams {
  gtId?: number | null;
  tarefaId?: number | null;
}

export function useTextoUnico({ gtId, tarefaId }: UseTextoUnicoParams) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(gtId && tarefaId),
    queryKey: ['texto_unico', gtId, tarefaId],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<TextoUnico>>('/texto_unico', {
        query: {
          gt: gtId ?? undefined,
          tarefa: tarefaId ?? undefined,
          page_size: 1,
        },
      });
      return response.data.results?.[0] || null;
    },
  });
}

export function useCreateTextoUnico() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateTextoUnicoPayload) => {
      const response = await client.post<TextoUnico>('/texto_unico', {
        body: payload,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ 
        queryKey: ['texto_unico', data.gt, data.tarefa] 
      });
    },
  });
}

interface UpdateTextoUnicoInput {
  id: number;
  payload: UpdateTextoUnicoPayload;
  etag?: string;
}

export function useUpdateTextoUnico() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload, etag }: UpdateTextoUnicoInput) => {
      const response = await client.put<TextoUnico>(`/texto_unico/${id}`, {
        body: payload,
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ 
        queryKey: ['texto_unico', data.gt, data.tarefa] 
      });
    },
  });
}

interface UpsertTextoUnicoInput {
  gtId: number;
  tarefaId: number;
  conteudoHtml: string;
  textoUnicoId?: number;
  etag?: string;
}

export function useUpsertTextoUnico() {
  const createTextoUnico = useCreateTextoUnico();
  const updateTextoUnico = useUpdateTextoUnico();

  return useMutation({
    mutationFn: async ({ gtId, tarefaId, conteudoHtml, textoUnicoId, etag }: UpsertTextoUnicoInput) => {
      if (textoUnicoId) {
        return updateTextoUnico.mutateAsync({
          id: textoUnicoId,
          payload: { conteudo_html: conteudoHtml },
          etag,
        });
      } else {
        return createTextoUnico.mutateAsync({
          gt: gtId,
          tarefa: tarefaId,
          conteudo_html: conteudoHtml,
        });
      }
    },
  });
}