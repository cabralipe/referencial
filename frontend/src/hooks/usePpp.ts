import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PppDocumento, PppOverviewItem } from '@/api/types';

interface UsePppDocumentoParams {
  escolaId?: number | null;
  enabled?: boolean;
}

export function usePppDocumento({ escolaId, enabled = true }: UsePppDocumentoParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['ppp', 'documento', { escolaId }],
    enabled,
    queryFn: async () => {
      const response = await client.get<PppDocumento>('/ppp', {
        query: {
          escola_id: escolaId ?? undefined,
        },
      });
      return response.data;
    },
  });
}

export function usePppOverview(enabled = true) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['ppp', 'overview'],
    enabled,
    queryFn: async () => {
      const response = await client.get<PppOverviewItem[]>('/ppp/overview');
      return response.data;
    },
  });
}

interface UpdatePppConteudoInput {
  escolaId?: number | null;
  etag?: string;
  titulo?: string;
  conteudoHtml: string;
}

export function useUpdatePppConteudo() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ escolaId, etag, titulo, conteudoHtml }: UpdatePppConteudoInput) => {
      const response = await client.patch<PppDocumento>('/ppp/conteudo', {
        query: {
          escola_id: escolaId ?? undefined,
        },
        body: {
          titulo,
          conteudo_html: conteudoHtml,
        },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['ppp', 'documento', { escolaId: variables.escolaId ?? undefined }] });
      queryClient.invalidateQueries({ queryKey: ['ppp', 'overview'] });
    },
  });
}

interface ConcludePppInput {
  escolaId?: number | null;
  etag?: string;
}

export function useConcludePpp() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ escolaId, etag }: ConcludePppInput) => {
      const response = await client.post<PppDocumento>('/ppp/concluir', {
        query: {
          escola_id: escolaId ?? undefined,
        },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['ppp', 'documento', { escolaId: variables.escolaId ?? undefined }] });
      queryClient.invalidateQueries({ queryKey: ['ppp', 'overview'] });
      queryClient.invalidateQueries({ queryKey: ['comentarios'] });
    },
  });
}
