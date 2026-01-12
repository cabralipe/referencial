import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { fetchAllPaginated } from '@/utils/pagination';
import type { PaginatedResponse, Resposta } from '@/api/types';

interface UseRespostasParams {
  gtId?: number | null;
  includeAll?: boolean;
}

export function useRespostas({ gtId, includeAll = false }: UseRespostasParams) {
  const client = useApiClient();

  return useQuery({
    enabled: includeAll || Boolean(gtId),
    queryKey: ['respostas', gtId, includeAll],
    queryFn: async () => {
      if (gtId) {
        return fetchAllPaginated<Resposta>(client.get, '/respostas', {
          query: {
            gt: gtId,
            gt_id: gtId,
            page_size: 200,
          },
        });
      }
      const response = await client.get<PaginatedResponse<Resposta>>('/respostas', {
        query: {
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface UpsertRespostaInput {
  respostaId?: number;
  perguntaId: number;
  conteudoHtml: string;
  etag?: string;
}

export function useUpsertResposta(gtId?: number | null) {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ respostaId, perguntaId, conteudoHtml, etag }: UpsertRespostaInput) => {
      if (!gtId) {
        throw new Error('Selecione um GT para salvar a resposta');
      }
      if (respostaId) {
        const response = await client.put<Resposta>(`/respostas/${respostaId}`, {
          body: {
            gt: gtId,
            pergunta: perguntaId,
            conteudo_html: conteudoHtml,
          },
          ifMatch: etag,
        });
        return response.data;
      }
      const response = await client.post<Resposta>('/respostas', {
        body: {
          gt: gtId,
          pergunta: perguntaId,
          conteudo_html: conteudoHtml,
        },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: () => {
      if (gtId) {
        queryClient.invalidateQueries({ queryKey: ['respostas', gtId] });
      }
    },
  });
}
