import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse, TextoColaborativo } from '@/api/types';

interface UseTextosColaborativosParams {
  gtId?: number;
}

export function useTextosColaborativos({ gtId }: UseTextosColaborativosParams = {}) {
  const client = useApiClient();

  return useQuery({
    enabled: typeof gtId === 'number',
    queryKey: ['textos-colaborativos', { gtId }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<TextoColaborativo>>('/textos_colaborativos', {
        query: {
          gt: gtId ?? undefined,
          gt_id: gtId ?? undefined,
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface CreateTextoColaborativoInput {
  gtId: number;
  titulo: string;
  conteudoHtml: string;
}

export function useCreateTextoColaborativo() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ gtId, titulo, conteudoHtml }: CreateTextoColaborativoInput) => {
      const response = await client.post<TextoColaborativo>('/textos_colaborativos', {
        body: {
          gt: gtId,
          titulo,
          conteudo_html: conteudoHtml,
        },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData<TextoColaborativo[] | undefined>(['textos-colaborativos', { gtId: data.gt }], (previous = []) => {
        const filtered = previous.filter((item) => item.id !== data.id);
        const next = [data, ...filtered];
        return next.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
      });
    },
  });
}

interface UpdateTextoColaborativoInput {
  textoId: number;
  gtId: number;
  titulo: string;
  conteudoHtml: string;
  etag: string;
}

export function useUpdateTextoColaborativo() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ textoId, titulo, conteudoHtml, etag }: UpdateTextoColaborativoInput) => {
      const response = await client.put<TextoColaborativo>(`/textos_colaborativos/${textoId}`, {
        body: {
          titulo,
          conteudo_html: conteudoHtml,
        },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData<TextoColaborativo[] | undefined>(['textos-colaborativos', { gtId: data.gt }], (previous = []) => {
        const filtered = previous.filter((item) => item.id !== data.id);
        const next = [data, ...filtered];
        return next.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
      });
    },
  });
}
